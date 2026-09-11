import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from fastapi.testclient import TestClient
from app.main import app
from app.database.session import init_db, get_db

client = TestClient(app)

def test_rigorous_cross_tenant_security_isolation():
    init_db(force=True)
    
    # 1. Onboard Society A: Kaveri Handloom Co-op
    res_a = client.post("/api/v1/onboarding/finalize", json={
        "primary_phone": "9900111111",
        "primary_email": "secretary@kaveri.coop",
        "admin_password": "passwordA123",
        "admin_full_name": "Secretary Kaveri",
        "legal_name_en": "Kaveri Handloom Weavers Co-operative Society Ltd",
        "legal_name_kn": "ಕಾವೇರಿ ಕೈಮಗ್ಗ ನೇಕಾರರ ಸಹಕಾರ ಸಂಘ ನಿಯಮಿತ",
        "registration_number": "DR/KCS/KAV/2026/001",
        "registration_date": "2026-01-01",
        "district": "Mandya",
        "taluk": "Srirangapatna",
        "hobli_village": "Arakere",
        "pincode": "571415",
        "registered_office_address": "Main Road, Srirangapatna",
        "members_count": 40,
        "active_looms_count": 30
    })
    assert res_a.status_code == 200
    tenant_a_id = res_a.json()["tenant_id"]
    
    # 2. Onboard Society B: Tungabhadra Handloom Co-op
    res_b = client.post("/api/v1/onboarding/finalize", json={
        "primary_phone": "9900222222",
        "primary_email": "secretary@tunga.coop",
        "admin_password": "passwordB123",
        "admin_full_name": "Secretary Tunga",
        "legal_name_en": "Tungabhadra Handloom Weavers Co-operative Society Ltd",
        "legal_name_kn": "ತುಂಗಭದ್ರಾ ಕೈಮಗ್ಗ ನೇಕಾರರ ಸಹಕಾರ ಸಂಘ ನಿಯಮಿತ",
        "registration_number": "DR/KCS/TUN/2026/002",
        "registration_date": "2026-01-01",
        "district": "Ballari",
        "taluk": "Hospet",
        "hobli_village": "Kampli",
        "pincode": "583132",
        "registered_office_address": "Station Road, Kampli",
        "members_count": 50,
        "active_looms_count": 40
    })
    assert res_b.status_code == 200
    tenant_b_id = res_b.json()["tenant_id"]
    
    # 3. Authenticate User A and User B
    login_a = client.post("/api/v1/auth/login", json={"identifier": "9900111111", "password": "passwordA123"})
    assert login_a.status_code == 200
    token_a = login_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}
    
    login_b = client.post("/api/v1/auth/login", json={"identifier": "9900222222", "password": "passwordB123"})
    assert login_b.status_code == 200
    token_b = login_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}
    
    # 4. Resolve Warehouses for A and B
    whs_a = client.get("/api/v1/inventory/warehouses", headers=headers_a).json()
    wh_a_showroom = next(w["id"] for w in whs_a if w["storage_type"] == "FINISHED_SHOWROOM")
    
    whs_b = client.get("/api/v1/inventory/warehouses", headers=headers_b).json()
    wh_b_showroom = next(w["id"] for w in whs_b if w["storage_type"] == "FINISHED_SHOWROOM")
    assert wh_a_showroom != wh_b_showroom
    
    # 5. Create Weaver A in Society A & Weaver B in Society B
    res_w_a = client.post("/api/v1/weavers", headers=headers_a, json={
        "membership_no": "MBR/KAV/001",
        "full_name_en": "Channappa Kaveri",
        "full_name_kn": "ಚನ್ನಪ್ಪ ಕಾವೇರಿ",
        "village": "Arakere",
        "taluk": "Srirangapatna",
        "loom_type": "FRAME_LOOM",
        "active_looms_count": 1
    })
    assert res_w_a.status_code == 200
    weaver_a_id = res_w_a.json()["id"]

    res_w_b = client.post("/api/v1/weavers", headers=headers_b, json={
        "membership_no": "MBR/TUN/001",
        "full_name_en": "Basappa Tunga",
        "full_name_kn": "ಬಸಪ್ಪ ತುಂಗ",
        "village": "Kampli",
        "taluk": "Hospet",
        "loom_type": "PIT_LOOM",
        "active_looms_count": 2
    })
    assert res_w_b.status_code == 200
    weaver_b_id = res_w_b.json()["id"]

    # 6. Create Product A in Society A & Product B in Society B
    res_p_a = client.post("/api/v1/products", headers=headers_a, json={
        "sku": "KAV-SARI-01",
        "name_en": "Kaveri Cotton Sari",
        "name_kn": "ಕಾವೇರಿ ಹತ್ತಿ ಸೀರೆ",
        "category": "SARI",
        "retail_rate": 1200.0,
        "wholesale_rate": 950.0
    })
    assert res_p_a.status_code == 200
    prod_a_id = res_p_a.json()["id"]

    res_p_b = client.post("/api/v1/products", headers=headers_b, json={
        "sku": "TUN-SILK-01",
        "name_en": "Tungabhadra Silk Sari",
        "name_kn": "ತುಂಗಭದ್ರಾ ರೇಷ್ಮೆ ಸೀರೆ",
        "category": "SARI",
        "retail_rate": 4500.0,
        "wholesale_rate": 3800.0
    })
    assert res_p_b.status_code == 200
    prod_b_id = res_p_b.json()["id"]

    # =========================================================================
    # STRICT CROSS-TENANT PENETRATION ATTEMPTS: ALL MUST BE REJECTED
    # =========================================================================
    
    # 7. User A attempts to view Weaver B -> MUST BE 404
    att_1 = client.get(f"/api/v1/weavers/{weaver_b_id}/profile", headers=headers_a)
    assert att_1.status_code == 404, "Breach: User A accessed Weaver B profile!"

    # 8. User B attempts to view Weaver A -> MUST BE 404
    att_2 = client.get(f"/api/v1/weavers/{weaver_a_id}/profile", headers=headers_b)
    assert att_2.status_code == 404, "Breach: User B accessed Weaver A profile!"

    # 9. User A listing weavers -> MUST NOT SEE Weaver B
    list_weavers_a = client.get("/api/v1/weavers", headers=headers_a).json()
    assert len(list_weavers_a) == 1
    assert list_weavers_a[0]["id"] == weaver_a_id
    assert not any(w["id"] == weaver_b_id for w in list_weavers_a), "Breach: User A saw Weaver B in list!"

    # 10. User A attempts to view Product B -> MUST BE 404
    att_3 = client.get(f"/api/v1/products/{prod_b_id}", headers=headers_a)
    assert att_3.status_code == 404, "Breach: User A accessed Product B!"

    # 11. User A attempts to submit sale billing Product B -> MUST BE 404
    att_4 = client.post("/api/v1/sales/transactions", headers=headers_a, json={
        "sale_channel": "RETAIL_SHOWROOM",
        "warehouse_id": wh_a_showroom,
        "customer_name": "Cross Attacker",
        "items": [{"product_id": prod_b_id, "quantity": 1}]
    })
    assert att_4.status_code in (400, 404), "Breach: User A billed another society's product!"

    # 12. User A attempts to bill against Society B's warehouse -> MUST BE REJECTED
    att_5 = client.post("/api/v1/sales/transactions", headers=headers_a, json={
        "sale_channel": "RETAIL_SHOWROOM",
        "warehouse_id": wh_b_showroom,
        "customer_name": "Cross Warehouse Attacker",
        "items": [{"product_id": prod_a_id, "quantity": 1}]
    })
    assert att_5.status_code in (400, 404, 500), "Breach: User A operated on Society B warehouse!"

    # 13. User A attempts unauthorized switch-tenant to Society B -> MUST BE 403
    att_6 = client.post(
        "/api/v1/auth/switch-tenant",
        headers=headers_a,
        json={"target_tenant_id": tenant_b_id}
    )
    assert att_6.status_code == 403, "Breach: User A switched into unauthorized Society B!"

    # 14. User B attempts unauthorized switch-tenant to Society A -> MUST BE 403
    att_7 = client.post(
        "/api/v1/auth/switch-tenant",
        headers=headers_b,
        json={"target_tenant_id": tenant_a_id}
    )
    assert att_7.status_code == 403, "Breach: User B switched into unauthorized Society A!"

    # 15. Reports Daybook Isolation
    db_a = client.get("/api/v1/reports/daybook", headers=headers_a).json()
    assert db_a["total_receipts"] == 0.0
    db_b = client.get("/api/v1/reports/daybook", headers=headers_b).json()
    assert db_b["total_receipts"] == 0.0

    print("Rigorous cross-tenant security isolation tests passed completely: 100% tenant boundaries enforced!")

if __name__ == "__main__":
    test_rigorous_cross_tenant_security_isolation()
