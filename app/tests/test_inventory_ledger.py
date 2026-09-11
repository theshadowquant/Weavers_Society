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

def test_multi_state_inventory_ledger():
    tenant_1_id = "11111111-1111-1111-1111-111111111111"
    token = create_access_token({
        "sub": "aaaa1111-1111-1111-1111-111111111111",
        "tenant_id": tenant_1_id,
        "role": "SECRETARY"
    })
    headers = {"Authorization": f"Bearer {token}"}
    
    wh1_store = "wh1-store-1111-1111-111111111111"
    prod_id = "p1-1111-1111-1111-111111111111" # Gadag Cotton Sari (initial 32 pcs in showroom)
    
    # 1. Fetch inventory status by state
    status_res = client.get("/api/v1/inventory/status", headers=headers)
    assert status_res.status_code == 200
    data = status_res.json()
    
    # Verify Raw Yarn Godown contains cotton yarn
    assert len(data["raw_yarn_godown"]) >= 2
    assert any("NHDC" in y["lot_number"] for y in data["raw_yarn_godown"])
    
    # Verify Showroom stock has 32 saris
    sari_stock = next(p for p in data["showroom_stock"] if p["sku"] == "GDG-COT-60S-01")
    assert sari_stock["available_pieces"] == 32.0
    
    # 2. Perform Retail Sale of 2 Saris
    sale_payload = {
        "sale_channel": "RETAIL_SHOWROOM",
        "warehouse_id": wh1_store,
        "customer_name": "Rajeswari Rao",
        "apply_govt_rebate": True,
        "payment_mode": "CASH",
        "items": [{"product_id": prod_id, "quantity": 2.0, "discount_amount": 0.0}]
    }
    sale_res = client.post("/api/v1/sales/transactions", json=sale_payload, headers=headers)
    assert sale_res.status_code == 200
    
    # 3. Check stock decremented to 30.0 in ledger
    status_after = client.get("/api/v1/inventory/status", headers=headers)
    sari_stock_after = next(p for p in status_after.json()["showroom_stock"] if p["sku"] == "GDG-COT-60S-01")
    assert sari_stock_after["available_pieces"] == 30.0
    
    print("Multi-state inventory ledger test passed successfully!")

if __name__ == "__main__":
    setup_module()
    test_multi_state_inventory_ledger()
