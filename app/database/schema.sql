-- Karnataka Handloom Cooperative Management Platform
-- First-Principles Multi-Tenant Database Schema DDL

PRAGMA foreign_keys = ON;

-- 1. TENANTS (Individual Handloom Cooperative Societies)
CREATE TABLE IF NOT EXISTS tenants (
    id TEXT PRIMARY KEY,
    slug TEXT UNIQUE NOT NULL,
    legal_name_en TEXT NOT NULL,
    legal_name_kn TEXT NOT NULL,
    registration_number TEXT NOT NULL,
    registration_date TEXT NOT NULL,
    society_type TEXT NOT NULL DEFAULT 'PRIMARY_WEAVERS_COOP',
    district TEXT NOT NULL,
    taluk TEXT NOT NULL,
    hobli_village TEXT NOT NULL,
    pincode TEXT NOT NULL,
    primary_phone TEXT NOT NULL,
    primary_email TEXT,
    registered_office_address TEXT NOT NULL,
    pan TEXT,
    gstin TEXT,
    directorate_society_code TEXT,
    bank_name TEXT,
    bank_account_no TEXT,
    bank_ifsc TEXT,
    members_count INTEGER NOT NULL DEFAULT 0,
    active_looms_count INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('TRIAL', 'ACTIVE', 'SUSPENDED', 'ARCHIVED')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_tenants_slug ON tenants(slug);

-- 2. ONBOARDING DRAFTS (Multi-step Resumable Onboarding)
CREATE TABLE IF NOT EXISTS tenant_onboarding_drafts (
    id TEXT PRIMARY KEY,
    contact_identifier TEXT NOT NULL,
    current_step INTEGER NOT NULL DEFAULT 1,
    form_data_json TEXT NOT NULL DEFAULT '{}',
    is_completed INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 3. USERS & RBAC
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE,
    phone TEXT UNIQUE,
    full_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    preferred_language TEXT NOT NULL DEFAULT 'kn' CHECK (preferred_language IN ('kn', 'en')),
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS user_tenant_roles (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN (
        'MANAGING_DIRECTOR',
        'SECRETARY',
        'ACCOUNTANT',
        'GODOWN_KEEPER',
        'QUALITY_INSPECTOR',
        'SHOWROOM_CASHIER',
        'AUDITOR_READONLY'
    )),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    CONSTRAINT uq_user_tenant UNIQUE (user_id, tenant_id)
);

-- 4. LOCATIONS / STORAGE NODES (Multi-State Inventory Separation)
CREATE TABLE IF NOT EXISTS warehouses (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
    code TEXT NOT NULL,
    name_en TEXT NOT NULL,
    name_kn TEXT NOT NULL,
    storage_type TEXT NOT NULL CHECK (storage_type IN (
        'RAW_YARN_GODOWN',
        'WEAVER_CUSTODY_WIP',
        'FINISHED_SHOWROOM',
        'WHOLESALE_DEPOT',
        'TRANSIT_NODE'
    )),
    address TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    CONSTRAINT uq_tenant_warehouse UNIQUE (tenant_id, code)
);

-- 5. YARN RAW MATERIAL LOTS
CREATE TABLE IF NOT EXISTS yarn_lots (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
    lot_number TEXT NOT NULL,
    yarn_type TEXT NOT NULL,                 -- 'COTTON', 'MULBERRY_SILK', 'TASSAR_SILK', 'ZARI', 'WOOL'
    count_spec TEXT NOT NULL,                -- e.g. '2/60s Combed', '20/22 Denier', '100s Mercerised'
    shade_code TEXT,                         -- Color code / Natural
    mill_name TEXT NOT NULL,                 -- Sourced spinning mill / NHDC depot
    hsn_code TEXT NOT NULL DEFAULT '5205',
    unit_cost_per_kg REAL NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    CONSTRAINT uq_tenant_yarn_lot UNIQUE (tenant_id, lot_number)
);

-- 6. PRODUCT MASTER (Finished Handloom Catalog)
CREATE TABLE IF NOT EXISTS products (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
    sku TEXT NOT NULL,
    name_en TEXT NOT NULL,
    name_kn TEXT NOT NULL,
    category TEXT NOT NULL,                  -- 'SARI', 'DHOTI', 'YARDAGE', 'TOWEL_DUKHI', 'KHANA'
    gi_tag_certified INTEGER NOT NULL DEFAULT 0, -- Geographical Indication Tag
    warp_count_spec TEXT,
    weft_count_spec TEXT,
    uom TEXT NOT NULL DEFAULT 'PCS',
    hsn_code TEXT NOT NULL DEFAULT '5208',
    standard_manufacturing_cost REAL NOT NULL DEFAULT 0.00,
    retail_rate REAL NOT NULL DEFAULT 0.00,
    wholesale_rate REAL NOT NULL DEFAULT 0.00,
    tax_rate REAL NOT NULL DEFAULT 5.00,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    CONSTRAINT uq_tenant_product_sku UNIQUE (tenant_id, sku)
);

-- 7. WEAVER ARTISANAL PROFILES & SHAREHOLDERS
CREATE TABLE IF NOT EXISTS weaver_members (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
    membership_no TEXT NOT NULL,
    full_name_en TEXT NOT NULL,
    full_name_kn TEXT NOT NULL,
    phone TEXT,
    village TEXT NOT NULL,
    taluk TEXT NOT NULL,
    loom_type TEXT NOT NULL DEFAULT 'PIT_LOOM' CHECK (loom_type IN ('PIT_LOOM', 'FRAME_LOOM', 'JACQUARD_LOOM', 'RAISED_PIT_LOOM')),
    active_looms_count INTEGER NOT NULL DEFAULT 1,
    pehchan_card_id TEXT,                    -- Ministry of Textiles National Weaver ID
    bank_name TEXT,
    bank_account_no TEXT,
    bank_ifsc TEXT,
    thrift_fund_rate REAL NOT NULL DEFAULT 8.00, -- Statutory Thrift Fund % (KCS Act)
    passbook_wage_balance REAL NOT NULL DEFAULT 0.00, -- Accrued unpaid weaving wages
    thrift_fund_balance REAL NOT NULL DEFAULT 0.00,   -- Accumulated welfare savings
    advances_outstanding REAL NOT NULL DEFAULT 0.00,  -- Pending festive advances
    status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'SUSPENDED', 'RETIRED')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    CONSTRAINT uq_tenant_weaver_mbr UNIQUE (tenant_id, membership_no)
);

