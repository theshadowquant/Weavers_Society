import uuid
import json
import re
from typing import Dict, Any, Optional
from fastapi import HTTPException
from app.database.session import get_db
from app.models.schemas import OnboardingStepSave, OnboardingFinalizeRequest
from app.core.security import hash_password
from app.core.audit import log_audit_event

def _generate_slug(name: str) -> str:
    slug = re.sub(r'[^a-zA-Z0-9\s-]', '', name).strip().lower()
    slug = re.sub(r'[\s-]+', '-', slug)
    return slug or f"society-{uuid.uuid4().hex[:6]}"

def save_onboarding_draft(data: OnboardingStepSave) -> Dict[str, Any]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, form_data_json FROM tenant_onboarding_drafts WHERE contact_identifier = ? AND is_completed = 0", (data.contact_identifier,))
        existing = cursor.fetchone()
        
        if existing:
            draft_id = existing["id"]
            merged_data = json.loads(existing["form_data_json"] or "{}")
            merged_data.update(data.form_data)
            conn.execute("""
                UPDATE tenant_onboarding_drafts
                SET current_step = ?, form_data_json = ?, updated_at = datetime('now')
                WHERE id = ?
            """, (data.current_step, json.dumps(merged_data), draft_id))
        else:
            draft_id = str(uuid.uuid4())
            conn.execute("""
                INSERT INTO tenant_onboarding_drafts (id, contact_identifier, current_step, form_data_json)
                VALUES (?, ?, ?, ?)
            """, (draft_id, data.contact_identifier, data.current_step, json.dumps(data.form_data)))
            
        return {"draft_id": draft_id, "current_step": data.current_step, "status": "SAVED"}

def get_onboarding_draft(contact_identifier: str) -> Dict[str, Any]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tenant_onboarding_drafts WHERE contact_identifier = ? AND is_completed = 0 ORDER BY updated_at DESC LIMIT 1", (contact_identifier,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="No active onboarding draft found.")
        return {
            "draft_id": row["id"],
            "contact_identifier": row["contact_identifier"],
            "current_step": row["current_step"],
            "form_data": json.loads(row["form_data_json"] or "{}")
        }

def finalize_society_onboarding(data: OnboardingFinalizeRequest) -> Dict[str, Any]:
    tenant_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    slug = data.slug or _generate_slug(data.legal_name_en)
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM tenants WHERE slug = ?", (slug,))
        if cursor.fetchone():
            slug = f"{slug}-{uuid.uuid4().hex[:4]}"
            
        cursor.execute("SELECT id FROM tenants WHERE registration_number = ?", (data.registration_number,))
        if cursor.fetchone():
            data.registration_number = f"{data.registration_number}-{uuid.uuid4().hex[:4]}"
            
        # 1. Insert Tenant Record
        conn.execute("""
            INSERT INTO tenants (
                id, slug, legal_name_en, legal_name_kn, registration_number,
                registration_date, society_type, district, taluk, hobli_village,
                pincode, primary_phone, primary_email, registered_office_address,
                pan, gstin, directorate_society_code, bank_name, bank_account_no, bank_ifsc,
                members_count, active_looms_count, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE')
        """, (
            tenant_id, slug, data.legal_name_en, data.legal_name_kn, data.registration_number,
            data.registration_date, data.society_type, data.district, data.taluk, data.hobli_village,
            data.pincode, data.primary_phone, data.primary_email, data.registered_office_address,
            data.pan, data.gstin, data.directorate_society_code, data.bank_name, data.bank_account_no, data.bank_ifsc,
            data.members_count, data.active_looms_count
        ))
        
        # 2. Insert or Resolve Society Administrator
        cursor.execute("SELECT id FROM users WHERE phone = ?", (data.primary_phone,))
        existing_user = cursor.fetchone()
        if existing_user:
            user_id = existing_user["id"]
        else:
            pw_hash = hash_password(data.admin_password)
            conn.execute("""
                INSERT INTO users (id, email, phone, full_name, password_hash, preferred_language)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, data.primary_email, data.primary_phone, data.admin_full_name, pw_hash, data.preferred_language))
        
        # 3. Bind Role: SECRETARY / MANAGING_DIRECTOR
        conn.execute("""
            INSERT INTO user_tenant_roles (id, user_id, tenant_id, role)
            VALUES (?, ?, ?, 'SECRETARY')
        """, (str(uuid.uuid4()), user_id, tenant_id))
        
        # 4. Provision Multi-State Storage Nodes
        conn.execute("""
            INSERT INTO warehouses (id, tenant_id, code, name_en, name_kn, storage_type)
            VALUES 
            (?, ?, 'RAW_YARN_DEPOT', 'Central Yarn Godown', 'ಕೇಂದ್ರ ನೂಲು ಉಗ್ರಾಣ', 'RAW_YARN_GODOWN'),
            (?, ?, 'LOOM_CUSTODY', 'Weaver Cottage Looms (WIP)', 'ನೇಕಾರರ ಮನೆ ಮಗ್ಗಗಳು (ಚಾಲ್ತಿ)', 'WEAVER_CUSTODY_WIP'),
            (?, ?, 'RETAIL_DEPOT', 'Main Society Showroom', 'ಮುಖ್ಯ ಮಾರಾಟ ಮಳಿಗೆ', 'FINISHED_SHOWROOM'),
            (?, ?, 'WHOLESALE_DEPOT', 'Apex & Bulk Contract Depot', 'ಸಗಟು ಮತ್ತು ಅಪೆಕ್ಸ್ ಡಿಪೋ', 'WHOLESALE_DEPOT')
        """, (
            str(uuid.uuid4()), tenant_id,
            str(uuid.uuid4()), tenant_id,
            str(uuid.uuid4()), tenant_id,
            str(uuid.uuid4()), tenant_id
        ))
        
        # 5. Provision Default Karnataka Directorate 20% Rebate Scheme
        conn.execute("""
            INSERT INTO scheme_configs (
                id, tenant_id, scheme_name_en, scheme_name_kn, sanctioning_authority,
                rebate_percentage, state_share_percentage, effective_from, effective_until, is_active
            ) VALUES (?, ?, 'Karnataka Handloom 20% Special Festival Rebate Scheme', 
                      'ಕರ್ನಾಟಕ ರಾಜ್ಯ 20% ವಿಶೇಷ ಹಬ್ಬದ ರಿಯಾಯಿತಿ ಯೋಜನೆ', 
                      'Directorate of Handlooms & Textiles, Govt of Karnataka',
                      20.00, 100.00, '2026-01-01', '2027-03-31', 1)
        """, (str(uuid.uuid4()), tenant_id))
        
        # 6. Mark Draft Completed if applicable
        if data.draft_id:
            conn.execute("UPDATE tenant_onboarding_drafts SET is_completed = 1 WHERE id = ?", (data.draft_id,))
            
        log_audit_event(
            conn=conn,
            tenant_id=tenant_id,
            action="SOCIETY_ONBOARDED",
            entity_type="tenants",
            entity_id=tenant_id,
            user_id=user_id,
            new_values={"legal_name_kn": data.legal_name_kn, "slug": slug}
        )
        
        return {
            "tenant_id": tenant_id,
            "slug": slug,
            "legal_name_en": data.legal_name_en,
            "legal_name_kn": data.legal_name_kn,
            "admin_user_id": user_id,
            "message": "Society digital headquarters created successfully."
        }
