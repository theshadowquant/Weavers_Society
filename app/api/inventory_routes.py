from typing import Optional
from fastapi import APIRouter, Depends
from app.core.tenant_context import TenantContext, get_current_tenant_context
from app.models.schemas import YarnLotCreate
from app.services.inventory_service import (
    get_inventory_status_by_state, get_stock_movement_journal, get_tenant_warehouses,
    create_yarn_lot, list_yarn_lots
)
from app.services.report_service import get_stock_valuation_schedule

router = APIRouter(prefix="/inventory", tags=["Multi-State Inventory Ledger"])

@router.get("/yarn-lots")
def api_list_yarn_lots(ctx: TenantContext = Depends(get_current_tenant_context)):
    return list_yarn_lots(ctx.tenant_id)

@router.post("/yarn-lots")
def api_create_yarn_lot(data: YarnLotCreate, ctx: TenantContext = Depends(get_current_tenant_context)):
    return create_yarn_lot(ctx.tenant_id, data)

@router.get("/warehouses")
def api_get_warehouses(ctx: TenantContext = Depends(get_current_tenant_context)):
    return get_tenant_warehouses(ctx.tenant_id)

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