-- 8. COTTAGE PRODUCTION ALLOTMENTS (Hanchike)
CREATE TABLE IF NOT EXISTS production_allotments (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
    allotment_no TEXT NOT NULL,              -- e.g. 'PO/HNK/2026/014'
    weaver_id TEXT NOT NULL REFERENCES weaver_members(id) ON DELETE RESTRICT,
    product_id TEXT NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    warp_yarn_lot_id TEXT NOT NULL REFERENCES yarn_lots(id) ON DELETE RESTRICT,
    warp_issued_kgs REAL NOT NULL,
    weft_yarn_lot_id TEXT NOT NULL REFERENCES yarn_lots(id) ON DELETE RESTRICT,
    weft_issued_kgs REAL NOT NULL,
    target_pieces INTEGER NOT NULL,
    agreed_piece_wage REAL NOT NULL,
    reed_pick_specs TEXT,
    issue_date TEXT NOT NULL,
    expected_return_date TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'WITH_WEAVER' CHECK (status IN ('WITH_WEAVER', 'PARTIALLY_RETURNED', 'COMPLETED', 'CANCELLED')),
    issued_by TEXT NOT NULL,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    CONSTRAINT uq_tenant_allotment UNIQUE (tenant_id, allotment_no)
);

-- 9. TECHNICAL QUALITY INSPECTION & GOODS RECEIPTS (GRN)
CREATE TABLE IF NOT EXISTS inspection_receipts (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
    receipt_no TEXT NOT NULL,                -- e.g. 'GRN/2026/042'
    allotment_id TEXT NOT NULL REFERENCES production_allotments(id) ON DELETE RESTRICT,
    weaver_id TEXT NOT NULL REFERENCES weaver_members(id) ON DELETE RESTRICT,
    product_id TEXT NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    receiving_warehouse_id TEXT NOT NULL REFERENCES warehouses(id) ON DELETE RESTRICT,
    inspection_date TEXT NOT NULL,
    pieces_received INTEGER NOT NULL,
    first_quality_count INTEGER NOT NULL,
    second_quality_count INTEGER NOT NULL,
    rejected_count INTEGER NOT NULL,
    measured_meters REAL NOT NULL,
    weft_yarn_scrap_returned_kgs REAL NOT NULL DEFAULT 0.0,
    allowable_wastage_pct REAL NOT NULL DEFAULT 3.0,
    shortage_penalty_amount REAL NOT NULL DEFAULT 0.0,
    gross_wages_earned REAL NOT NULL,
    thrift_fund_deduction REAL NOT NULL,
    net_wages_credited REAL NOT NULL,
    inspection_notes TEXT,
    inspected_by TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    CONSTRAINT uq_tenant_receipt UNIQUE (tenant_id, receipt_no)
);

