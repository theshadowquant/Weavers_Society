import uuid
from typing import List, Dict, Any
from fastapi import HTTPException
from app.database.session import get_db
from app.models.schemas import ProductionAllotmentCreate, InspectionReceiptCreate
from app.services.inventory_service import append_ledger_entry, get_yarn_lot_stock_in_godown
from app.core.audit import log_audit_event

def create_production_allotment(tenant_id: str, user_id: str, data: ProductionAllotmentCreate) -> Dict[str, Any]:
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check allotment number uniqueness
        cursor.execute("SELECT id FROM production_allotments WHERE tenant_id = ? AND allotment_no = ?", (tenant_id, data.allotment_no))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail=f"Allotment No '{data.allotment_no}' already exists.")
            
        # Verify yarn lot stocks in Central Yarn Godown
        cursor.execute("SELECT id FROM warehouses WHERE tenant_id = ? AND storage_type = 'RAW_YARN_GODOWN' LIMIT 1", (tenant_id,))
        godown_row = cursor.fetchone()
        if not godown_row:
            raise HTTPException(status_code=500, detail="Central Raw Yarn Godown not configured for this society.")
        godown_id = godown_row["id"]
        
        cursor.execute("SELECT id FROM warehouses WHERE tenant_id = ? AND storage_type = 'WEAVER_CUSTODY_WIP' LIMIT 1", (tenant_id,))
        loom_wip_row = cursor.fetchone()
        if not loom_wip_row:
            raise HTTPException(status_code=500, detail="Weaver Cottage Looms WIP node not configured.")
        loom_wip_id = loom_wip_row["id"]
        
        warp_avail = get_yarn_lot_stock_in_godown(tenant_id, data.warp_yarn_lot_id)
        if warp_avail < data.warp_issued_kgs:
            raise HTTPException(status_code=400, detail=f"Insufficient warp yarn stock in godown. Available: {warp_avail} kg, Requested: {data.warp_issued_kgs} kg")
            
        weft_avail = get_yarn_lot_stock_in_godown(tenant_id, data.weft_yarn_lot_id)
        if weft_avail < data.weft_issued_kgs:
            raise HTTPException(status_code=400, detail=f"Insufficient weft yarn stock in godown. Available: {weft_avail} kg, Requested: {data.weft_issued_kgs} kg")
            
        # Insert Allotment
        allotment_id = str(uuid.uuid4())
        conn.execute("""
            INSERT INTO production_allotments (
                id, tenant_id, allotment_no, weaver_id, product_id,
                warp_yarn_lot_id, warp_issued_kgs, weft_yarn_lot_id, weft_issued_kgs,
                target_pieces, agreed_piece_wage, reed_pick_specs, issue_date,
                expected_return_date, status, issued_by, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'WITH_WEAVER', ?, ?)
        """, (
            allotment_id, tenant_id, data.allotment_no, data.weaver_id, data.product_id,
            data.warp_yarn_lot_id, data.warp_issued_kgs, data.weft_yarn_lot_id, data.weft_issued_kgs,
            data.target_pieces, data.agreed_piece_wage, data.reed_pick_specs, data.issue_date,
            data.expected_return_date, user_id, data.notes
        ))
        
        # Move Yarn from RAW_YARN_GODOWN to WEAVER_CUSTODY_WIP
        # Warp outward from Godown
        append_ledger_entry(
            conn=conn, tenant_id=tenant_id, warehouse_id=godown_id,
            movement_type="LOOM_ALLOTMENT_ISSUE", quantity_delta=-data.warp_issued_kgs,
            unit_cost=0.0, reference_type="ALLOTMENT", reference_id=allotment_id,
            performed_by=user_id, yarn_lot_id=data.warp_yarn_lot_id,
            notes=f"Warp Issue for Allotment {data.allotment_no}"
        )
        # Warp inward to Weaver Loom Custody WIP
        append_ledger_entry(
            conn=conn, tenant_id=tenant_id, warehouse_id=loom_wip_id,
            movement_type="LOOM_CUSTODY_INWARD", quantity_delta=data.warp_issued_kgs,
            unit_cost=0.0, reference_type="ALLOTMENT", reference_id=allotment_id,
            performed_by=user_id, yarn_lot_id=data.warp_yarn_lot_id,
            notes=f"Warp in Weaver Custody: {data.allotment_no}"
        )
        # Weft outward from Godown
        append_ledger_entry(
            conn=conn, tenant_id=tenant_id, warehouse_id=godown_id,
            movement_type="LOOM_ALLOTMENT_ISSUE", quantity_delta=-data.weft_issued_kgs,
            unit_cost=0.0, reference_type="ALLOTMENT", reference_id=allotment_id,
            performed_by=user_id, yarn_lot_id=data.weft_yarn_lot_id,
            notes=f"Weft Issue for Allotment {data.allotment_no}"
        )
        # Weft inward to Weaver Loom Custody WIP
        append_ledger_entry(
            conn=conn, tenant_id=tenant_id, warehouse_id=loom_wip_id,
            movement_type="LOOM_CUSTODY_INWARD", quantity_delta=data.weft_issued_kgs,
            unit_cost=0.0, reference_type="ALLOTMENT", reference_id=allotment_id,
            performed_by=user_id, yarn_lot_id=data.weft_yarn_lot_id,
            notes=f"Weft in Weaver Custody: {data.allotment_no}"
        )
        
        log_audit_event(
            conn=conn, tenant_id=tenant_id, action="HANCHIKE_ALLOTMENT_ISSUED",
            entity_type="production_allotments", entity_id=allotment_id, user_id=user_id,
            new_values={"allotment_no": data.allotment_no, "target_pieces": data.target_pieces}
        )
        
        return {"allotment_id": allotment_id, "allotment_no": data.allotment_no, "status": "WITH_WEAVER"}

