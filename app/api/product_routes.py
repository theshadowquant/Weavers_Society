from typing import Optional
from fastapi import APIRouter, Depends
from app.core.tenant_context import TenantContext, get_current_tenant_context, require_roles
from app.models.schemas import ProductCreate
from app.services.product_service import create_product, list_products, get_product

router = APIRouter(prefix="/products", tags=["Products Master"])

@router.post("")
def api_create_product(
    data: ProductCreate,
    ctx: TenantContext = Depends(require_roles(["SOCIETY_ADMIN", "ACCOUNTANT", "PRODUCTION_SUPERVISOR"]))
):
    return create_product(ctx.tenant_id, data)

@router.get("")
def api_list_products(
    category: Optional[str] = None,
    search: Optional[str] = None,
    warehouse_id: Optional[str] = None,
    ctx: TenantContext = Depends(get_current_tenant_context)
):
    return list_products(ctx.tenant_id, category=category, search=search, warehouse_id=warehouse_id)

@router.get("/{product_id}")
def api_get_product(
    product_id: str,
    ctx: TenantContext = Depends(get_current_tenant_context)
):
    return get_product(ctx.tenant_id, product_id)
