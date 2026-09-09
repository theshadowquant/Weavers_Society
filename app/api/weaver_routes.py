from typing import Optional
from fastapi import APIRouter, Depends
from app.core.tenant_context import TenantContext, get_current_tenant_context, require_roles
from app.models.schemas import WeaverCreate
from app.services.weaver_service import create_weaver_member, list_weavers, get_weaver_operational_profile

router = APIRouter(prefix="/weavers", tags=["Weaver Artisanal Ecosystem"])

@router.post("")
def api_create_weaver(
    data: WeaverCreate,
    ctx: TenantContext = Depends(require_roles(["SECRETARY", "MANAGING_DIRECTOR", "ACCOUNTANT"]))
):
    return create_weaver_member(ctx.tenant_id, data)

@router.get("")
def api_list_weavers(
    search: Optional[str] = None,
    ctx: TenantContext = Depends(get_current_tenant_context)
):
    return list_weavers(ctx.tenant_id, search=search)

@router.get("/{weaver_id}/profile")
def api_get_weaver_profile(
    weaver_id: str,
    ctx: TenantContext = Depends(get_current_tenant_context)
):
    return get_weaver_operational_profile(ctx.tenant_id, weaver_id)