def process_technical_inspection_receipt(tenant_id: str, user_id: str, data: InspectionReceiptCreate) -> Dict[str, Any]:
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT pa.*, wm.thrift_fund_rate, wm.id as weaver_member_id, p.standard_manufacturing_cost
            FROM production_allotments pa
            JOIN weaver_members wm ON wm.id = pa.weaver_id
            JOIN products p ON p.id = pa.product_id
            WHERE pa.tenant_id = ? AND pa.id = ?
        """, (tenant_id, data.allotment_id))
        allotment = cursor.fetchone()
        if not allotment:
            raise HTTPException(status_code=404, detail="Production allotment not found.")
            
        receipt_id = str(uuid.uuid4())
        receipt_no = f"GRN-{uuid.uuid4().hex[:6].upper()}"
        
        # Accepted Pieces = First Quality + Second Quality
        accepted_pieces = data.first_quality_count + data.second_quality_count
        wage_rate = float(allotment["agreed_piece_wage"])
        gross_wages = accepted_pieces * wage_rate
        
        # Statutory 8% Thrift Fund deduction under KCS Act 1959
        tf_rate = float(allotment["thrift_fund_rate"])
        thrift_deduction = round(gross_wages * (tf_rate / 100.0), 2)
        net_wages = round(gross_wages - thrift_deduction, 2)
        
        # 1. Insert Inspection Receipt
        conn.execute("""
            INSERT INTO inspection_receipts (
                id, tenant_id, receipt_no, allotment_id, weaver_id,
                product_id, receiving_warehouse_id, inspection_date,
                pieces_received, first_quality_count, second_quality_count, rejected_count,
                measured_meters, weft_yarn_scrap_returned_kgs, allowable_wastage_pct,
                shortage_penalty_amount, gross_wages_earned, thrift_fund_deduction,
                net_wages_credited, inspection_notes, inspected_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0.0, ?, ?, ?, ?, ?)
        """, (
            receipt_id, tenant_id, receipt_no, data.allotment_id, allotment["weaver_id"],
            allotment["product_id"], data.receiving_warehouse_id, data.inspection_date,
            data.pieces_received, data.first_quality_count, data.second_quality_count, data.rejected_count,
            data.measured_meters, data.weft_yarn_scrap_returned_kgs, data.allowable_wastage_pct,
            gross_wages, thrift_deduction, net_wages, data.inspection_notes, user_id
        ))
        
        # 2. Update Weaver Passbook Balance & Thrift Reserve
        conn.execute("""
            UPDATE weaver_members
            SET passbook_wage_balance = passbook_wage_balance + ?,
                thrift_fund_balance = thrift_fund_balance + ?
            WHERE id = ? AND tenant_id = ?
        """, (net_wages, thrift_deduction, allotment["weaver_id"], tenant_id))
        
        # 3. Post Accepted Pieces to FINISHED_SHOWROOM Inventory
        if accepted_pieces > 0:
            cost_basis = float(allotment["standard_manufacturing_cost"]) or wage_rate
            append_ledger_entry(
                conn=conn, tenant_id=tenant_id, warehouse_id=data.receiving_warehouse_id,
                movement_type="PRODUCTION_RECEIPT_ACCEPT", quantity_delta=float(accepted_pieces),
                unit_cost=cost_basis, reference_type="INSPECTION_RECEIPT", reference_id=receipt_id,
                performed_by=user_id, product_id=allotment["product_id"],
                notes=f"Inspected Woven Saris: {receipt_no} (1st: {data.first_quality_count}, 2nd: {data.second_quality_count})"
            )
            
        # 4. Update Allotment Status
        new_status = "COMPLETED" if (data.pieces_received >= allotment["target_pieces"]) else "PARTIALLY_RETURNED"
        conn.execute("UPDATE production_allotments SET status = ? WHERE id = ? AND tenant_id = ?", (new_status, data.allotment_id, tenant_id))
        
        log_audit_event(
            conn=conn, tenant_id=tenant_id, action="CLOTH_INSPECTION_ACCEPTED",
            entity_type="inspection_receipts", entity_id=receipt_id, user_id=user_id,
            new_values={"receipt_no": receipt_no, "accepted_pieces": accepted_pieces, "net_wages": net_wages}
        )
        
        return {
            "receipt_id": receipt_id,
            "receipt_no": receipt_no,
            "accepted_pieces": accepted_pieces,
            "gross_wages": gross_wages,
            "thrift_fund_deducted": thrift_deduction,
            "net_wages_credited": net_wages,
            "message": "Cloth inspected, weaver wage credited, and finished stock capitalized."
        }

def list_production_allotments(tenant_id: str) -> List[Dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT pa.*, wm.full_name_kn as weaver_name_kn, wm.full_name_en as weaver_name_en,
                   wm.membership_no, wm.village, p.name_kn as product_name_kn, p.name_en as product_name_en, p.sku
            FROM production_allotments pa
            JOIN weaver_members wm ON wm.id = pa.weaver_id
            JOIN products p ON p.id = pa.product_id
            WHERE pa.tenant_id = ?
            ORDER BY pa.issue_date DESC
        """, (tenant_id,))
        return [dict(r) for r in cursor.fetchall()]
