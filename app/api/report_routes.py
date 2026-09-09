from typing import Optional
from fastapi import APIRouter, Depends
from app.core.tenant_context import TenantContext, get_current_tenant_context
from app.services.report_service import (
    get_statutory_daybook,
    get_weaver_material_balance_register,
    get_weaver_wage_thrift_register,
    get_directorate_rebate_claim_schedule,
    get_stock_valuation_schedule
)

router = APIRouter(prefix="/reports", tags=["Statutory Cooperative Registers"])

@router.get("/daybook")
def api_get_daybook(date: Optional[str] = None, ctx: TenantContext = Depends(get_current_tenant_context)):
    return get_statutory_daybook(ctx.tenant_id, target_date=date)

@router.get("/weaver-material")
def api_get_weaver_material(ctx: TenantContext = Depends(get_current_tenant_context)):
    return get_weaver_material_balance_register(ctx.tenant_id)

@router.get("/weaver-wages")
def api_get_weaver_wages(ctx: TenantContext = Depends(get_current_tenant_context)):
    return get_weaver_wage_thrift_register(ctx.tenant_id)

@router.get("/rebate-claims")
def api_get_rebate_claims(ctx: TenantContext = Depends(get_current_tenant_context)):
    return get_directorate_rebate_claim_schedule(ctx.tenant_id)

@router.get("/stock-valuation")
def api_get_stock_valuation(ctx: TenantContext = Depends(get_current_tenant_context)):
    return get_stock_valuation_schedule(ctx.tenant_id)
