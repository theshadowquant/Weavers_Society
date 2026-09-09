from typing import Optional
from fastapi import APIRouter, Depends
from app.core.tenant_context import TenantContext, get_current_tenant_context, require_roles
from app.models.schemas import WeaverCreate
from app.services.member_service import create_weaver, list_weavers, get_weaver_passbook

router = APIRouter(prefix="/weavers", tags=["Weaver Members"])

@router.post("")
def api_create_weaver(
    data: WeaverCreate,
    ctx: TenantContext = Depends(require_roles(["SOCIETY_ADMIN", "ACCOUNTANT", "PRODUCTION_SUPERVISOR"]))
):
    return create_weaver(ctx.tenant_id, data)

@router.get("")
def api_list_weavers(
    search: Optional[str] = None,
    ctx: TenantContext = Depends(get_current_tenant_context)
):
    return list_weavers(ctx.tenant_id, search=search)

@router.get("/{weaver_id}/passbook")
def api_get_weaver_passbook(
    weaver_id: str,
    ctx: TenantContext = Depends(get_current_tenant_context)
):
    return get_weaver_passbook(ctx.tenant_id, weaver_id)
