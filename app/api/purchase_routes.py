from fastapi import APIRouter, Depends
from app.core.tenant_context import TenantContext, get_current_tenant_context, require_roles
from app.models.schemas import PurchaseInvoiceCreate, SupplierCreate
from app.services.purchase_service import create_purchase_invoice, post_purchase_invoice, list_purchases
from app.database.session import get_db
import uuid

router = APIRouter(prefix="/purchases", tags=["Purchasing & Suppliers"])

@router.post("/suppliers")
def api_create_supplier(
    data: SupplierCreate,
    ctx: TenantContext = Depends(require_roles(["SECRETARY", "MANAGING_DIRECTOR", "ACCOUNTANT", "GODOWN_KEEPER"]))
):
    supplier_id = str(uuid.uuid4())
    type_map = {
        "YARN_MILL": "COOP_SPINNING_MILL",
        "DYE_SUPPLIER": "DYES_CHEMICALS",
        "ZARI_DEALER": "PRIVATE_MILL",
        "GENERAL": "PRIVATE_MILL"
    }
    sup_type = type_map.get(data.supplier_type, data.supplier_type)
    if sup_type not in ('NHDC_DEPOT', 'COOP_SPINNING_MILL', 'PRIVATE_MILL', 'DYES_CHEMICALS'):
        sup_type = 'COOP_SPINNING_MILL'

    with get_db() as conn:
        conn.execute("""
            INSERT INTO suppliers (id, tenant_id, name, supplier_type, contact_person, phone, gstin, address)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (supplier_id, ctx.tenant_id, data.name, sup_type, data.contact_person, data.phone, data.gstin, data.address))
        return {"id": supplier_id, "name": data.name, "supplier_type": sup_type}

@router.get("/suppliers")
def api_list_suppliers(ctx: TenantContext = Depends(get_current_tenant_context)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM suppliers WHERE tenant_id = ? ORDER BY name ASC", (ctx.tenant_id,))
        return [dict(r) for r in cursor.fetchall()]

@router.post("/invoices")
def api_create_purchase(
    data: PurchaseInvoiceCreate,
    ctx: TenantContext = Depends(require_roles(["SECRETARY", "MANAGING_DIRECTOR", "ACCOUNTANT", "GODOWN_KEEPER"]))
):
    return create_purchase_invoice(ctx.tenant_id, ctx.user_id, data)

@router.post("/invoices/{invoice_id}/post")
def api_post_purchase(
    invoice_id: str,
    ctx: TenantContext = Depends(require_roles(["SECRETARY", "MANAGING_DIRECTOR", "ACCOUNTANT", "GODOWN_KEEPER"]))
):
    return post_purchase_invoice(ctx.tenant_id, ctx.user_id, invoice_id)

@router.get("/invoices")
def api_list_purchases(ctx: TenantContext = Depends(get_current_tenant_context)):
    return list_purchases(ctx.tenant_id)
