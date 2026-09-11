import os
os.environ.setdefault("SOCIETY_DB_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "test_society.db"))
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from fastapi.testclient import TestClient
from app.main import app
from app.database.seed import seed_database
from app.core.security import create_access_token

client = TestClient(app)

def setup_module():
    seed_database()

def test_first_principles_cross_tenant_isolation():
    """
    NON-NEGOTIABLE RULE:
    Society A (Gadag Weavers Co-op) must NEVER access Society B (Ilkal Sari Co-op) records.
    """
    tenant_1_id = "11111111-1111-1111-1111-111111111111" # Gadag
    tenant_2_id = "22222222-2222-2222-2222-222222222222" # Ilkal
    
    token_1 = create_access_token({
        "sub": "aaaa1111-1111-1111-1111-111111111111",
        "tenant_id": tenant_1_id,
        "role": "SECRETARY"
    })
    token_2 = create_access_token({
        "sub": "bbbb2222-2222-2222-2222-222222222222",
        "tenant_id": tenant_2_id,
        "role": "MANAGING_DIRECTOR"
    })
    
    headers_1 = {"Authorization": f"Bearer {token_1}"}
    headers_2 = {"Authorization": f"Bearer {token_2}"}
    
    # 1. Operational Command Center Isolation
    cmd_1 = client.get("/api/v1/dashboard/command-center", headers=headers_1)
    assert cmd_1.status_code == 200
    assert cmd_1.json()["weavers_summary"]["registered_weavers"] == 2
    
    cmd_2 = client.get("/api/v1/dashboard/command-center", headers=headers_2)
    assert cmd_2.status_code == 200
    assert cmd_2.json()["weavers_summary"]["registered_weavers"] == 0 # Ilkal has 0 weavers in seed
    
    # 2. Weaver Ecosystem Isolation
    weavers_1 = client.get("/api/v1/weavers", headers=headers_1)
    assert weavers_1.status_code == 200
    assert len(weavers_1.json()) == 2
    assert weavers_1.json()[0]["membership_no"] == "MBR/GDG/001"
    
    weavers_2 = client.get("/api/v1/weavers", headers=headers_2)
    assert weavers_2.status_code == 200
    assert len(weavers_2.json()) == 0, "Leakage: Society 2 saw Society 1's weavers!"
    
    # 3. Direct Profile Fetch by ID should return 404 for other society
    w1_id = "w1-1111-1111-1111-111111111111"
    cross_profile = client.get(f"/api/v1/weavers/{w1_id}/profile", headers=headers_2)
    assert cross_profile.status_code == 404, "Security violation: Cross-tenant weaver fetch did not return 404!"
    
    # 4. Inventory Status Isolation
    inv_1 = client.get("/api/v1/inventory/status", headers=headers_1)
    assert inv_1.status_code == 200
    assert any("GDG-COT" in p["sku"] for p in inv_1.json()["showroom_stock"])
    assert not any("ILK-TOPE" in p["sku"] for p in inv_1.json()["showroom_stock"])

    inv_2 = client.get("/api/v1/inventory/status", headers=headers_2)
    assert inv_2.status_code == 200
    assert any("ILK-TOPE" in p["sku"] for p in inv_2.json()["showroom_stock"])
    assert not any("GDG-COT" in p["sku"] for p in inv_2.json()["showroom_stock"])

    print("First-principles cross-tenant isolation test passed!")

if __name__ == "__main__":
    setup_module()
    test_first_principles_cross_tenant_isolation()
