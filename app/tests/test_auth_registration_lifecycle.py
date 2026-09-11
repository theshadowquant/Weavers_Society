import os
os.environ.setdefault("SOCIETY_DB_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "test_society.db"))
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from fastapi.testclient import TestClient
from app.main import app
from app.database.session import init_db, get_db

client = TestClient(app)

def test_full_registration_auth_and_switching_lifecycle():
    init_db(force=True)
    
    # 1. Register brand new Society A
    reg_payload_a = {
        "primary_phone": "9845011111",
        "primary_email": "secretary@mysuruweavers.coop",
        "admin_password": "securepassword123",
        "admin_full_name": "Nagaraj Rao",
        "legal_name_en": "Mysuru Traditional Silk Weavers Co-op Society Ltd",
        "legal_name_kn": "ಮೈಸೂರು ಸಾಂಪ್ರದಾಯಿಕ ರೇಷ್ಮೆ ನೇಕಾರರ ಸಹಕಾರ ಸಂಘ ನಿಯಮಿತ",
        "registration_number": "DR/KCS/MYS/2026/089",
        "registration_date": "2026-01-15",
        "society_type": "PRIMARY_WEAVERS_COOP",
        "district": "Mysuru",
        "taluk": "Mysuru",
        "hobli_village": "Nanjangud",
        "pincode": "571301",
        "registered_office_address": "Weavers Complex, Nanjangud Road, Mysuru",
        "members_count": 60,
        "active_looms_count": 45,
        "preferred_language": "kn"
    }
    
    res_reg = client.post("/api/v1/onboarding/finalize", json=reg_payload_a)
    assert res_reg.status_code == 200, f"Registration failed: {res_reg.text}"
    data_reg = res_reg.json()
    tenant_a_id = data_reg["tenant_id"]
    user_a_id = data_reg["admin_user_id"]
    slug_a = data_reg["slug"]
    
    # Verify Tenant A starts completely empty
    with get_db() as conn:
        cursor = conn.cursor()
        for tbl in ["weaver_members", "products", "yarn_lots", "inventory_ledger", "sales_transactions", "purchase_invoices"]:
            cursor.execute(f"SELECT COUNT(*) as c FROM {tbl} WHERE tenant_id = ?", (tenant_a_id,))
            assert cursor.fetchone()["c"] == 0, f"Tenant A was polluted with records in {tbl}!"
            
        # Verify 4 storage nodes exist for Tenant A
        cursor.execute("SELECT storage_type FROM warehouses WHERE tenant_id = ?", (tenant_a_id,))
        nodes = {r["storage_type"] for r in cursor.fetchall()}
        assert nodes == {"RAW_YARN_GODOWN", "WEAVER_CUSTODY_WIP", "FINISHED_SHOWROOM", "WHOLESALE_DEPOT"}

    # 2. Login with registered phone & password
    login_res = client.post("/api/v1/auth/login", json={
        "identifier": "9845011111",
        "password": "securepassword123"
    })
    assert login_res.status_code == 200
    auth_data = login_res.json()
    token = auth_data["access_token"]
    assert auth_data["user_id"] == user_a_id
    assert auth_data["tenant_id"] == tenant_a_id
    assert auth_data["role"] == "SECRETARY"
    assert len(auth_data["authorized_tenants"]) == 1
    assert auth_data["authorized_tenants"][0]["tenant_id"] == tenant_a_id

    # 3. Access current profile /me
    me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["user"]["phone"] == "9845011111"
    assert me_data["active_tenant"]["id"] == tenant_a_id

    # 4. Fetch dynamically provisioned warehouses
    wh_res = client.get("/api/v1/inventory/warehouses", headers={"Authorization": f"Bearer {token}"})
    assert wh_res.status_code == 200
    whs = wh_res.json()
    assert len(whs) == 4
    showroom = next(w for w in whs if w["storage_type"] == "FINISHED_SHOWROOM")
    assert showroom["tenant_id"] == tenant_a_id

    # 5. Test invalid credentials
    bad_login = client.post("/api/v1/auth/login", json={
        "identifier": "9845011111",
        "password": "wrongpassword"
    })
    assert bad_login.status_code == 401

    # 6. Test Multi-Society Membership & Context Switching
    # Bind user_a to a second society: Society B
    import uuid
    tenant_b_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute("""
            INSERT INTO tenants (id, slug, legal_name_en, legal_name_kn, registration_number, registration_date, district, taluk, hobli_village, pincode, primary_phone, registered_office_address, status)
            VALUES (?, 'chamarajanagar-silk', 'Chamarajanagar Silk Co-op', 'ಚಾಮರಾಜನಗರ ರೇಷ್ಮೆ ಸಂಘ', 'DR/KCS/CHN/2026/001', '2026-02-01', 'Chamarajanagar', 'Chamarajanagar', 'Town', '571313', '9845022222', 'Main Road', 'ACTIVE')
        """, (tenant_b_id,))
        conn.execute("""
            INSERT INTO user_tenant_roles (id, user_id, tenant_id, role)
            VALUES (?, ?, ?, 'ACCOUNTANT')
        """, (str(uuid.uuid4()), user_a_id, tenant_b_id))
        
    # Login again: should now return 2 authorized tenants
    login_multi = client.post("/api/v1/auth/login", json={
        "identifier": "9845011111",
        "password": "securepassword123"
    })
    assert login_multi.status_code == 200
    multi_data = login_multi.json()
    assert len(multi_data["authorized_tenants"]) == 2
    
    # Authorized switch to Tenant B
    switch_res = client.post(
        "/api/v1/auth/switch-tenant",
        json={"target_tenant_id": tenant_b_id},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert switch_res.status_code == 200
    switch_data = switch_res.json()
    assert switch_data["tenant_id"] == tenant_b_id
    assert switch_data["role"] == "ACCOUNTANT"

    # Unauthorized switch to a random third tenant
    fake_tenant_id = str(uuid.uuid4())
    unauth_switch = client.post(
        "/api/v1/auth/switch-tenant",
        json={"target_tenant_id": fake_tenant_id},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert unauth_switch.status_code == 403

    print("Full registration, auth, clean tenant, and switching lifecycle tests passed!")

if __name__ == "__main__":
    test_full_registration_auth_and_switching_lifecycle()
