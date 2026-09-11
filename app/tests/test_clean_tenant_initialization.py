import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.database.session import init_db, get_db

def test_clean_database_has_zero_tenants_and_records():
    """
    CLEAN TENANT PRINCIPLE:
    A fresh database initialized without demo seeds must have exactly ZERO
    tenants, users, weavers, products, stock, or transactions.
    """
    init_db(force=True)
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        for table in [
            "tenants",
            "users",
            "user_tenant_roles",
            "weaver_members",
            "products",
            "yarn_lots",
            "warehouses",
            "inventory_ledger",
            "sales_transactions",
            "sales_items",
            "purchase_invoices",
            "purchase_items",
            "production_allotments",
            "inspection_receipts",
            "suppliers"
        ]:
            cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
            cnt = cursor.fetchone()["count"]
            assert cnt == 0, f"Violation: Fresh database contains {cnt} preloaded records in '{table}'!"
            
    print("Clean database verification passed: 0 preloaded societies, 0 fake records.")

if __name__ == "__main__":
    test_clean_database_has_zero_tenants_and_records()
