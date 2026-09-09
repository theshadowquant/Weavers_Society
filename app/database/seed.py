import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import uuid
from app.database.session import init_db, get_db
from app.core.security import hash_password
from app.services.inventory_service import append_ledger_entry

def seed_database():
    """Seeds the platform with two realistic Karnataka Handloom Societies."""
    init_db(force=True)
    print("First-principles database schema initialized.")
    
    with get_db() as conn:
        # ----------------------------------------------------
        # TENANT 1: GADAG COTTON WEAVERS CO-OPERATIVE SOCIETY
        # ----------------------------------------------------
        tenant_1_id = "11111111-1111-1111-1111-111111111111"
        conn.execute("""
            INSERT INTO tenants (
                id, slug, legal_name_en, legal_name_kn, registration_number,
                registration_date, society_type, district, taluk, hobli_village,
                pincode, primary_phone, primary_email, registered_office_address,
                pan, gstin, directorate_society_code, bank_name, bank_account_no, bank_ifsc,
                members_count, active_looms_count, status
            ) VALUES (?, ?, ?, ?, ?, ?, 'PRIMARY_WEAVERS_COOP', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 128, 96, 'ACTIVE')
        """, (
            tenant_1_id,
            "gadag-weavers-coop",
            "Gadag Cotton Handloom Weavers Co-operative Society Ltd.",
            "ಗದಗ ಹತ್ತಿ ಕೈಮಗ್ಗ ನೇಕಾರರ ಸಹಕಾರ ಸಂಘ ನಿಯಮಿತ",
            "DR/KCS/GNP/1962/142",
            "1962-08-15",
            "Gadag",
            "Gadag-Betageri",
            "Betageri",
            "582102",
            "08372234567",
            "secretary@gadagweavers.coop",
            "Weavers Colony, Main Road, Betageri, Gadag - 582102",
            "AAAAA0000A",
            "29AAAAA0000A1Z5",
            "DTH/GDG/104",
            "Karnataka State Apex Co-operative Bank",
            "100234567890",
            "KSCB0001002"
        ))
        
        # Admin User: Secretary
        user_1_id = "aaaa1111-1111-1111-1111-111111111111"
        conn.execute("""
            INSERT INTO users (id, email, phone, full_name, password_hash, preferred_language)
            VALUES (?, ?, ?, ?, ?, 'kn')
        """, (
            user_1_id,
            "admin@gadag.coop",
            "9845012345",
            "K. N. Patil (ಕಾರ್ಯದರ್ಶಿ)",
            hash_password("admin123")
        ))
        conn.execute("""
            INSERT INTO user_tenant_roles (id, user_id, tenant_id, role)
            VALUES (?, ?, ?, 'SECRETARY')
        """, (str(uuid.uuid4()), user_1_id, tenant_1_id))
        
        # Multi-State Storage Nodes
        wh1_godown = "wh1-godown-1111-1111-111111111111"
        wh1_wip = "wh1-wip-1111-1111-111111111111"
        wh1_store = "wh1-store-1111-1111-111111111111"
        wh1_apex = "wh1-apex-1111-1111-111111111111"
        conn.execute("""
            INSERT INTO warehouses (id, tenant_id, code, name_en, name_kn, storage_type)
            VALUES 
            (?, ?, 'YARN_GODOWN', 'Central Yarn Godown', 'ಕೇಂದ್ರ ನೂಲು ಗೋದಾಮು', 'RAW_YARN_GODOWN'),
            (?, ?, 'LOOM_WIP', 'Cottage Weavers Looms (WIP)', 'ನೇಕಾರರ ಮನೆ ಮಗ್ಗಗಳು (ಚಾಲ್ತಿ)', 'WEAVER_CUSTODY_WIP'),
            (?, ?, 'RETAIL_MAIN', 'Gadag Town Sales Showroom', 'ಗದಗ ನಗರ ಮಾರಾಟ ಮಳಿಗೆ', 'FINISHED_SHOWROOM'),
            (?, ?, 'WHOLESALE_DEPOT', 'Apex Contracts Depot', 'ಅಪೆಕ್ಸ್ ಸಗಟು ಡಿಪೋ', 'WHOLESALE_DEPOT')
        """, (wh1_godown, tenant_1_id, wh1_wip, tenant_1_id, wh1_store, tenant_1_id, wh1_apex, tenant_1_id))
        
        # Yarn Lots (NHDC & Spinning Mill)
        yarn_1_id = "y1-1111-1111-1111-111111111111"
        yarn_2_id = "y2-1111-1111-1111-111111111111"
        conn.execute("""
            INSERT INTO yarn_lots (id, tenant_id, lot_number, yarn_type, count_spec, shade_code, mill_name, unit_cost_per_kg)
            VALUES 
            (?, ?, 'NHDC-COT-60S-412', 'COTTON', '2/60s Combed Mercerised', 'Natural Ecru', 'NHDC Central Depot, Gadag', 420.00),
            (?, ?, 'GADAG-SPN-80S-09', 'COTTON', '80s Combed Cotton Hank', 'Deep Indigo 12B', 'Karnataka Co-operative Spinning Mill, Gadag', 480.00)
        """, (yarn_1_id, tenant_1_id, yarn_2_id, tenant_1_id))
        
        # Finished Handloom Products
        prod_1_id = "p1-1111-1111-1111-111111111111"
        prod_2_id = "p2-1111-1111-1111-111111111111"
        conn.execute("""
            INSERT INTO products (
                id, tenant_id, sku, name_en, name_kn, category, gi_tag_certified,
                warp_count_spec, weft_count_spec, uom, hsn_code, standard_manufacturing_cost,
                retail_rate, wholesale_rate, tax_rate
            ) VALUES 
            (?, ?, 'GDG-COT-60S-01', 'Gadag Pure Cotton Sari 60s Count (Temple Border)', 'ಗದಗ ಶುದ್ಧ ಹತ್ತಿ ಸೀರೆ 60s ಕೌಂಟ್ (ಗೋಪುರ ಅಂಚು)', 'SARI', 1, '2/60s Cotton', '80s Cotton', 'PCS', '5208', 920.00, 1550.00, 1250.00, 5.00),
            (?, ?, 'GDG-DHO-40S-02', 'Traditional Kasuti Handloom Dhoti (9x5)', 'ಸಾಂಪ್ರದಾಯಿಕ ಕಸೂತಿ ಕೈಮಗ್ಗ ಪಂಚೆ (೯x೫)', 'DHOTI', 0, '2/40s Cotton', '2/40s Cotton', 'PCS', '5208', 420.00, 750.00, 600.00, 5.00)
        """, (prod_1_id, tenant_1_id, prod_2_id, tenant_1_id))
        
        # Weaver Members
        weaver_1_id = "w1-1111-1111-1111-111111111111"
        weaver_2_id = "w2-1111-1111-1111-111111111111"
        conn.execute("""
            INSERT INTO weaver_members (
                id, tenant_id, membership_no, full_name_en, full_name_kn,
                phone, village, taluk, loom_type, active_looms_count,
                pehchan_card_id, bank_name, bank_account_no, bank_ifsc,
                thrift_fund_rate, passbook_wage_balance, thrift_fund_balance
            ) VALUES 
            (?, ?, 'MBR/GDG/001', 'Basavaraj Shettar', 'ಬಸವರಾಜ ಶೆಟ್ಟರ್', '9880112233', 'Betageri', 'Gadag', 'FRAME_LOOM', 2, 'KNT-GDG-100234', 'Karnataka Apex Co-op Bank', '3029101001', 'KSCB0001002', 8.0, 2400.0, 4800.0),
            (?, ?, 'MBR/GDG/002', 'Mallamma Badiger', 'ಮಲ್ಲಮ್ಮ ಬಡಿಗೇರ', '9880223344', 'Mulagund', 'Gadag', 'PIT_LOOM', 1, 'KNT-GDG-100567', 'Karnataka Apex Co-op Bank', '3029101002', 'KSCB0001002', 8.0, 1200.0, 3100.0)
        """, (weaver_1_id, tenant_1_id, weaver_2_id, tenant_1_id))
        
        # Production Allotment with Weaver (Hanchike)
        allot_1_id = "allot-1111-1111-1111-111111111111"
        conn.execute("""
            INSERT INTO production_allotments (
                id, tenant_id, allotment_no, weaver_id, product_id,
                warp_yarn_lot_id, warp_issued_kgs, weft_yarn_lot_id, weft_issued_kgs,
                target_pieces, agreed_piece_wage, reed_pick_specs, issue_date,
                expected_return_date, status, issued_by, notes
            ) VALUES (?, ?, 'PO/HNK/2026/001', ?, ?, ?, 12.5, ?, 8.5, 10, 350.0, '68 Reed / 64 Picks (Double Zari Temple)', '2026-08-10', '2026-09-02', 'WITH_WEAVER', ?, 'Special Deepavali order warp')
        """, (allot_1_id, tenant_1_id, weaver_1_id, prod_1_id, yarn_1_id, yarn_2_id, user_1_id))
        
        # Directorate 20% Festival Rebate Scheme
        scheme_1_id = "scheme-1111-1111-1111-111111111111"
        conn.execute("""
            INSERT INTO scheme_configs (
                id, tenant_id, scheme_name_en, scheme_name_kn, sanctioning_authority,
                rebate_percentage, state_share_percentage, effective_from, effective_until, is_active
            ) VALUES (?, ?, 'Karnataka Handloom 20% Special Festival Rebate Scheme', 
                      'ಕರ್ನಾಟಕ ರಾಜ್ಯ 20% ವಿಶೇಷ ಹಬ್ಬದ ರಿಯಾಯಿತಿ ಯೋಜನೆ', 
                      'Directorate of Handlooms & Textiles, Govt of Karnataka',
                      20.00, 100.00, '2026-01-01', '2027-03-31', 1)
        """, (scheme_1_id, tenant_1_id))
        
        # Stock Initializations in Immutable Ledger
        # 1. Raw yarn in godown
        append_ledger_entry(
            conn=conn, tenant_id=tenant_1_id, warehouse_id=wh1_godown,
            movement_type="PURCHASE_YARN_INWARD", quantity_delta=350.0, unit_cost=420.0,
            reference_type="PURCHASE_INVOICE", reference_id="NHDC-INV-9901", performed_by=user_1_id,
            yarn_lot_id=yarn_1_id, notes="Opening stock from NHDC depot"
        )
        append_ledger_entry(
            conn=conn, tenant_id=tenant_1_id, warehouse_id=wh1_godown,
            movement_type="PURCHASE_YARN_INWARD", quantity_delta=200.0, unit_cost=480.0,
            reference_type="PURCHASE_INVOICE", reference_id="GADAG-SPN-301", performed_by=user_1_id,
            yarn_lot_id=yarn_2_id, notes="Opening stock from Gadag Spinning Mill"
        )
        # 2. Yarn held at cottage looms (WIP)
        append_ledger_entry(
            conn=conn, tenant_id=tenant_1_id, warehouse_id=wh1_wip,
            movement_type="LOOM_CUSTODY_INWARD", quantity_delta=21.0, unit_cost=450.0,
            reference_type="ALLOTMENT", reference_id=allot_1_id, performed_by=user_1_id,
            yarn_lot_id=yarn_1_id, notes="Warp & Weft at Betageri loom (Basavaraj Shettar)"
        )
        # 3. Finished saris in Showroom
        append_ledger_entry(
            conn=conn, tenant_id=tenant_1_id, warehouse_id=wh1_store,
            movement_type="PRODUCTION_RECEIPT_ACCEPT", quantity_delta=32.0, unit_cost=920.0,
            reference_type="INSPECTION_RECEIPT", reference_id="GRN-INIT-01", performed_by=user_1_id,
            product_id=prod_1_id, notes="Inspected Grade 1 Saris in Showroom"
        )
        append_ledger_entry(
            conn=conn, tenant_id=tenant_1_id, warehouse_id=wh1_store,
            movement_type="PRODUCTION_RECEIPT_ACCEPT", quantity_delta=60.0, unit_cost=420.0,
            reference_type="INSPECTION_RECEIPT", reference_id="GRN-INIT-02", performed_by=user_1_id,
            product_id=prod_2_id, notes="Kasuti Dhotis in Showroom"
        )

        # ----------------------------------------------------
        # TENANT 2: ILKAL TRADITIONAL SARI WEAVERS CO-OP
        # (Proof of complete tenant isolation)
        # ----------------------------------------------------
        tenant_2_id = "22222222-2222-2222-2222-222222222222"
        conn.execute("""
            INSERT INTO tenants (
                id, slug, legal_name_en, legal_name_kn, registration_number,
                registration_date, society_type, district, taluk, hobli_village,
                pincode, primary_phone, primary_email, registered_office_address,
                pan, gstin, directorate_society_code, bank_name, bank_account_no, bank_ifsc,
                members_count, active_looms_count, status
            ) VALUES (?, ?, ?, ?, ?, ?, 'PRIMARY_WEAVERS_COOP', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 210, 180, 'ACTIVE')
        """, (
            tenant_2_id,
            "ilkal-sari-coop",
            "Ilkal Traditional Sari Weavers Co-operative Society Ltd.",
            "ಇಳಕಲ್ ಸಾಂಪ್ರದಾಯಿಕ ಸೀರೆ ನೇಕಾರರ ಸಹಕಾರ ಸಂಘ ನಿಯಮಿತ",
            "DR/KCS/BGK/1971/208",
            "1971-11-01",
            "Bagalkot",
            "Ilkal",
            "Ilkal",
            "587125",
            "08351278901",
            "md@ilkalsarees.coop",
            "GI Handloom Complex, Weaver Street, Ilkal - 587125",
            "BBBBB1111B",
            "29BBBBB1111B1Z9",
            "DTH/BGK/209",
            "Bagalkot District Central Co-op Bank",
            "200987654321",
            "BDCC0002009"
        ))
        
        user_2_id = "bbbb2222-2222-2222-2222-222222222222"
        conn.execute("""
            INSERT INTO users (id, email, phone, full_name, password_hash, preferred_language)
            VALUES (?, ?, ?, ?, ?, 'kn')
        """, (
            user_2_id,
            "admin@ilkal.coop",
            "9845098765",
            "Shankarappa Tenginkai (ವ್ಯವಸ್ಥಾಪಕ ನಿರ್ದೇಶಕ)",
            hash_password("admin123")
        ))
        conn.execute("""
            INSERT INTO user_tenant_roles (id, user_id, tenant_id, role)
            VALUES (?, ?, ?, 'MANAGING_DIRECTOR')
        """, (str(uuid.uuid4()), user_2_id, tenant_2_id))
        
        wh2_store = "wh2-store-2222-2222-222222222222"
        conn.execute("""
            INSERT INTO warehouses (id, tenant_id, code, name_en, name_kn, storage_type)
            VALUES (?, ?, 'ILKAL_MAIN', 'Ilkal Heritage Showroom', 'ಇಳಕಲ್ ಪಾರಂಪರಿಕ ಮಾರಾಟ ಮಳಿಗೆ', 'FINISHED_SHOWROOM')
        """, (wh2_store, tenant_2_id))
        
        prod_ilkal_1 = "p-ilkal-2222-2222-2222-222222222222"
        conn.execute("""
            INSERT INTO products (
                id, tenant_id, sku, name_en, name_kn, category, gi_tag_certified,
                warp_count_spec, weft_count_spec, uom, hsn_code, standard_manufacturing_cost,
                retail_rate, wholesale_rate, tax_rate
            ) VALUES (?, ?, 'ILK-TOPE-TENI-01', 'Authentic Ilkal Silk Sari (Tope Teni Seragu, GI Certified)', 'ಅಸಲಿ ಇಳಕಲ್ ರೇಷ್ಮೆ ಸೀರೆ (ಟೋಪೆ ತೆನಿ ಸೆರಗು, ಜಿಐ ಮಾನ್ಯತೆ)', 'SARI', 1, '20/22 Mulberry Silk', 'Art Silk Zari', 'PCS', '5007', 2600.00, 4250.00, 3400.00, 5.00)
        """, (prod_ilkal_1, tenant_2_id))
        
        append_ledger_entry(
            conn=conn, tenant_id=tenant_2_id, warehouse_id=wh2_store,
            movement_type="PRODUCTION_RECEIPT_ACCEPT", quantity_delta=25.0, unit_cost=2600.0,
            reference_type="INSPECTION_RECEIPT", reference_id="GRN-ILKAL-01", performed_by=user_2_id,
            product_id=prod_ilkal_1, notes="Opening GI certified Ilkal silk saris"
        )
        
    print("Seed complete: Gadag Cotton Weavers & Ilkal Silk Weavers societies initialized.")

if __name__ == "__main__":
    seed_database()
