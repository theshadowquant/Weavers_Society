import uuid
from typing import List, Dict, Any, Optional
from fastapi import HTTPException
from app.database.session import get_db
from app.models.schemas import ProductCreate

def create_product(tenant_id: str, data: ProductCreate) -> Dict[str, Any]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM products WHERE tenant_id = ? AND sku = ?", (tenant_id, data.sku))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail=f"Product with SKU '{data.sku}' already exists.")
            
        product_id = str(uuid.uuid4())
        conn.execute("""
            INSERT INTO products (
                id, tenant_id, sku, name_en, name_kn, category,
                gi_tag_certified, warp_count_spec, weft_count_spec, uom, hsn_code,
                standard_manufacturing_cost, retail_rate, wholesale_rate, tax_rate, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, (
            product_id, tenant_id, data.sku, data.name_en, data.name_kn, data.category,
            data.gi_tag_certified, data.warp_count_spec, data.weft_count_spec, data.uom, data.hsn_code,
            data.standard_manufacturing_cost, data.retail_rate, data.wholesale_rate, data.tax_rate
        ))
        return {
            "id": product_id,
            "tenant_id": tenant_id,
            "sku": data.sku,
            "name_en": data.name_en,
            "name_kn": data.name_kn,
            "retail_rate": data.retail_rate,
            "wholesale_rate": data.wholesale_rate,
            "current_stock": 0.0
        }

def list_products(
    tenant_id: str,
    category: Optional[str] = None,
    search: Optional[str] = None,
    warehouse_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.cursor()
        
        # We join with inventory_ledger to compute real-time available stock
        if warehouse_id:
            query = """
                SELECT p.*, COALESCE(SUM(il.quantity_delta), 0.0) as current_stock
                FROM products p
                LEFT JOIN inventory_ledger il ON il.product_id = p.id AND il.tenant_id = p.tenant_id AND il.warehouse_id = ?
                WHERE p.tenant_id = ? AND p.is_active = 1
            """
            params = [warehouse_id, tenant_id]
        else:
            query = """
                SELECT p.*, COALESCE(SUM(il.quantity_delta), 0.0) as current_stock
                FROM products p
                LEFT JOIN inventory_ledger il ON il.product_id = p.id AND il.tenant_id = p.tenant_id
                WHERE p.tenant_id = ? AND p.is_active = 1
            """
            params = [tenant_id]
            
        if category:
            query += " AND p.category = ?"
            params.append(category)
            
        if search:
            query += " AND (p.name_en LIKE ? OR p.name_kn LIKE ? OR p.sku LIKE ?)"
            term = f"%{search}%"
            params.extend([term, term, term])
            
        query += " GROUP BY p.id ORDER BY p.name_en ASC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def get_product(tenant_id: str, product_id: str) -> Dict[str, Any]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.*, COALESCE(SUM(il.quantity_delta), 0.0) as current_stock
            FROM products p
            LEFT JOIN inventory_ledger il ON il.product_id = p.id AND il.tenant_id = p.tenant_id
            WHERE p.tenant_id = ? AND p.id = ?
            GROUP BY p.id
        """, (tenant_id, product_id))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Product not found.")
        return dict(row)
