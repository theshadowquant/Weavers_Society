import uuid
from typing import List, Dict, Any, Optional
from fastapi import HTTPException
from app.database.session import get_db
from app.models.schemas import SalesTransactionCreate
from app.services.inventory_service import append_ledger_entry, get_product_stock_in_warehouse
from app.core.audit import log_audit_event

def create_sale_transaction(tenant_id: str, user_id: str, data: SalesTransactionCreate) -> Dict[str, Any]:
    sale_id = str(uuid.uuid4())
    prefix = "RET" if data.sale_channel == "RETAIL_SHOWROOM" else "WHL"
    bill_number = f"{prefix}-{uuid.uuid4().hex[:6].upper()}"
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 1. Resolve Active Directorate Rebate Scheme if requested
        rebate_percent = 0.0
        scheme_id = data.scheme_id
        if data.apply_govt_rebate:
            if scheme_id:
                cursor.execute("SELECT * FROM scheme_configs WHERE tenant_id = ? AND id = ? AND is_active = 1", (tenant_id, scheme_id))
            else:
                cursor.execute("SELECT * FROM scheme_configs WHERE tenant_id = ? AND is_active = 1 ORDER BY created_at DESC LIMIT 1", (tenant_id,))
            scheme = cursor.fetchone()
            if scheme:
                rebate_percent = float(scheme["rebate_percentage"])
                scheme_id = scheme["id"]
                
        # 2. Process Line Items and Check Showroom Stock
        gross_amount = 0.0
        total_discount = 0.0
        total_rebate = 0.0
        total_tax = 0.0
        processed_items = []
        
        for item in data.items:
            cursor.execute("SELECT * FROM products WHERE tenant_id = ? AND (id = ? OR sku = ?)", (tenant_id, item.product_id, item.product_id))
            prod = cursor.fetchone()
            if not prod:
                raise HTTPException(status_code=404, detail=f"Product '{item.product_id}' not found.")
                
            available_stock = get_product_stock_in_warehouse(tenant_id, prod["id"], data.warehouse_id)
            if available_stock < item.quantity:
                raise HTTPException(
                    status_code=400,
                    detail=f"Insufficient showroom stock for '{prod['name_kn']}' ({prod['sku']}). Available: {available_stock}, Requested: {item.quantity}"
                )
                
            rate = item.unit_rate if item.unit_rate is not None else (float(prod["wholesale_rate"]) if data.sale_channel != "RETAIL_SHOWROOM" else float(prod["retail_rate"]))
            line_gross = item.quantity * rate
            line_disc = item.discount_amount
            
            # Rebate on post-discount value
            line_rebate = 0.0
            if rebate_percent > 0:
                line_rebate = round((line_gross - line_disc) * (rebate_percent / 100.0), 2)
                
            line_taxable = max(0.0, line_gross - line_disc - line_rebate)
            line_tax = round(line_taxable * (float(prod["tax_rate"]) / 100.0), 2)
            line_net = line_taxable + line_tax
            
            gross_amount += line_gross
            total_discount += line_disc
            total_rebate += line_rebate
            total_tax += line_tax
            
            processed_items.append({
                "product_id": prod["id"],
                "sku": prod["sku"],
                "name_en": prod["name_en"],
                "name_kn": prod["name_kn"],
                "quantity": item.quantity,
                "unit_rate": rate,
                "discount_amount": line_disc,
                "rebate_amount": line_rebate,
                "tax_rate": float(prod["tax_rate"]),
                "tax_amount": line_tax,
                "line_total": line_net,
                "cost_basis": float(prod["standard_manufacturing_cost"])
            })
            
        taxable_total = gross_amount - total_discount - total_rebate
        raw_payable = taxable_total + total_tax
        round_off = round(round(raw_payable) - raw_payable, 2)
        net_payable = round(raw_payable + round_off, 2)
        
        # 3. Insert Master Sales Record
        conn.execute("""
            INSERT INTO sales_transactions (
                id, tenant_id, bill_number, sale_channel, warehouse_id,
                customer_name, customer_phone, customer_gstin, customer_address,
                gross_amount, discount_amount, rebate_amount, scheme_id,
                taxable_amount, tax_amount, round_off, net_customer_payable,
                govt_subsidy_receivable, payment_mode, payment_reference,
                status, created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'POSTED', ?)
        """, (
            sale_id, tenant_id, bill_number, data.sale_channel, data.warehouse_id,
            data.customer_name, data.customer_phone, data.customer_gstin, data.customer_address,
            gross_amount, total_discount, total_rebate, scheme_id,
            taxable_total, total_tax, round_off, net_payable,
            total_rebate, data.payment_mode, data.payment_reference, user_id
        ))
        
        # 4. Insert Items & Post Stock Outward Movement
        movement_type = "RETAIL_SALE" if data.sale_channel == "RETAIL_SHOWROOM" else "WHOLESALE_SALE"
        for item in processed_items:
            conn.execute("""
                INSERT INTO sales_items (
                    id, tenant_id, sale_id, product_id, quantity,
                    unit_rate, discount_amount, rebate_amount,
                    tax_rate, tax_amount, line_total
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(uuid.uuid4()), tenant_id, sale_id, item["product_id"], item["quantity"],
                item["unit_rate"], item["discount_amount"], item["rebate_amount"],
                item["tax_rate"], item["tax_amount"], item["line_total"]
            ))
            
            # Immutable Outward Ledger Entry
            append_ledger_entry(
                conn=conn, tenant_id=tenant_id, warehouse_id=data.warehouse_id,
                movement_type=movement_type, quantity_delta=-item["quantity"],
                unit_cost=item["cost_basis"], reference_type="SALE_BILL",
                reference_id=sale_id, performed_by=user_id, product_id=item["product_id"],
                notes=f"Bill No: {bill_number} ({data.sale_channel})"
            )
            
        log_audit_event(
            conn=conn, tenant_id=tenant_id, action="SALE_COMMITTED",
            entity_type="sales_transactions", entity_id=sale_id, user_id=user_id,
            new_values={"bill_number": bill_number, "net_payable": net_payable, "rebate_subsidy": total_rebate}
        )
        
        return {
            "sale_id": sale_id,
            "bill_number": bill_number,
            "sale_channel": data.sale_channel,
            "gross_amount": gross_amount,
            "rebate_discount": total_rebate,
            "tax_amount": total_tax,
            "net_payable": net_payable,
            "govt_subsidy_receivable": total_rebate,
            "payment_mode": data.payment_mode,
            "items": processed_items
        }

def get_bilingual_sale_bill(tenant_id: str, sale_id: str) -> Dict[str, Any]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.*, t.legal_name_en as society_name_en, t.legal_name_kn as society_name_kn,
                   t.registration_number, t.registered_office_address, t.primary_phone,
                   t.gstin as society_gstin, t.directorate_society_code,
                   w.name_kn as showroom_name_kn, w.name_en as showroom_name_en
            FROM sales_transactions s
            JOIN tenants t ON t.id = s.tenant_id
            JOIN warehouses w ON w.id = s.warehouse_id
            WHERE s.tenant_id = ? AND s.id = ?
        """, (tenant_id, sale_id))
        bill = cursor.fetchone()
        if not bill:
            raise HTTPException(status_code=404, detail="Sale bill not found.")
            
        cursor.execute("""
            SELECT si.*, p.sku, p.name_kn, p.name_en, p.uom, p.hsn_code, p.gi_tag_certified
            FROM sales_items si
            JOIN products p ON p.id = si.product_id
            WHERE si.tenant_id = ? AND si.sale_id = ?
        """, (tenant_id, sale_id))
        items = cursor.fetchall()
        
        return {
            "bill": dict(bill),
            "items": [dict(i) for i in items]
        }
