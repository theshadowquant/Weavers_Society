from fastapi import APIRouter, HTTPException, Depends, status
from app.database.session import get_db
from app.models.schemas import (
    LoginRequest,
    TokenResponse,
    TenantMembership,
    SwitchTenantRequest,
    FirebaseLoginRequest,
    FirebaseCustomTokenResponse
)
from app.core.security import verify_password, create_access_token
from app.core.tenant_context import TenantContext, get_current_tenant_context
from app.core.audit import log_audit_event
from app.core.firebase import (
    verify_firebase_id_token,
    create_firebase_custom_token,
    is_firebase_available
)

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

@router.post("/firebase-login", response_model=TokenResponse)
def firebase_login(data: FirebaseLoginRequest):
    """
    Authenticates a user via Firebase Authentication ID token (from Firebase Phone OTP,
    Google Sign-in, or Firebase client auth).
    Validates token, matches/links user, and issues cooperative tenant session JWT.
    """
    if not is_firebase_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Firebase Authentication service is not available or configured."
        )

    try:
        decoded = verify_firebase_id_token(data.id_token)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Firebase ID token: {str(e)}"
        )

    firebase_uid = decoded.get("uid")
    phone_number = decoded.get("phone_number")
    email = decoded.get("email")

    with get_db() as conn:
        cursor = conn.cursor()

        # 1. Match user by firebase_uid, phone, or email
        user = None
        if firebase_uid:
            cursor.execute("SELECT * FROM users WHERE firebase_uid = ?", (firebase_uid,))
            user = cursor.fetchone()

        if not user and phone_number:
            clean_phone = phone_number.replace("+91", "").strip()
            cursor.execute("""
                SELECT * FROM users 
                WHERE phone = ? OR phone = ? OR phone = ?
            """, (phone_number, clean_phone, f"+91{clean_phone}"))
            user = cursor.fetchone()

        if not user and email:
            cursor.execute("SELECT * FROM users WHERE email = ?", (email.lower(),))
            user = cursor.fetchone()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No cooperative society account found for this Firebase identity. Please register or contact your society Secretary."
            )

        # 2. Link firebase_uid if not already linked
        if not user["firebase_uid"] and firebase_uid:
            cursor.execute("UPDATE users SET firebase_uid = ? WHERE id = ?", (firebase_uid, user["id"]))

        if not user["is_active"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive.")

        # 3. Retrieve authorized tenant societies
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

        # 4. Resolve active society context
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
            "contact": user["email"] or user["phone"] or phone_number or email
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
            action="FIREBASE_USER_LOGIN",
            entity_type="users",
            entity_id=user["id"],
            user_id=user["id"],
            new_values={"firebase_uid": firebase_uid, "role": matched["role"], "society": matched["tenant_slug"]}
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

@router.get("/firebase-token", response_model=FirebaseCustomTokenResponse)
def get_firebase_custom_token(ctx: TenantContext = Depends(get_current_tenant_context)):
    """
    Generates a cryptographically signed Firebase Custom Token for the authenticated user,
    including their active tenant context claims. Enables web/mobile clients to authenticate
    directly with Firebase SDK (Firestore, Cloud Storage) with society security rules.
    """
    if not is_firebase_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Firebase is not connected or initialized."
        )

    try:
        from app.core.firebase import get_firebase_status
        status_info = get_firebase_status()
        custom_token = create_firebase_custom_token(
            uid=ctx.user_id,
            additional_claims={
                "tenant_id": ctx.tenant_id,
                "role": ctx.role,
                "email_or_phone": ctx.email_or_phone
            }
        )
        return FirebaseCustomTokenResponse(
            custom_token=custom_token,
            project_id=status_info.get("project_id", "weaver-society"),
            user_id=ctx.user_id,
            tenant_id=ctx.tenant_id,
            role=ctx.role
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate Firebase custom token: {str(e)}"
        )

