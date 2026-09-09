from fastapi import APIRouter, Depends
from app.core.tenant_context import TenantContext, get_current_tenant_context
from app.services.dashboard_service import get_operational_command_center

router = APIRouter(prefix="/dashboard", tags=["Operational Command Center"])

@router.get("/command-center")
def api_get_command_center(ctx: TenantContext = Depends(get_current_tenant_context)):
    return get_operational_command_center(ctx.tenant_id)
