import uuid
from typing import List, Dict, Any
from fastapi import HTTPException
from app.database.session import get_db
from app.models.schemas import PurchaseInvoiceCreate
from app.services.inventory_service import append_stock_movement
from app.core.audit import log_audit_event

def create_purchase_invoice(tenant_id: str, user_id: str, data: PurchaseInvoiceCreate) -> Dict[str, Any]:
    invoice_id = str(uuid.uuid4())
    subtotal = sum(item.quantity * item.unit_cost for item in data.items)
    tax_amount = sum((item.quantity * item.unit_cost * item.tax_rate / 100.0) for item in data.items)
    total_amount = subtotal + tax_amount
    entry_no = data.society_entry_no or data.society_ref_no or f"PI-{uuid.uuid4().hex[:6].upper()}"
    wh_id = data.receiving_warehouse_id or data.warehouse_id
    
    with get_db() as conn:
        cursor = conn.cursor()
        if not wh_id:
            cursor.execute("SELECT id FROM warehouses WHERE tenant_id = ? AND storage_type = 'RAW_YARN_GODOWN' LIMIT 1", (tenant_id,))
            wh_row = cursor.fetchone()
            wh_id = wh_row["id"] if wh_row else None
            
        cursor.execute("SELECT id FROM purchase_invoices WHERE tenant_id = ? AND society_entry_no = ?", (tenant_id, entry_no))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail=f"Purchase entry '{entry_no}' already exists.")
            
        conn.execute("""
            INSERT INTO purchase_invoices (
                id, tenant_id, supplier_id, invoice_no, society_entry_no,
                invoice_date, receiving_warehouse_id, subtotal, tax_amount, total_amount,
                payment_status, status, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'UNPAID', 'DRAFT', ?)
        """, (
            invoice_id, tenant_id, data.supplier_id, data.invoice_no, entry_no,
            data.invoice_date, wh_id, subtotal, tax_amount, total_amount, data.notes
        ))
        
        for item in data.items:
            item_id = str(uuid.uuid4())
            yarn_lot_id = item.yarn_lot_id
            
            # Inline yarn lot resolution or creation
            if not yarn_lot_id and item.lot_number:
                cursor.execute("SELECT id FROM yarn_lots WHERE tenant_id = ? AND lot_number = ?", (tenant_id, item.lot_number))
                existing_lot = cursor.fetchone()
                if existing_lot:
                    yarn_lot_id = existing_lot["id"]
                else:
                    yarn_lot_id = str(uuid.uuid4())
                    conn.execute("""
                        INSERT INTO yarn_lots (
                            id, tenant_id, lot_number, yarn_type, count_spec, shade_code, mill_name, hsn_code, unit_cost_per_kg
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        yarn_lot_id, tenant_id, item.lot_number,
                        item.yarn_type or "COTTON",
                        item.count_spec or "Standard Count",
                        item.shade_code or "Natural/White",
                        item.mill_name or "Direct Sourced Mill",
                        "5205", item.unit_cost
                    ))

            item_sub = item.quantity * item.unit_cost
            item_tax = item_sub * item.tax_rate / 100.0
            item_tot = item_sub + item_tax
            conn.execute("""
                INSERT INTO purchase_items (
                    id, tenant_id, purchase_invoice_id, yarn_lot_id, product_id,
                    quantity_kgs, rate_per_unit, tax_rate, tax_amount, line_total
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item_id, tenant_id, invoice_id, yarn_lot_id, item.product_id,
                item.quantity, item.unit_cost, item.tax_rate, item_tax, item_tot
            ))
            
    # If auto_post is requested, immediately post into the inventory ledger
    if getattr(data, "auto_post", True):
        return post_purchase_invoice(tenant_id, user_id, invoice_id)

    return {
        "invoice_id": invoice_id,
        "society_entry_no": entry_no,
        "total_amount": round(total_amount, 2),
        "status": "DRAFT"
    }

