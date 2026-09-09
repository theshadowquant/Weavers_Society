from fastapi import APIRouter, Depends
from app.core.tenant_context import TenantContext, get_current_tenant_context, require_roles
from app.models.schemas import ProductionAllotmentCreate, InspectionReceiptCreate
from app.services.production_service import create_production_allotment, process_technical_inspection_receipt, list_production_allotments

router = APIRouter(prefix="/production", tags=["Cottage Loom Production"])

@router.post("/allotments")
def api_create_allotment(
    data: ProductionAllotmentCreate,
    ctx: TenantContext = Depends(require_roles(["SECRETARY", "MANAGING_DIRECTOR", "GODOWN_KEEPER"]))
):
    return create_production_allotment(ctx.tenant_id, ctx.user_id, data)

@router.post("/inspections")
def api_process_inspection(
    data: InspectionReceiptCreate,
    ctx: TenantContext = Depends(require_roles(["SECRETARY", "MANAGING_DIRECTOR", "QUALITY_INSPECTOR"]))
):
    return process_technical_inspection_receipt(ctx.tenant_id, ctx.user_id, data)

@router.get("/allotments")
def api_list_allotments(ctx: TenantContext = Depends(get_current_tenant_context)):
    return list_production_allotments(ctx.tenant_id)
