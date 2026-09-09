from fastapi.testclient import TestClient
from app.main import app
from app.database.seed import seed_database
from app.core.security import create_access_token

client = TestClient(app)

def setup_module():
    seed_database()

def test_government_rebate_calculation_and_claim():
    """
    Validates that:
    1. 20% Festival Rebate correctly reduces customer net payable.
    2. Rebate amount is recorded as govt_subsidy_receivable.
    3. Tax is calculated accurately.
    4. The Directorate Rebate Claim Register contains the transaction.
    """
    tenant_1_id = "11111111-1111-1111-1111-111111111111"
    token = create_access_token({
        "sub": "aaaa1111-1111-1111-1111-111111111111",
        "tenant_id": tenant_1_id,
        "role": "SOCIETY_ADMIN"
    })
    headers = {"Authorization": f"Bearer {token}"}
    
    prod_id = "p1-1111-1111-1111-111111111111" # Retail rate = 1450.00, GST = 5%
    wh_id = "wh1-store-1111-1111-111111111111"
    
    # Buy 2 Saris with 20% Festival Rebate
    # Gross = 2 * 1450 = 2900.00
    # Rebate (20%) = 580.00
    # Taxable = 2900 - 580 = 2320.00
    # GST (5%) = 116.00
    # Net Customer Payable = 2320 + 116 = 2436.00
    # Govt Subsidy Receivable = 580.00
    
    sale_payload = {
        "sale_type": "RETAIL",
        "warehouse_id": wh_id,
        "customer_name": "Smt. Sharda Devi",
        "customer_phone": "9845112233",
        "apply_govt_rebate": True,
        "payment_mode": "CASH",
        "items": [
            {
                "product_id": prod_id,
                "quantity": 2.0,
                "discount_amount": 0.0
            }
        ]
    }
    
    res = client.post("/api/v1/sales/transactions", json=sale_payload, headers=headers)
    assert res.status_code == 200
    data = res.json()
    
    assert data["gross_amount"] == 2900.00
    assert data["rebate_amount"] == 580.00
    assert data["tax_amount"] == 116.00
    assert data["net_payable"] == 2436.00
    assert data["govt_subsidy_receivable"] == 580.00
    
    # Verify Directorate Claims Register
    res_claims = client.get("/api/v1/reports/rebate-claims", headers=headers)
    assert res_claims.status_code == 200
    claims_data = res_claims.json()
    assert claims_data["total_claimable_amount"] >= 580.00
    assert any(c["customer_name"] == "Smt. Sharda Devi" for c in claims_data["claims"])

if __name__ == "__main__":
    setup_module()
    test_government_rebate_calculation_and_claim()
    print("Government rebate calculation & claim test passed successfully!")
