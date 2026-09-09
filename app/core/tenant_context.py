from dataclasses import dataclass
from typing import Optional, List
from fastapi import Header, HTTPException, Depends, status
from app.core.security import decode_access_token
from app.database.session import get_db

@dataclass
class TenantContext:
    user_id: str
    tenant_id: str
    role: str
    email_or_phone: str
    preferred_language: str

def get_current_tenant_context(
    authorization: Optional[str] = Header(None)
) -> TenantContext:
    """
    Tenant Context Guard:
    1. Validates JWT Bearer token signature and expiration.
    2. Strictly extracts tenant_id, user_id, and role from the server-validated JWT payload.
    3. Confirms user-tenant active binding against the database.
    4. Rejects any attempt to spoof or alter tenant context from the client side.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header. Must be 'Bearer <token>'."
        )
        
    token = authorization.split(" ")[1]
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token."
        )
        
    user_id = payload.get("sub")
    tenant_id = payload.get("tenant_id")
    role = payload.get("role")
    
    if not user_id or not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token does not contain valid tenant authorization."
        )
        
    # Verify binding against database to guarantee real-time revocation support
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.is_active, u.preferred_language, utr.role, t.status
            FROM users u
            JOIN user_tenant_roles utr ON utr.user_id = u.id AND utr.tenant_id = ?
            JOIN tenants t ON t.id = utr.tenant_id
            WHERE u.id = ?
        """, (tenant_id, user_id))
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User does not have authorized access to this society tenant."
            )
            
        if not row["is_active"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is deactivated.")
            
        if row["status"] != "ACTIVE" and row["status"] != "TRIAL":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Society tenant account is suspended or archived.")
            
        return TenantContext(
            user_id=user_id,
            tenant_id=tenant_id,
            role=row["role"],
            email_or_phone=payload.get("contact", ""),
            preferred_language=row["preferred_language"] or "kn"
        )

def require_roles(allowed_roles: List[str]):
    """Role-Based Access Control decorator/dependency."""
    def role_checker(ctx: TenantContext = Depends(get_current_tenant_context)) -> TenantContext:
        if ctx.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted for role '{ctx.role}'. Required: {allowed_roles}"
            )
        return ctx
    return role_checker
