import uuid
from typing import List, Dict, Any, Optional
from fastapi import HTTPException
from app.database.session import get_db
from app.models.schemas import WeaverCreate

def create_weaver(tenant_id: str, data: WeaverCreate) -> Dict[str, Any]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM weaver_members WHERE tenant_id = ? AND membership_no = ?", (tenant_id, data.membership_no))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail=f"Weaver with Membership No '{data.membership_no}' already exists.")
            
        weaver_id = str(uuid.uuid4())
        conn.execute("""
            INSERT INTO weaver_members (
                id, tenant_id, membership_no, full_name_en, full_name_kn,
                phone, village, loom_type, active_looms_count, pehchan_id,
                bank_account_no, bank_ifsc, thrift_fund_rate, passbook_balance, thrift_fund_balance, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0.0, 0.0, 'ACTIVE')
        """, (
            weaver_id, tenant_id, data.membership_no, data.full_name_en, data.full_name_kn,
            data.phone, data.village, data.loom_type, data.active_looms_count, data.pehchan_id,
            data.bank_account_no, data.bank_ifsc, data.thrift_fund_rate
        ))
        return {"id": weaver_id, "membership_no": data.membership_no, "full_name_en": data.full_name_en}

def list_weavers(tenant_id: str, search: Optional[str] = None) -> List[Dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.cursor()
        query = "SELECT * FROM weaver_members WHERE tenant_id = ?"
        params = [tenant_id]
        if search:
            query += " AND (full_name_en LIKE ? OR full_name_kn LIKE ? OR membership_no LIKE ? OR village LIKE ?)"
            term = f"%{search}%"
            params.extend([term, term, term, term])
        query += " ORDER BY membership_no ASC"
        cursor.execute(query, params)
        return [dict(r) for r in cursor.fetchall()]

def get_weaver_passbook(tenant_id: str, weaver_id: str) -> Dict[str, Any]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM weaver_members WHERE tenant_id = ? AND id = ?", (tenant_id, weaver_id))
        weaver = cursor.fetchone()
        if not weaver:
            raise HTTPException(status_code=404, detail="Weaver member not found.")
            
        # Recent allotments
        cursor.execute("""
            SELECT po.*, p.name_en as product_name_en, p.name_kn as product_name_kn
            FROM production_orders po
            JOIN products p ON p.id = po.product_id
            WHERE po.tenant_id = ? AND po.weaver_id = ?
            ORDER BY po.created_at DESC LIMIT 10
        """, (tenant_id, weaver_id))
        allotments = [dict(r) for r in cursor.fetchall()]
        
        # Recent goods receipts (wages earned)
        cursor.execute("""
            SELECT gr.*, p.name_en as product_name_en, p.name_kn as product_name_kn
            FROM goods_receipts gr
            JOIN products p ON p.id = gr.product_id
            WHERE gr.tenant_id = ? AND gr.weaver_id = ?
            ORDER BY gr.created_at DESC LIMIT 10
        """, (tenant_id, weaver_id))
        receipts = [dict(r) for r in cursor.fetchall()]
        
        return {
            "weaver": dict(weaver),
            "allotments": allotments,
            "receipts": receipts
        }
