from typing import List, Dict, Any, Optional
from app.database.session import get_db

def get_statutory_daybook(tenant_id: str, target_date: Optional[str] = None) -> Dict[str, Any]:
    """
    Computes the statutory Daily Daybook (ದಿನಚರಿ ಪುಸ್ತಕ - Form A):
    Reconciles all daily receipts (Retail Counter, Wholesale recovery)
    against all daily disbursements (Weaver wages, Purchases, Advances).
    """
    with get_db() as conn:
        cursor = conn.cursor()
        date_filter = target_date or "DATE('now')"
        
        # 1. Receipts (Sales collections)
        cursor.execute(f"""
            SELECT id, bill_number as voucher_ref, 
                   COALESCE(customer_name, 'Showroom Cash Customer') as description,
                   payment_mode, net_customer_payable as amount, created_at, 'RECEIPT' as entry_type
            FROM sales_transactions
            WHERE tenant_id = ? AND DATE(created_at) = {date_filter} AND status = 'POSTED'
            ORDER BY created_at ASC
        """, (tenant_id,))
        receipts = [dict(r) for r in cursor.fetchall()]
        
        # 2. Payments (Wages credited / disbursed via goods receipts)
        cursor.execute(f"""
            SELECT ir.id, ir.receipt_no as voucher_ref,
                   'Weaver Wage: ' || wm.full_name_kn || ' (' || wm.membership_no || ')' as description,
                   'CASH/BANK' as payment_mode, ir.net_wages_credited as amount, ir.created_at, 'PAYMENT' as entry_type
            FROM inspection_receipts ir
            JOIN weaver_members wm ON wm.id = ir.weaver_id
            WHERE ir.tenant_id = ? AND DATE(ir.created_at) = {date_filter}
            ORDER BY ir.created_at ASC
        """, (tenant_id,))
        payments = [dict(r) for r in cursor.fetchall()]
        
        total_receipts = sum(r["amount"] for r in receipts)
        total_payments = sum(p["amount"] for p in payments)
        net_cash_flow = total_receipts - total_payments
        
        return {
            "date": target_date or "Today",
            "total_receipts": round(total_receipts, 2),
            "total_payments": round(total_payments, 2),
            "net_cash_flow": round(net_cash_flow, 2),
            "receipts": receipts,
            "payments": payments
        }

def get_weaver_material_balance_register(tenant_id: str) -> List[Dict[str, Any]]:
    """
    Weaver-wise material custody register tracking raw yarn held at cottage looms vs return status.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                wm.membership_no, wm.full_name_kn, wm.full_name_en, wm.village, wm.loom_type,
                COUNT(pa.id) as total_allotments_issued,
                COALESCE(SUM(pa.warp_issued_kgs + pa.weft_issued_kgs), 0.0) as total_yarn_issued_kgs,
                COALESCE(SUM(CASE WHEN pa.status = 'WITH_WEAVER' THEN (pa.warp_issued_kgs + pa.weft_issued_kgs) ELSE 0 END), 0.0) as active_yarn_at_looms_kgs,
                COALESCE(SUM(pa.target_pieces), 0) as total_pieces_targeted,
                COALESCE(SUM(CASE WHEN pa.status = 'COMPLETED' THEN pa.target_pieces ELSE 0 END), 0) as completed_pieces
            FROM weaver_members wm
            LEFT JOIN production_allotments pa ON pa.weaver_id = wm.id AND pa.tenant_id = wm.tenant_id
            WHERE wm.tenant_id = ?
            GROUP BY wm.id
            ORDER BY active_yarn_at_looms_kgs DESC
        """, (tenant_id,))
        return [dict(r) for r in cursor.fetchall()]

def get_weaver_wage_thrift_register(tenant_id: str) -> List[Dict[str, Any]]:
    """
    Statutory register tracking piece-rate wages earned, 8% Thrift Fund deductions, and passbook balances.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                wm.membership_no, wm.full_name_kn, wm.full_name_en, wm.village,
                wm.passbook_wage_balance, wm.thrift_fund_balance, wm.thrift_fund_rate,
                COUNT(ir.id) as inspection_receipts_count,
                COALESCE(SUM(ir.first_quality_count + ir.second_quality_count), 0) as total_saris_woven,
                COALESCE(SUM(ir.gross_wages_earned), 0.0) as total_gross_wages,
                COALESCE(SUM(ir.thrift_fund_deduction), 0.0) as total_thrift_deducted,
                COALESCE(SUM(ir.net_wages_credited), 0.0) as total_net_wages_credited
            FROM weaver_members wm
            LEFT JOIN inspection_receipts ir ON ir.weaver_id = wm.id AND ir.tenant_id = wm.tenant_id
            WHERE wm.tenant_id = ?
            GROUP BY wm.id
            ORDER BY wm.membership_no ASC
        """, (tenant_id,))
        return [dict(r) for r in cursor.fetchall()]

def get_directorate_rebate_claim_schedule(tenant_id: str) -> Dict[str, Any]:
    """
    Compiles statutory claims format for submission to the Karnataka Directorate of Handlooms & Textiles.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                s.bill_number, s.created_at, s.customer_name, s.customer_phone,
                s.gross_amount, s.rebate_amount, s.net_customer_payable,
                s.govt_subsidy_receivable, sc.scheme_name_en, sc.scheme_name_kn, sc.sanctioning_authority
            FROM sales_transactions s
            JOIN scheme_configs sc ON sc.id = s.scheme_id
            WHERE s.tenant_id = ? AND s.govt_subsidy_receivable > 0 AND s.status = 'POSTED'
            ORDER BY s.created_at DESC
        """, (tenant_id,))
        claims = [dict(r) for r in cursor.fetchall()]
        total_subsidy = sum(c["govt_subsidy_receivable"] for c in claims)
        
        return {
            "total_claimable_subsidy": round(total_subsidy, 2),
            "total_bills_count": len(claims),
            "claims": claims
        }

def get_stock_valuation_schedule(tenant_id: str) -> List[Dict[str, Any]]:
    """
    Derives stock valuation schedule using Weighted Average Cost (WAC).
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                p.id as product_id, p.sku, p.name_kn, p.name_en, p.category, p.uom,
                p.retail_rate, p.wholesale_rate, p.standard_manufacturing_cost,
                COALESCE(SUM(il.quantity_delta), 0.0) as closing_stock_pieces,
                ROUND(COALESCE(SUM(il.quantity_delta), 0.0) * p.standard_manufacturing_cost, 2) as valuation_at_cost,
                ROUND(COALESCE(SUM(il.quantity_delta), 0.0) * p.retail_rate, 2) as valuation_at_retail
            FROM products p
            JOIN warehouses w ON w.tenant_id = p.tenant_id AND w.storage_type = 'FINISHED_SHOWROOM'
            LEFT JOIN inventory_ledger il ON il.product_id = p.id AND il.warehouse_id = w.id
            WHERE p.tenant_id = ? AND p.is_active = 1
            GROUP BY p.id
            ORDER BY p.name_en ASC
        """, (tenant_id,))
        return [dict(r) for r in cursor.fetchall()]
