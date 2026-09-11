import uuid
import sqlite3
from typing import List, Dict, Any, Optional
from app.database.session import get_db

def append_ledger_entry(
    conn: sqlite3.Connection,
    tenant_id: str,
    warehouse_id: str,
    movement_type: str,
    quantity_delta: float,
    unit_cost: float,
    reference_type: str,
    reference_id: str,
    performed_by: str,
    product_id: Optional[str] = None,
    yarn_lot_id: Optional[str] = None,
    notes: Optional[str] = None
) -> str:
    """
    Appends an immutable entry to the multi-state inventory ledger.
    """
    entry_id = str(uuid.uuid4())
    conn.execute("""
        INSERT INTO inventory_ledger (
            id, tenant_id, warehouse_id, product_id, yarn_lot_id,
            movement_type, quantity_delta, unit_cost, reference_type,
            reference_id, performed_by, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        entry_id, tenant_id, warehouse_id, product_id, yarn_lot_id,
        movement_type, quantity_delta, unit_cost, reference_type,
        reference_id, performed_by, notes
    ))
    return entry_id

def get_product_stock_in_warehouse(tenant_id: str, product_id: str, warehouse_id: str) -> float:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COALESCE(SUM(quantity_delta), 0.0) as current_stock
            FROM inventory_ledger
            WHERE tenant_id = ? AND product_id = ? AND warehouse_id = ?
        """, (tenant_id, product_id, warehouse_id))
        row = cursor.fetchone()
        return float(row["current_stock"]) if row else 0.0

def get_yarn_lot_stock_in_godown(tenant_id: str, yarn_lot_id: str) -> float:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COALESCE(SUM(il.quantity_delta), 0.0) as current_stock_kgs
            FROM inventory_ledger il
            JOIN warehouses w ON w.id = il.warehouse_id AND w.storage_type = 'RAW_YARN_GODOWN'
            WHERE il.tenant_id = ? AND il.yarn_lot_id = ?
        """, (tenant_id, yarn_lot_id))
        row = cursor.fetchone()
        return float(row["current_stock_kgs"]) if row else 0.0

def create_yarn_lot(tenant_id: str, data) -> Dict[str, Any]:
    lot_id = str(uuid.uuid4())
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM yarn_lots WHERE tenant_id = ? AND lot_number = ?", (tenant_id, data.lot_number))
        existing = cursor.fetchone()
        if existing:
            return {"id": existing["id"], "lot_number": data.lot_number, "status": "EXISTING"}
            
        conn.execute("""
            INSERT INTO yarn_lots (
                id, tenant_id, lot_number, yarn_type, count_spec, shade_code, mill_name, hsn_code, unit_cost_per_kg
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            lot_id, tenant_id, data.lot_number, data.yarn_type, data.count_spec,
            data.shade_code or "Natural/White", data.mill_name, getattr(data, "hsn_code", "5205") or "5205",
            data.unit_cost_per_kg
        ))
        return {
            "id": lot_id,
            "lot_number": data.lot_number,
            "yarn_type": data.yarn_type,
            "count_spec": data.count_spec,
            "mill_name": data.mill_name,
            "unit_cost_per_kg": data.unit_cost_per_kg,
            "status": "CREATED"
        }

