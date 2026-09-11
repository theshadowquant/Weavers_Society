import logging
from datetime import datetime, timezone
from typing import Dict, Any
from app.core.firebase import get_firestore_client, is_firebase_available

logger = logging.getLogger(__name__)

def firestore_timestamp():
    return datetime.now(timezone.utc).isoformat()

def sync_tenant_to_firestore(tenant_id: str, conn) -> Dict[str, Any]:
    """
    Syncs a tenant's profile, weaver members, and products catalog to Cloud Firestore.
    Maintains Firestore collection hierarchy:
      /tenants/{tenant_id}
      /tenants/{tenant_id}/weavers/{weaver_id}
      /tenants/{tenant_id}/products/{product_id}
    """
    if not is_firebase_available():
        return {"synced": False, "reason": "Firebase credentials not configured or initialized"}

    db = get_firestore_client()
    if not db:
        return {"synced": False, "reason": "Firestore client unavailable"}

    try:
        cursor = conn.cursor()
        
        # 1. Sync Tenant Profile
        cursor.execute("SELECT * FROM tenants WHERE id = ?", (tenant_id,))
        tenant = cursor.fetchone()
        if not tenant:
            return {"synced": False, "reason": f"Tenant {tenant_id} not found"}

        t = dict(tenant)
        tenant_ref = db.collection("tenants").document(tenant_id)
        tenant_ref.set({
            "id": t["id"],
            "slug": t.get("slug"),
            "legal_name_en": t.get("legal_name_en"),
            "legal_name_kn": t.get("legal_name_kn"),
            "district": t.get("district"),
            "taluk": t.get("taluk"),
            "hobli_village": t.get("hobli_village"),
            "pincode": t.get("pincode"),
            "registration_number": t.get("registration_number"),
            "registration_date": t.get("registration_date"),
            "society_type": t.get("society_type", "PRIMARY_WEAVERS_COOP"),
            "primary_phone": t.get("primary_phone"),
            "primary_email": t.get("primary_email"),
            "pan": t.get("pan"),
            "gstin": t.get("gstin"),
            "bank_name": t.get("bank_name"),
            "bank_account_no": t.get("bank_account_no"),
            "bank_ifsc": t.get("bank_ifsc"),
            "members_count": t.get("members_count", 0),
            "active_looms_count": t.get("active_looms_count", 0),
            "status": t.get("status", "ACTIVE"),
            "synced_at": firestore_timestamp()
        }, merge=True)

        # 2. Sync Weaver Members
        cursor.execute("SELECT * FROM weaver_members WHERE tenant_id = ?", (tenant_id,))
        members = cursor.fetchall()
        members_coll = tenant_ref.collection("weavers")
        for m in members:
            w = dict(m)
            members_coll.document(w["id"]).set({
                "id": w["id"],
                "membership_no": w.get("membership_no"),
                "full_name_en": w.get("full_name_en"),
                "full_name_kn": w.get("full_name_kn"),
                "phone": w.get("phone"),
                "village": w.get("village"),
                "taluk": w.get("taluk"),
                "loom_type": w.get("loom_type"),
                "active_looms_count": w.get("active_looms_count", 1),
                "pehchan_card_id": w.get("pehchan_card_id"),
                "bank_name": w.get("bank_name"),
                "bank_account_no": w.get("bank_account_no"),
                "bank_ifsc": w.get("bank_ifsc"),
                "thrift_fund_balance": float(w.get("thrift_fund_balance", 0.0) or 0.0),
                "passbook_wage_balance": float(w.get("passbook_wage_balance", 0.0) or 0.0),
                "status": w.get("status", "ACTIVE"),
                "synced_at": firestore_timestamp()
            }, merge=True)

        # 3. Sync Products
        cursor.execute("SELECT * FROM products WHERE tenant_id = ?", (tenant_id,))
        products = cursor.fetchall()
        products_coll = tenant_ref.collection("products")
        for p in products:
            prod = dict(p)
            products_coll.document(prod["id"]).set({
                "id": prod["id"],
                "sku": prod.get("sku"),
                "name_en": prod.get("name_en"),
                "name_kn": prod.get("name_kn"),
                "category": prod.get("category"),
                "retail_rate": float(prod.get("retail_rate", 0.0) or 0.0),
                "wholesale_rate": float(prod.get("wholesale_rate", 0.0) or 0.0),
                "gi_tag_certified": bool(prod.get("gi_tag_certified", 0)),
                "is_active": bool(prod.get("is_active", 1)),
                "synced_at": firestore_timestamp()
            }, merge=True)

        return {
            "synced": True,
            "tenant_id": tenant_id,
            "society_name": t.get("legal_name_en"),
            "members_synced": len(members),
            "products_synced": len(products),
            "firestore_collection": f"tenants/{tenant_id}",
            "synced_at": firestore_timestamp()
        }
    except Exception as e:
        logger.error(f"Error syncing tenant {tenant_id} to Firestore: {e}", exc_info=True)
        return {"synced": False, "error": str(e)}
