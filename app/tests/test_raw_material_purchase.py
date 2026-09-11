import os
os.environ.setdefault("SOCIETY_DB_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "test_society.db"))
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from fastapi.testclient import TestClient
from app.main import app
from app.core.security import create_access_token

client = TestClient(app)

TENANT_ID = "33333333-3333-3333-3333-333333333333"
USER_ID = "cccc3333-3333-3333-3333-333333333333"

def get_auth_headers():
    token = create_access_token({
        "sub": USER_ID,
        "tenant_id": TENANT_ID,
        "role": "SECRETARY",
        "contact": "lekhan@shadowquant.coop"
    })
    return {"Authorization": f"Bearer {token}"}

def test_raw_material_purchase_and_inventory_flow():
    headers = get_auth_headers()

    # 1. Create a supplier
    sup_res = client.post(
        "/api/v1/purchases/suppliers",
        json={
            "name": "Karnataka Apex Co-operative Cotton Yarn Depot",
            "supplier_type": "YARN_MILL",
            "contact_person": "Mallikarjun",
            "phone": "9845112233",
            "gstin": "29AAACK1234F1Z5"
        },
        headers=headers
    )
    assert sup_res.status_code == 200
    supplier_id = sup_res.json()["id"]

    # 2. Inward a raw material purchase invoice with auto_post=True
    import uuid
    uid = uuid.uuid4().hex[:6]
    lot_number = f"LOT-TEST-{uid}"
    inv_res = client.post(
        "/api/v1/purchases/invoices",
        json={
            "supplier_id": supplier_id,
            "invoice_no": f"APEX-INV-{uid}",
            "society_entry_no": f"INW-TEST-{uid}",
            "invoice_date": "2026-09-11",
            "auto_post": True,
            "items": [
                {
                    "lot_number": lot_number,
                    "yarn_type": "COTTON",
                    "count_spec": "2/60s Combed Cotton Hank",
                    "mill_name": "Gokak Mills",
                    "shade_code": "Bleached White",
                    "quantity": 100.0,
                    "unit_cost": 385.0,
                    "tax_rate": 5.0
                }
            ]
        },
        headers=headers
    )
    assert inv_res.status_code == 200
    inv_data = inv_res.json()
    assert inv_data["status"] == "POSTED"

    # 3. Verify stock shows up in Central Yarn Godown
    status_res = client.get("/api/v1/inventory/status", headers=headers)
    assert status_res.status_code == 200
    raw_yarn = status_res.json()["raw_yarn_godown"]
    matched_lot = next((y for y in raw_yarn if y["lot_number"] == lot_number), None)
    assert matched_lot is not None
    assert matched_lot["stock_kgs"] == 100.0
    assert matched_lot["count_spec"] == "2/60s Combed Cotton Hank"

    # 4. Verify stock movement journal entry
    journal_res = client.get("/api/v1/inventory/journal", headers=headers)
    assert journal_res.status_code == 200
    journal = journal_res.json()
    inward_movements = [j for j in journal if j["movement_type"] == "PURCHASE_YARN_INWARD"]
    assert len(inward_movements) > 0
    assert inward_movements[0]["quantity_delta"] == 100.0

    # 5. Verify purchases list includes invoice with items
    list_res = client.get("/api/v1/purchases/invoices", headers=headers)
    assert list_res.status_code == 200
    purchases = list_res.json()
    matched_inv = next((p for p in purchases if p["invoice_no"] == f"APEX-INV-{uid}"), None)
    assert matched_inv is not None
    assert matched_inv["status"] == "POSTED"
    assert len(matched_inv["items"]) == 1
    assert matched_inv["items"][0]["quantity_kgs"] == 100.0
    print("[PASS] Raw material purchase and inventory flow test passed successfully!")

if __name__ == "__main__":
    test_raw_material_purchase_and_inventory_flow()
