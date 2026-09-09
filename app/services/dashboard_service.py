from typing import Dict, Any, List
from app.database.session import get_db

def get_operational_command_center(tenant_id: str) -> Dict[str, Any]:
    """
    Constructs the operational pulse of the Society answering:
    'What is happening in my Society today?'
    """
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 1. Today's Counter Sales & Collections
        cursor.execute("""
            SELECT 
                COALESCE(SUM(net_customer_payable), 0.0) as today_collections,
                COALESCE(SUM(gross_amount), 0.0) as today_gross_sales,
                COUNT(id) as today_bills_count
            FROM sales_transactions
            WHERE tenant_id = ? AND DATE(created_at) = DATE('now') AND status = 'POSTED'
        """, (tenant_id,))
        sales_pulse = cursor.fetchone()
        
        # 2. Material with Weavers (Cottage Custody WIP)
        cursor.execute("""
            SELECT 
                COALESCE(SUM(warp_issued_kgs + weft_issued_kgs), 0.0) as active_yarn_with_weavers_kgs,
                COUNT(id) as active_allotments_count
            FROM production_allotments
            WHERE tenant_id = ? AND status = 'WITH_WEAVER'
        """, (tenant_id,))
        loom_pulse = cursor.fetchone()
        
        # 3. Finished Goods Awaiting Quality Inspection
        cursor.execute("""
            SELECT COUNT(id) as pending_inspection_allotments
            FROM production_allotments
            WHERE tenant_id = ? AND status = 'PARTIALLY_RETURNED'
        """, (tenant_id,))
        inspection_pulse = cursor.fetchone()
        
        # 4. Pending Weaver Wage Settlements & Accumulated Thrift Funds
        cursor.execute("""
            SELECT 
                COALESCE(SUM(passbook_wage_balance), 0.0) as total_unpaid_wages,
                COALESCE(SUM(thrift_fund_balance), 0.0) as total_thrift_reserve,
                COUNT(id) as registered_weavers_count
            FROM weaver_members
            WHERE tenant_id = ? AND status = 'ACTIVE'
        """, (tenant_id,))
        weaver_pulse = cursor.fetchone()
        
        # 5. Directorate Rebate Sales Awaiting Claim Preparation
        cursor.execute("""
            SELECT 
                COALESCE(SUM(govt_subsidy_receivable), 0.0) as unclaimed_rebate_subsidy,
                COUNT(id) as rebate_sales_count
            FROM sales_transactions
            WHERE tenant_id = ? AND govt_subsidy_receivable > 0 AND status = 'POSTED'
        """, (tenant_id,))
        rebate_pulse = cursor.fetchone()
        
        # 6. Critical Actionable Alerts
        alerts: List[Dict[str, Any]] = []
        
        # Alert: Weavers holding yarn for > 28 days
        cursor.execute("""
            SELECT pa.allotment_no, pa.issue_date, pa.target_pieces,
                   wm.full_name_kn, wm.full_name_en, wm.membership_no, wm.village
            FROM production_allotments pa
            JOIN weaver_members wm ON wm.id = pa.weaver_id
            WHERE pa.tenant_id = ? AND pa.status = 'WITH_WEAVER'
              AND (julianday('now') - julianday(pa.issue_date)) > 28
            ORDER BY pa.issue_date ASC LIMIT 5
        """, (tenant_id,))
        overdue_allotments = [dict(r) for r in cursor.fetchall()]
        if overdue_allotments:
            alerts.append({
                "type": "WARNING",
                "code": "OVERDUE_YARN_ALLOTMENTS",
                "title_kn": f"{len(overdue_allotments)} ನೇಕಾರರಲ್ಲಿ ನೂಲು ೨೮ ದಿನಗಳಿಗಿಂತ ಹೆಚ್ಚು ಬಾಕಿ ಉಳಿದಿದೆ",
                "title_en": f"{len(overdue_allotments)} Weavers have yarn pending for >28 days",
                "items": overdue_allotments
            })
            
        # Alert: Low Finished Goods Stock in Showrooms (< 5 units)
        cursor.execute("""
            SELECT p.sku, p.name_kn, p.name_en, p.uom, COALESCE(SUM(il.quantity_delta), 0.0) as current_stock
            FROM products p
            JOIN warehouses w ON w.tenant_id = p.tenant_id AND w.storage_type = 'FINISHED_SHOWROOM'
            LEFT JOIN inventory_ledger il ON il.product_id = p.id AND il.warehouse_id = w.id
            WHERE p.tenant_id = ? AND p.is_active = 1
            GROUP BY p.id
            HAVING current_stock < 5.0
            LIMIT 5
        """, (tenant_id,))
        low_stocks = [dict(r) for r in cursor.fetchall()]
        if low_stocks:
            alerts.append({
                "type": "INFO",
                "code": "LOW_SHOWROOM_STOCK",
                "title_kn": f"{len(low_stocks)} ಉತ್ಪನ್ನಗಳ ದಾಸ್ತಾನು ಮಳಿಗೆಯಲ್ಲಿ ಕೊರತೆಯಿದೆ (< ೫ ಸೀರೆಗಳು)",
                "title_en": f"{len(low_stocks)} Products have low showroom stock (< 5 units)",
                "items": low_stocks
            })
            
        # 7. Recent Operational Activity Journal
        cursor.execute("""
            SELECT il.created_at, il.movement_type, il.quantity_delta, il.notes,
                   COALESCE(p.name_kn, yl.count_spec) as item_name_kn,
                   COALESCE(p.name_en, yl.yarn_type) as item_name_en,
                   w.name_kn as warehouse_name_kn, w.name_en as warehouse_name_en
            FROM inventory_ledger il
            LEFT JOIN products p ON p.id = il.product_id
            LEFT JOIN yarn_lots yl ON yl.id = il.yarn_lot_id
            JOIN warehouses w ON w.id = il.warehouse_id
            WHERE il.tenant_id = ?
            ORDER BY il.created_at DESC LIMIT 8
        """, (tenant_id,))
        recent_activity = [dict(r) for r in cursor.fetchall()]
        
        return {
            "today_sales": {
                "collections": float(sales_pulse["today_collections"]),
                "gross_sales": float(sales_pulse["today_gross_sales"]),
                "bills_count": int(sales_pulse["today_bills_count"])
            },
            "cottage_production": {
                "active_yarn_with_weavers_kgs": float(loom_pulse["active_yarn_with_weavers_kgs"]),
                "active_allotments_count": int(loom_pulse["active_allotments_count"]),
                "pending_inspection_count": int(inspection_pulse["pending_inspection_allotments"])
            },
            "weavers_summary": {
                "total_unpaid_wages": float(weaver_pulse["total_unpaid_wages"]),
                "total_thrift_reserve": float(weaver_pulse["total_thrift_reserve"]),
                "registered_weavers": int(weaver_pulse["registered_weavers_count"])
            },
            "schemes_summary": {
                "unclaimed_rebate_subsidy": float(rebate_pulse["unclaimed_rebate_subsidy"]),
                "rebate_sales_count": int(rebate_pulse["rebate_sales_count"])
            },
            "actionable_alerts": alerts,
            "recent_activity": recent_activity
        }
