from fastapi import APIRouter, Depends, HTTPException, status
from app.core.firebase import get_firebase_status, is_firebase_available
from app.core.tenant_context import get_current_tenant_context, TenantContext, require_roles
from app.database.session import get_db
from app.services.firebase_sync_service import sync_tenant_to_firestore

router = APIRouter(prefix="/system", tags=["System & Cloud Services"])

@router.get("/firebase-status")
def check_firebase_status():
    """Returns the live connection status of Firebase and Cloud Firestore."""
    return get_firebase_status()

@router.post("/firebase-sync")
def trigger_firebase_sync(
    ctx: TenantContext = Depends(get_current_tenant_context),
    _role: TenantContext = Depends(require_roles(["SECRETARY", "MANAGING_DIRECTOR", "ACCOUNTANT"]))
):
    """Syncs the current cooperative society's data to Firebase Cloud Firestore."""
    if not is_firebase_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Firebase is not connected or initialized"
        )
    
    with get_db() as conn:
        result = sync_tenant_to_firestore(ctx.tenant_id, conn)
    return result
