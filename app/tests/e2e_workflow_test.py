import urllib.request
import json
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def post(url, data, token=None):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers)
    with urllib.request.urlopen(req) as res:
        return json.loads(res.read().decode('utf-8'))

def get(url, token):
    headers = {'Authorization': f'Bearer {token}'}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as res:
        return json.loads(res.read().decode('utf-8'))

def run_e2e_verification():
    base = "http://127.0.0.1:8000/api/v1"
    
    # 1. Login as Gadag Cotton Weavers Co-op
    auth_gadag = post(f"{base}/auth/login", {
        "identifier": "admin@gadag.coop",
        "password": "admin123",
        "tenant_slug": "gadag-weavers-coop"
    })
    token_gadag = auth_gadag["access_token"]
    print(f"Gadag Login OK: {auth_gadag['tenant_name_kn']} ({auth_gadag['tenant_name_en']})")
    
    # 2. Login as Ilkal Traditional Sari Weavers Co-op
    auth_ilkal = post(f"{base}/auth/login", {
        "identifier": "admin@ilkal.coop",
        "password": "admin123",
        "tenant_slug": "ilkal-sari-coop"
    })
    token_ilkal = auth_ilkal["access_token"]
    print(f"Ilkal Login OK: {auth_ilkal['tenant_name_kn']} ({auth_ilkal['tenant_name_en']})")
    
    # 3. Operational Command Center Verification
    cmd_gadag = get(f"{base}/dashboard/command-center", token_gadag)
    print("\nGADAG OPERATIONAL COMMAND CENTER PULSE:")
    print(f"  Today Collections: Rs. {cmd_gadag['today_sales']['collections']}")
    print(f"  Active Yarn with Cottage Weavers (WIP): {cmd_gadag['cottage_production']['active_yarn_with_weavers_kgs']} Kgs")
    print(f"  Unpaid Weaving Wages Balance: Rs. {cmd_gadag['weavers_summary']['total_unpaid_wages']}")
    print(f"  Weaver Welfare Thrift Funds: Rs. {cmd_gadag['weavers_summary']['total_thrift_reserve']}")
    print(f"  Actionable Alerts Count: {len(cmd_gadag['actionable_alerts'])}")
    for a in cmd_gadag['actionable_alerts']:
        print(f"    - Alert: {a['title_kn']} ({a['title_en']})")
        
    # 4. Weaver Ecosystem & Operational Profile
    weavers = get(f"{base}/weavers", token_gadag)
    print(f"\nRegistered Weavers in Gadag: {len(weavers)}")
    assert len(weavers) >= 2
    w1 = weavers[0]
    w1_profile = get(f"{base}/weavers/{w1['id']}/profile", token_gadag)
    print(f"Weaver Operational Profile: {w1_profile['weaver']['full_name_kn']} ({w1_profile['weaver']['membership_no']})")
    print(f"  Loom Type: {w1_profile['weaver']['loom_type']} ({w1_profile['weaver']['active_looms_count']} looms)")
    print(f"  Yarn currently held at home loom: {w1_profile['yarn_in_custody']['total_kgs']} Kgs")
    print(f"  Wage Balance: Rs. {w1_profile['weaver']['passbook_wage_balance']}")
    print(f"  Accumulated 8% Thrift Fund: Rs. {w1_profile['weaver']['thrift_fund_balance']}")

    # 5. Multi-State Inventory Breakdown
    inv_status = get(f"{base}/inventory/status", token_gadag)
    print(f"\nMulti-State Inventory Status in Gadag:")
    print(f"  Central Yarn Godown: {len(inv_status['raw_yarn_godown'])} yarn lots")
    for y in inv_status['raw_yarn_godown']:
        print(f"    • {y['lot_number']}: {y['stock_kgs']} Kgs ({y['count_spec']})")
    print(f"  Finished Goods in Showrooms: {len(inv_status['showroom_stock'])} products")
    for s in inv_status['showroom_stock']:
        print(f"    • {s['sku']}: {s['available_pieces']} {s['uom']} available @ Rs. {s['retail_rate']}")

    # 6. Showroom Retail Sale with 20% Directorate Rebate
    target_sari = inv_status['showroom_stock'][0]
    initial_showroom_stock = target_sari['available_pieces']
    
    sale_payload = {
        "sale_channel": "RETAIL_SHOWROOM",
        "warehouse_id": "wh1-store-1111-1111-111111111111",
        "customer_name": "Smt. Sharda Kulkarni",
        "customer_phone": "9845112233",
        "apply_govt_rebate": True,
        "payment_mode": "UPI_QR",
        "items": [
            {
                "product_id": target_sari["sku"],
                "quantity": 2.0
            }
        ]
    }
    
    sale_res = post(f"{base}/sales/transactions", sale_payload, token_gadag)
    print(f"\nShowroom Sale Committed: {sale_res['bill_number']}")
    print(f"  Gross: Rs. {sale_res['gross_amount']}")
    print(f"  Govt 20% Rebate: -Rs. {sale_res['rebate_discount']}")
    print(f"  GST (5%): Rs. {sale_res['tax_amount']}")
    print(f"  Customer Paid: Rs. {sale_res['net_payable']}")
    print(f"  State Subsidy Claimable: Rs. {sale_res['govt_subsidy_receivable']}")
    
    # 7. Check Inventory Decremented in Ledger
    inv_after = get(f"{base}/inventory/status", token_gadag)
    target_after = next(p for p in inv_after['showroom_stock'] if p['sku'] == target_sari['sku'])
    print(f"  Showroom Stock after sale: {target_after['available_pieces']} (Expected: {initial_showroom_stock - 2.0})")
    assert target_after['available_pieces'] == initial_showroom_stock - 2.0
    
    # 8. Directorate Rebate Claims Register
    claims = get(f"{base}/reports/rebate-claims", token_gadag)
    print(f"\nDirectorate Rebate Claims Annexure-I Total: Rs. {claims['total_claimable_subsidy']} across {claims['total_bills_count']} bills")
    assert claims['total_claimable_subsidy'] >= sale_res['govt_subsidy_receivable']
    
    # 9. Cross-Tenant Isolation Check on Ilkal
    claims_ilkal = get(f"{base}/reports/rebate-claims", token_ilkal)
    print(f"Ilkal Rebate Claims Total (Must be 0.0): Rs. {claims_ilkal['total_claimable_subsidy']}")
    assert claims_ilkal['total_claimable_subsidy'] == 0.0, "Isolation breach!"

    print("\n========================================================")
    print("SUCCESS: 100% FIRST-PRINCIPLES WORKFLOW & ISOLATION VERIFIED!")
    print("========================================================")

if __name__ == "__main__":
    run_e2e_verification()