def post_purchase_invoice(tenant_id: str, user_id: str, invoice_id: str) -> Dict[str, Any]:
    """
    Transitions purchase invoice from DRAFT to POSTED:
    1. Validates invoice state.
    2. Atomically records inward stock movements in inventory_ledger.
    3. Locks invoice from further editing.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM purchase_invoices WHERE tenant_id = ? AND id = ?", (tenant_id, invoice_id))
        inv = cursor.fetchone()
        if not inv:
            raise HTTPException(status_code=404, detail="Purchase invoice not found.")
        if inv["status"] == "POSTED":
            return {"invoice_id": invoice_id, "status": "POSTED", "message": "Invoice already posted."}
            
        cursor.execute("SELECT * FROM purchase_items WHERE tenant_id = ? AND purchase_invoice_id = ?", (tenant_id, invoice_id))
        items = cursor.fetchall()
        
        # Post to inventory ledger
        for item in items:
            append_stock_movement(
                conn=conn,
                tenant_id=tenant_id,
                warehouse_id=inv["receiving_warehouse_id"],
                movement_type="PURCHASE_YARN_INWARD",
                quantity_delta=float(item["quantity_kgs"]), # Inward is positive
                unit_cost=float(item["rate_per_unit"]),
                reference_type="PURCHASE_INVOICE",
                reference_id=invoice_id,
                performed_by=user_id,
                product_id=item["product_id"],
                yarn_lot_id=item["yarn_lot_id"],
                notes=f"Supplier Inward: {inv['invoice_no']} Entry: {inv['society_entry_no']}"
            )
            
        conn.execute("""
            UPDATE purchase_invoices
            SET status = 'POSTED', posted_at = datetime('now'), verified_by = ?
            WHERE id = ? AND tenant_id = ?
        """, (user_id, invoice_id, tenant_id))
        
        log_audit_event(
            conn=conn,
            tenant_id=tenant_id,
            action="PURCHASE_POSTED",
            entity_type="purchase_invoices",
            entity_id=invoice_id,
            user_id=user_id,
            new_values={"total_amount": inv["total_amount"], "status": "POSTED"}
        )
        
        return {
            "invoice_id": invoice_id,
            "society_entry_no": inv["society_entry_no"],
            "total_amount": inv["total_amount"],
            "status": "POSTED",
            "message": "ದಾಸ್ತಾನು ಯಶಸ್ವಿಯಾಗಿ ಕೇಂದ್ರ ನೂಲು ಗೋದಾಮಿಗೆ ಜಮಾ ಆಗಿದೆ (Stock inward successfully posted)."
        }

def list_purchases(tenant_id: str) -> List[Dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT pi.*, 
                   COALESCE(s.name, 'Direct Mill Supplier') as supplier_name,
                   COALESCE(w.name_kn, 'ಕೇಂದ್ರ ನೂಲು ಉಗ್ರಾಣ') as warehouse_name_kn,
                   COALESCE(w.name_en, 'Central Yarn Godown') as warehouse_name
            FROM purchase_invoices pi
            LEFT JOIN suppliers s ON s.id = pi.supplier_id
            LEFT JOIN warehouses w ON w.id = pi.receiving_warehouse_id
            WHERE pi.tenant_id = ?
            ORDER BY pi.created_at DESC
        """, (tenant_id,))
        rows = [dict(r) for r in cursor.fetchall()]

        # Attach item summaries
        for r in rows:
            cursor.execute("""
                SELECT pi_item.*, yl.lot_number, yl.count_spec, yl.yarn_type
                FROM purchase_items pi_item
                LEFT JOIN yarn_lots yl ON yl.id = pi_item.yarn_lot_id
                WHERE pi_item.purchase_invoice_id = ?
            """, (r["id"],))
            r["items"] = [dict(it) for it in cursor.fetchall()]
            
        return rows

