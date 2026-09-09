import uuid
from typing import List, Dict, Any, Optional
from fastapi import HTTPException
from app.database.session import get_db
from app.models.schemas import WeaverCreate

def create_weaver_member(tenant_id: str, data: WeaverCreate) -> Dict[str, Any]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM weaver_members WHERE tenant_id = ? AND membership_no = ?", (tenant_id, data.membership_no))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail=f"Weaver Membership No '{data.membership_no}' already exists.")
            
        weaver_id = str(uuid.uuid4())
        conn.execute("""
            INSERT INTO weaver_members (
                id, tenant_id, membership_no, full_name_en, full_name_kn,
                phone, village, taluk, loom_type, active_looms_count,
                pehchan_card_id, bank_name, bank_account_no, bank_ifsc,
                thrift_fund_rate, passbook_wage_balance, thrift_fund_balance, advances_outstanding, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0.0, 0.0, 0.0, 'ACTIVE')
        """, (
            weaver_id, tenant_id, data.membership_no, data.full_name_en, data.full_name_kn,
            data.phone, data.village, data.taluk, data.loom_type, data.active_looms_count,
            data.pehchan_card_id, data.bank_name, data.bank_account_no, data.bank_ifsc,
            data.thrift_fund_rate
        ))
        
        # Increment active looms in tenant stats
        conn.execute("UPDATE tenants SET members_count = members_count + 1, active_looms_count = active_looms_count + ? WHERE id = ?", (data.active_looms_count, tenant_id))
        
        return {"id": weaver_id, "membership_no": data.membership_no, "full_name_kn": data.full_name_kn}

def list_weavers(tenant_id: str, search: Optional[str] = None) -> List[Dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.cursor()
        query = """
            SELECT 
                wm.*,
                COALESCE(SUM(CASE WHEN pa.status = 'WITH_WEAVER' THEN pa.warp_issued_kgs + pa.weft_issued_kgs ELSE 0 END), 0.0) as active_yarn_in_custody_kgs,
                COUNT(CASE WHEN pa.status = 'WITH_WEAVER' THEN pa.id END) as active_allotments_count
            FROM weaver_members wm
            LEFT JOIN production_allotments pa ON pa.weaver_id = wm.id AND pa.tenant_id = wm.tenant_id
            WHERE wm.tenant_id = ?
        """
        params = [tenant_id]
        if search:
            query += " AND (wm.full_name_kn LIKE ? OR wm.full_name_en LIKE ? OR wm.membership_no LIKE ? OR wm.village LIKE ?)"
            term = f"%{search}%"
            params.extend([term, term, term, term])
            
        query += " GROUP BY wm.id ORDER BY wm.membership_no ASC"
        cursor.execute(query, params)
        return [dict(r) for r in cursor.fetchall()]

def get_weaver_operational_profile(tenant_id: str, weaver_id: str) -> Dict[str, Any]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM weaver_members WHERE tenant_id = ? AND id = ?", (tenant_id, weaver_id))
        weaver = cursor.fetchone()
        if not weaver:
            raise HTTPException(status_code=404, detail="Weaver member not found.")
            
        # Active & Historical Allotments (Hanchike)
        cursor.execute("""
            SELECT pa.*, p.name_kn as product_name_kn, p.name_en as product_name_en, p.sku
            FROM production_allotments pa
            JOIN products p ON p.id = pa.product_id
            WHERE pa.tenant_id = ? AND pa.weaver_id = ?
            ORDER BY pa.issue_date DESC LIMIT 15
        """, (tenant_id, weaver_id))
        allotments = [dict(r) for r in cursor.fetchall()]
        
        # Inspection Receipts (GRNs) & Wages Earned
        cursor.execute("""
            SELECT ir.*, p.name_kn as product_name_kn, p.name_en as product_name_en
            FROM inspection_receipts ir
            JOIN products p ON p.id = ir.product_id
            WHERE ir.tenant_id = ? AND ir.weaver_id = ?
            ORDER BY ir.inspection_date DESC LIMIT 15
        """, (tenant_id, weaver_id))
        receipts = [dict(r) for r in cursor.fetchall()]
        
        # Yarn in current cottage custody
        cursor.execute("""
            SELECT 
                COALESCE(SUM(warp_issued_kgs), 0.0) as warp_in_custody,
                COALESCE(SUM(weft_issued_kgs), 0.0) as weft_in_custody
            FROM production_allotments
            WHERE tenant_id = ? AND weaver_id = ? AND status = 'WITH_WEAVER'
        """, (tenant_id, weaver_id))
        yarn_custody = cursor.fetchone()
        
        return {
            "weaver": dict(weaver),
            "yarn_in_custody": {
                "warp_kgs": float(yarn_custody["warp_in_custody"]),
                "weft_kgs": float(yarn_custody["weft_in_custody"]),
                "total_kgs": float(yarn_custody["warp_in_custody"]) + float(yarn_custody["weft_in_custody"])
            },
            "allotments": allotments,
            "receipts": receipts
        }
