from fastapi import APIRouter, HTTPException, status
from app.database.session import get_db
from app.models.schemas import LoginRequest, TokenResponse
from app.core.security import verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest):
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Look up user by email or phone
        cursor.execute("""
            SELECT u.*, utr.tenant_id, utr.role, t.slug as tenant_slug, 
                   t.legal_name_en as tenant_name_en, t.legal_name_kn as tenant_name_kn,
                   t.district, t.status as tenant_status
            FROM users u
            JOIN user_tenant_roles utr ON utr.user_id = u.id
            JOIN tenants t ON t.id = utr.tenant_id
            WHERE (u.email = ? OR u.phone = ?)
        """, (data.identifier, data.identifier))
        rows = cursor.fetchall()
        
        if not rows:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")
            
        # If tenant_slug provided, match specifically, else select first active tenant
        matched_row = None
        if data.tenant_slug:
            for r in rows:
                if r["tenant_slug"] == data.tenant_slug:
                    matched_row = r
                    break
        else:
            matched_row = rows[0]
            
        if not matched_row or not verify_password(data.password, matched_row["password_hash"]):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")
            
        if not matched_row["is_active"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive.")
            
        if matched_row["tenant_status"] not in ("ACTIVE", "TRIAL"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Society account is suspended.")
            
        token_payload = {
            "sub": matched_row["id"],
            "tenant_id": matched_row["tenant_id"],
            "role": matched_row["role"],
            "contact": matched_row["email"] or matched_row["phone"]
        }
        token = create_access_token(token_payload)
        
        return TokenResponse(
            access_token=token,
            token_type="bearer",
            user_id=matched_row["id"],
            tenant_id=matched_row["tenant_id"],
            tenant_slug=matched_row["tenant_slug"],
            tenant_name_en=matched_row["tenant_name_en"],
            tenant_name_kn=matched_row["tenant_name_kn"],
            district=matched_row["district"] or "Karnataka",
            role=matched_row["role"],
            preferred_language=matched_row["preferred_language"] or "kn"
        )
