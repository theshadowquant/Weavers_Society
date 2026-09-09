from typing import Optional
from fastapi import APIRouter, Depends
from app.core.tenant_context import TenantContext, get_current_tenant_context
from app.services.inventory_service import get_inventory_status_by_state, get_stock_movement_journal
from app.services.report_service import get_stock_valuation_schedule

router = APIRouter(prefix="/inventory", tags=["Multi-State Inventory Ledger"])

@router.get("/status")
def api_get_inventory_status(ctx: TenantContext = Depends(get_current_tenant_context)):
    return get_inventory_status_by_state(ctx.tenant_id)

@router.get("/journal")
def api_get_journal(
    warehouse_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    ctx: TenantContext = Depends(get_current_tenant_context)
):
    return get_stock_movement_journal(ctx.tenant_id, warehouse_id=warehouse_id, limit=limit, offset=offset)

@router.get("/valuation")
def api_get_valuation(ctx: TenantContext = Depends(get_current_tenant_context)):
    return get_stock_valuation_schedule(ctx.tenant_id)