-- 10. SUPPLIERS (NHDC, Co-op Mills, Dye Houses)
CREATE TABLE IF NOT EXISTS suppliers (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
    name TEXT NOT NULL,
    supplier_type TEXT NOT NULL DEFAULT 'YARN_MILL' CHECK (supplier_type IN ('NHDC_DEPOT', 'COOP_SPINNING_MILL', 'PRIVATE_MILL', 'DYES_CHEMICALS')),
    contact_person TEXT,
    phone TEXT,
    gstin TEXT,
    address TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 11. PURCHASE INVOICES (Yarn & Supplies)
CREATE TABLE IF NOT EXISTS purchase_invoices (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
    supplier_id TEXT NOT NULL REFERENCES suppliers(id) ON DELETE RESTRICT,
    invoice_no TEXT NOT NULL,
    society_entry_no TEXT NOT NULL,
    invoice_date TEXT NOT NULL,
    receiving_warehouse_id TEXT NOT NULL REFERENCES warehouses(id) ON DELETE RESTRICT,
    subtotal REAL NOT NULL,
    tax_amount REAL NOT NULL,
    total_amount REAL NOT NULL,
    payment_status TEXT NOT NULL DEFAULT 'UNPAID' CHECK (payment_status IN ('UNPAID', 'PARTIAL', 'PAID')),
    status TEXT NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT', 'VERIFIED', 'POSTED', 'CANCELLED')),
    notes TEXT,
    verified_by TEXT,
    posted_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    CONSTRAINT uq_tenant_purchase_entry UNIQUE (tenant_id, society_entry_no)
);

CREATE TABLE IF NOT EXISTS purchase_items (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
    purchase_invoice_id TEXT NOT NULL REFERENCES purchase_invoices(id) ON DELETE CASCADE,
    yarn_lot_id TEXT REFERENCES yarn_lots(id) ON DELETE RESTRICT,
    product_id TEXT REFERENCES products(id) ON DELETE RESTRICT,
    quantity_kgs REAL NOT NULL,
    rate_per_unit REAL NOT NULL,
    tax_rate REAL NOT NULL DEFAULT 5.0,
    tax_amount REAL NOT NULL,
    line_total REAL NOT NULL
);

-- 12. IMMUTABLE MULTI-STATE INVENTORY LEDGER
-- Physical stock transitions through operational states. No mutable stock columns.
CREATE TABLE IF NOT EXISTS inventory_ledger (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
    warehouse_id TEXT NOT NULL REFERENCES warehouses(id) ON DELETE RESTRICT,
    product_id TEXT REFERENCES products(id) ON DELETE RESTRICT,
    yarn_lot_id TEXT REFERENCES yarn_lots(id) ON DELETE RESTRICT,
    movement_type TEXT NOT NULL CHECK (movement_type IN (
        'PURCHASE_YARN_INWARD',
        'LOOM_ALLOTMENT_ISSUE',
        'LOOM_CUSTODY_INWARD',
        'PRODUCTION_RECEIPT_ACCEPT',
        'RETAIL_SALE',
        'WHOLESALE_SALE',
        'SALE_RETURN_INWARD',
        'PURCHASE_RETURN_OUTWARD',
        'DEPOT_TRANSFER_OUT',
        'DEPOT_TRANSFER_IN',
        'AUDIT_ADJUSTMENT'
    )),
    quantity_delta REAL NOT NULL,             -- Positive for inward, negative for outward
    unit_cost REAL NOT NULL,                  -- Cost basis for WAC valuation
    reference_type TEXT NOT NULL,             -- 'PURCHASE_INVOICE', 'ALLOTMENT', 'INSPECTION_RECEIPT', 'SALE_BILL'
    reference_id TEXT NOT NULL,
    performed_by TEXT NOT NULL,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_inv_ledger_lookup ON inventory_ledger(tenant_id, warehouse_id, product_id, yarn_lot_id);
CREATE INDEX IF NOT EXISTS idx_inv_ledger_time ON inventory_ledger(tenant_id, created_at DESC);

-- 13. GOVERNMENT REBATE SCHEMES (Karnataka Directorate of Handlooms)
CREATE TABLE IF NOT EXISTS scheme_configs (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
    scheme_name_en TEXT NOT NULL,
    scheme_name_kn TEXT NOT NULL,
    sanctioning_authority TEXT NOT NULL DEFAULT 'Directorate of Handlooms & Textiles, Govt of Karnataka',
    rebate_percentage REAL NOT NULL DEFAULT 20.00,
    state_share_percentage REAL NOT NULL DEFAULT 100.00,
    effective_from TEXT NOT NULL,
    effective_until TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 14. UNIFIED SALES ENGINE (Retail POS & Apex Wholesale)
CREATE TABLE IF NOT EXISTS sales_transactions (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
    bill_number TEXT NOT NULL,
    sale_channel TEXT NOT NULL DEFAULT 'RETAIL_SHOWROOM' CHECK (sale_channel IN ('RETAIL_SHOWROOM', 'WHOLESALE_APEX', 'INSTITUTIONAL_CONTRACT')),
    warehouse_id TEXT NOT NULL REFERENCES warehouses(id) ON DELETE RESTRICT,
    customer_name TEXT,
    customer_phone TEXT,
    customer_gstin TEXT,
    customer_address TEXT,
    gross_amount REAL NOT NULL,
    discount_amount REAL NOT NULL DEFAULT 0.00,
    rebate_amount REAL NOT NULL DEFAULT 0.00,
    scheme_id TEXT REFERENCES scheme_configs(id),
    taxable_amount REAL NOT NULL,
    tax_amount REAL NOT NULL,
    round_off REAL NOT NULL DEFAULT 0.00,
    net_customer_payable REAL NOT NULL,
    govt_subsidy_receivable REAL NOT NULL DEFAULT 0.00,
    payment_mode TEXT NOT NULL DEFAULT 'CASH' CHECK (payment_mode IN ('CASH', 'UPI_QR', 'CARD', 'CREDIT_ACCOUNT', 'SPLIT')),
    payment_reference TEXT,
    status TEXT NOT NULL DEFAULT 'POSTED' CHECK (status IN ('POSTED', 'REVERSED', 'RETURN_PARTIAL')),
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    CONSTRAINT uq_tenant_bill UNIQUE (tenant_id, bill_number)
);

CREATE INDEX IF NOT EXISTS idx_sales_tenant_date ON sales_transactions(tenant_id, created_at DESC);

CREATE TABLE IF NOT EXISTS sales_items (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
    sale_id TEXT NOT NULL REFERENCES sales_transactions(id) ON DELETE CASCADE,
    product_id TEXT NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    quantity REAL NOT NULL,
    unit_rate REAL NOT NULL,
    discount_amount REAL NOT NULL DEFAULT 0.0,
    rebate_amount REAL NOT NULL DEFAULT 0.0,
    tax_rate REAL NOT NULL,
    tax_amount REAL NOT NULL,
    line_total REAL NOT NULL
);

-- 15. SALES RETURNS & REVERSALS (Non-destructive)
CREATE TABLE IF NOT EXISTS sales_returns (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
    return_number TEXT NOT NULL,
    original_sale_id TEXT NOT NULL REFERENCES sales_transactions(id) ON DELETE RESTRICT,
    return_date TEXT NOT NULL,
    total_refund_amount REAL NOT NULL,
    reason TEXT NOT NULL,
    authorized_by TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    CONSTRAINT uq_tenant_return_num UNIQUE (tenant_id, return_number)
);

-- 16. UNALTERABLE AUDIT TRAIL
CREATE TABLE IF NOT EXISTS audit_events (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    user_id TEXT,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    old_values_json TEXT,
    new_values_json TEXT,
    client_ip TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_events(tenant_id, created_at DESC);
