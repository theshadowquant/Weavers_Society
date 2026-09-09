from fastapi import APIRouter, Depends
from app.core.tenant_context import TenantContext, get_current_tenant_context, require_roles
from app.models.schemas import SalesTransactionCreate
from app.services.sales_service import create_sale_transaction, get_bilingual_sale_bill
from app.database.session import get_db

router = APIRouter(prefix="/sales", tags=["Unified Sales Engine & Depots"])

@router.post("/transactions")
def api_create_sale(
    data: SalesTransactionCreate,
    ctx: TenantContext = Depends(require_roles(["SECRETARY", "SHOWROOM_CASHIER", "ACCOUNTANT", "MANAGING_DIRECTOR"]))
):
    return create_sale_transaction(ctx.tenant_id, ctx.user_id, data)

@router.get("/bills/{sale_id}")
def api_get_bill(sale_id: str, ctx: TenantContext = Depends(get_current_tenant_context)):
    return get_bilingual_sale_bill(ctx.tenant_id, sale_id)

@router.get("/recent")
def api_list_recent_sales(ctx: TenantContext = Depends(get_current_tenant_context)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.*, w.name_kn as showroom_name_kn
            FROM sales_transactions s
            JOIN warehouses w ON w.id = s.warehouse_id
            WHERE s.tenant_id = ?
            ORDER BY s.created_at DESC LIMIT 20
        """, (ctx.tenant_id,))
        return [dict(r) for r in cursor.fetchall()]
