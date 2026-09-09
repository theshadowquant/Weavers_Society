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
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM purchase_invoices WHERE tenant_id = ? AND society_ref_no = ?", (tenant_id, data.society_ref_no))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail=f"Purchase reference '{data.society_ref_no}' already exists.")
            
        conn.execute("""
            INSERT INTO purchase_invoices (
                id, tenant_id, supplier_id, invoice_no, society_ref_no,
                invoice_date, warehouse_id, subtotal, tax_amount, total_amount,
                payment_status, status, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'UNPAID', 'DRAFT', ?)
        """, (
            invoice_id, tenant_id, data.supplier_id, data.invoice_no, data.society_ref_no,
            data.invoice_date, data.warehouse_id, subtotal, tax_amount, total_amount, data.notes
        ))
        
        for item in data.items:
            item_id = str(uuid.uuid4())
            item_sub = item.quantity * item.unit_cost
            item_tax = item_sub * item.tax_rate / 100.0
            item_tot = item_sub + item_tax
            conn.execute("""
                INSERT INTO purchase_items (
                    id, tenant_id, purchase_invoice_id, product_id,
                    quantity, unit_cost, tax_rate, tax_amount, line_total
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item_id, tenant_id, invoice_id, item.product_id,
                item.quantity, item.unit_cost, item.tax_rate, item_tax, item_tot
            ))
            
        return {
            "invoice_id": invoice_id,
            "society_ref_no": data.society_ref_no,
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
            raise HTTPException(status_code=400, detail="Invoice is already POSTED and immutable.")
            
        cursor.execute("SELECT * FROM purchase_items WHERE tenant_id = ? AND purchase_invoice_id = ?", (tenant_id, invoice_id))
        items = cursor.fetchall()
        
        # Post to inventory ledger
        for item in items:
            append_stock_movement(
                conn=conn,
                tenant_id=tenant_id,
                product_id=item["product_id"],
                warehouse_id=inv["warehouse_id"],
                movement_type="PURCHASE_RECEIPT",
                quantity_delta=float(item["quantity"]), # Inward is positive
                unit_cost=float(item["unit_cost"]),
                reference_type="PURCHASE_INVOICE",
                reference_id=invoice_id,
                performed_by=user_id,
                notes=f"Supplier Inward: {inv['invoice_no']} Ref: {inv['society_ref_no']}"
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
            "status": "POSTED",
            "message": "Stock successfully added to inventory ledger."
        }

def list_purchases(tenant_id: str) -> List[Dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT pi.*, s.name as supplier_name, w.name_en as warehouse_name
            FROM purchase_invoices pi
            JOIN suppliers s ON s.id = pi.supplier_id
            JOIN warehouses w ON w.id = pi.warehouse_id
            WHERE pi.tenant_id = ?
            ORDER BY pi.created_at DESC
        """, (tenant_id,))
        return [dict(r) for r in cursor.fetchall()]