def list_yarn_lots(tenant_id: str) -> List[Dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT yl.id, yl.lot_number, yl.yarn_type, yl.count_spec, yl.shade_code,
                   yl.mill_name, yl.hsn_code, yl.unit_cost_per_kg, yl.created_at,
                   COALESCE(SUM(il.quantity_delta), 0.0) as stock_kgs
            FROM yarn_lots yl
            LEFT JOIN warehouses w ON w.tenant_id = yl.tenant_id AND w.storage_type = 'RAW_YARN_GODOWN'
            LEFT JOIN inventory_ledger il ON il.yarn_lot_id = yl.id AND il.warehouse_id = w.id
            WHERE yl.tenant_id = ? AND yl.is_active = 1
            GROUP BY yl.id
            ORDER BY yl.created_at DESC
        """, (tenant_id,))
        return [dict(r) for r in cursor.fetchall()]

def get_inventory_status_by_state(tenant_id: str) -> Dict[str, Any]:
    """
    Aggregates inventory categorized by operational state:
    Raw Yarn Godown, Loom Custody WIP, Showroom Stock, Wholesale Stock.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 1. Raw Yarn Godown - show all registered yarn lots and their current stock
        cursor.execute("""
            SELECT yl.id, yl.lot_number, yl.yarn_type, yl.count_spec, yl.mill_name, yl.shade_code,
                   COALESCE(SUM(il.quantity_delta), 0.0) as stock_kgs,
                   yl.unit_cost_per_kg
            FROM yarn_lots yl
            LEFT JOIN warehouses w ON w.tenant_id = yl.tenant_id AND w.storage_type = 'RAW_YARN_GODOWN'
            LEFT JOIN inventory_ledger il ON il.yarn_lot_id = yl.id AND il.warehouse_id = w.id
            WHERE yl.tenant_id = ? AND yl.is_active = 1
            GROUP BY yl.id
            ORDER BY yl.created_at DESC
        """, (tenant_id,))
        raw_yarn = [dict(r) for r in cursor.fetchall()]
        
        # 2. Finished Goods in Showrooms
        cursor.execute("""
            SELECT p.id, p.sku, p.name_kn, p.name_en, p.category, p.uom, p.retail_rate, p.wholesale_rate,
                   COALESCE(SUM(il.quantity_delta), 0.0) as available_pieces,
                   w.name_kn as showroom_name_kn
            FROM products p
            JOIN warehouses w ON w.tenant_id = p.tenant_id AND w.storage_type = 'FINISHED_SHOWROOM'
            LEFT JOIN inventory_ledger il ON il.product_id = p.id AND il.warehouse_id = w.id
            WHERE p.tenant_id = ? AND p.is_active = 1
            GROUP BY p.id, w.id
            ORDER BY p.name_en ASC
        """, (tenant_id,))
        showroom_stock = [dict(r) for r in cursor.fetchall()]
        
        return {
            "raw_yarn_godown": raw_yarn,
            "showroom_stock": showroom_stock
        }

def get_stock_movement_journal(
    tenant_id: str,
    warehouse_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> List[Dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.cursor()
        query = """
            SELECT 
                il.id, il.created_at, il.movement_type, il.quantity_delta, il.unit_cost,
                il.reference_type, il.notes,
                w.name_kn as warehouse_name_kn, w.name_en as warehouse_name_en, w.storage_type,
                COALESCE(p.name_kn, yl.count_spec) as item_name_kn,
                COALESCE(p.name_en, yl.yarn_type) as item_name_en,
                COALESCE(p.sku, yl.lot_number) as item_code,
                COALESCE(p.uom, 'KGS') as uom
            FROM inventory_ledger il
            JOIN warehouses w ON w.id = il.warehouse_id
            LEFT JOIN products p ON p.id = il.product_id
            LEFT JOIN yarn_lots yl ON yl.id = il.yarn_lot_id
            WHERE il.tenant_id = ?
        """
        params = [tenant_id]
        if warehouse_id:
            query += " AND il.warehouse_id = ?"
            params.append(warehouse_id)
            
        query += " ORDER BY il.created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        cursor.execute(query, params)
        return [dict(r) for r in cursor.fetchall()]

def get_tenant_warehouses(tenant_id: str) -> List[Dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, tenant_id, code, name_en, name_kn, storage_type, address
            FROM warehouses
            WHERE tenant_id = ? AND is_active = 1
            ORDER BY code ASC
        """, (tenant_id,))
        return [dict(r) for r in cursor.fetchall()]

# Alias for backward compatibility
append_stock_movement = append_ledger_entry

