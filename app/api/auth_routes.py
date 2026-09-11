from fastapi import APIRouter, HTTPException, Depends, status
from app.database.session import get_db
from app.models.schemas import LoginRequest, TokenResponse, TenantMembership, SwitchTenantRequest
from app.core.security import verify_password, create_access_token
from app.core.tenant_context import TenantContext, get_current_tenant_context
from app.core.audit import log_audit_event

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest):
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 1. Look up user by email or phone
        cursor.execute("""
            SELECT id, email, phone, full_name, password_hash, preferred_language, is_active
            FROM users
            WHERE (email = ? OR phone = ?)
        """, (data.identifier, data.identifier))
        user = cursor.fetchone()
        
        if not user or not verify_password(data.password, user["password_hash"]):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid phone/email or password.")
            
        if not user["is_active"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive.")
            
        # 2. Retrieve all active society memberships for this user
        cursor.execute("""
            SELECT utr.tenant_id, utr.role, t.slug as tenant_slug, 
                   t.legal_name_en as tenant_name_en, t.legal_name_kn as tenant_name_kn,
                   t.district, t.status as tenant_status
            FROM user_tenant_roles utr
            JOIN tenants t ON t.id = utr.tenant_id
            WHERE utr.user_id = ?
        """, (user["id"],))
        rows = cursor.fetchall()
        
        active_memberships = [r for r in rows if r["tenant_status"] in ("ACTIVE", "TRIAL")]
        if not active_memberships:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is not associated with any active society organization."
            )
            
        # 3. Resolve active society context
        matched = None
        if data.tenant_id:
            matched = next((m for m in active_memberships if m["tenant_id"] == data.tenant_id), None)
            if not matched:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User is not authorized to access the specified society."
                )
        elif data.tenant_slug:
            matched = next((m for m in active_memberships if m["tenant_slug"] == data.tenant_slug), None)
            if not matched:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User is not authorized to access the specified society."
                )
        else:
            matched = active_memberships[0]
            
        token_payload = {
            "sub": user["id"],
            "tenant_id": matched["tenant_id"],
            "role": matched["role"],
            "contact": user["email"] or user["phone"]
        }
        token = create_access_token(token_payload)
        
        authorized_tenants = [
            TenantMembership(
                tenant_id=m["tenant_id"],
                tenant_slug=m["tenant_slug"],
                tenant_name_en=m["tenant_name_en"],
                tenant_name_kn=m["tenant_name_kn"],
                role=m["role"],
                district=m["district"]
            )
            for m in active_memberships
        ]
        
        log_audit_event(
            conn=conn,
            tenant_id=matched["tenant_id"],
            action="USER_LOGIN",
            entity_type="users",
            entity_id=user["id"],
            user_id=user["id"],
            new_values={"role": matched["role"], "society": matched["tenant_slug"]}
        )
        
        return TokenResponse(
            access_token=token,
            token_type="bearer",
            user_id=user["id"],
            user_full_name=user["full_name"],
            tenant_id=matched["tenant_id"],
            tenant_slug=matched["tenant_slug"],
            tenant_name_en=matched["tenant_name_en"],
            tenant_name_kn=matched["tenant_name_kn"],
            district=matched["district"] or "Karnataka",
            role=matched["role"],
            preferred_language=user["preferred_language"] or "kn",
            authorized_tenants=authorized_tenants
        )

@router.post("/switch-tenant", response_model=TokenResponse)
def switch_tenant(
    data: SwitchTenantRequest,
    ctx: TenantContext = Depends(get_current_tenant_context)
):
    """
    Switches active tenant context strictly between societies where the authenticated user has a verified role.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Verify user has membership in target tenant
        cursor.execute("""
            SELECT utr.tenant_id, utr.role, t.slug as tenant_slug, 
                   t.legal_name_en as tenant_name_en, t.legal_name_kn as tenant_name_kn,
                   t.district, t.status as tenant_status,
                   u.full_name, u.preferred_language, u.email, u.phone
            FROM user_tenant_roles utr
            JOIN tenants t ON t.id = utr.tenant_id
            JOIN users u ON u.id = utr.user_id
            WHERE utr.user_id = ? AND utr.tenant_id = ?
        """, (ctx.user_id, data.target_tenant_id))
        target = cursor.fetchone()
        
        if not target:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Unauthorized: User does not have membership in the requested society."
            )
            
        if target["tenant_status"] not in ("ACTIVE", "TRIAL"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Target society is suspended.")
            
        token_payload = {
            "sub": ctx.user_id,
            "tenant_id": target["tenant_id"],
            "role": target["role"],
            "contact": target["email"] or target["phone"]
        }
        new_token = create_access_token(token_payload)
        
        # Get full list of authorized tenants
        cursor.execute("""
            SELECT utr.tenant_id, utr.role, t.slug as tenant_slug, 
                   t.legal_name_en as tenant_name_en, t.legal_name_kn as tenant_name_kn,
                   t.district
            FROM user_tenant_roles utr
            JOIN tenants t ON t.id = utr.tenant_id
            WHERE utr.user_id = ? AND t.status IN ('ACTIVE', 'TRIAL')
        """, (ctx.user_id,))
        all_memberships = cursor.fetchall()
        
        authorized_tenants = [
            TenantMembership(
                tenant_id=m["tenant_id"],
                tenant_slug=m["tenant_slug"],
                tenant_name_en=m["tenant_name_en"],
                tenant_name_kn=m["tenant_name_kn"],
                role=m["role"],
                district=m["district"]
            )
            for m in all_memberships
        ]
        
        log_audit_event(
            conn=conn,
            tenant_id=target["tenant_id"],
            action="TENANT_CONTEXT_SWITCHED",
            entity_type="users",
            entity_id=ctx.user_id,
            user_id=ctx.user_id,
            new_values={"switched_to": target["tenant_slug"], "role": target["role"]}
        )
        
        return TokenResponse(
            access_token=new_token,
            token_type="bearer",
            user_id=ctx.user_id,
            user_full_name=target["full_name"],
            tenant_id=target["tenant_id"],
            tenant_slug=target["tenant_slug"],
            tenant_name_en=target["tenant_name_en"],
            tenant_name_kn=target["tenant_name_kn"],
            district=target["district"] or "Karnataka",
            role=target["role"],
            preferred_language=target["preferred_language"] or "kn",
            authorized_tenants=authorized_tenants
        )

@router.get("/me")
def get_current_user_profile(ctx: TenantContext = Depends(get_current_tenant_context)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, full_name, email, phone, preferred_language FROM users WHERE id = ?", (ctx.user_id,))
        user = cursor.fetchone()
        
        cursor.execute("SELECT * FROM tenants WHERE id = ?", (ctx.tenant_id,))
        tenant = cursor.fetchone()
        
        cursor.execute("""
            SELECT utr.tenant_id, utr.role, t.slug as tenant_slug, 
                   t.legal_name_en as tenant_name_en, t.legal_name_kn as tenant_name_kn, t.district
            FROM user_tenant_roles utr
            JOIN tenants t ON t.id = utr.tenant_id
            WHERE utr.user_id = ? AND t.status IN ('ACTIVE', 'TRIAL')
        """, (ctx.user_id,))
        memberships = cursor.fetchall()
        
        return {
            "user": dict(user) if user else None,
            "active_tenant": dict(tenant) if tenant else None,
            "role": ctx.role,
            "authorized_tenants": [dict(m) for m in memberships]
        }
