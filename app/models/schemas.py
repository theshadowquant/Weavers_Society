from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

# --- ONBOARDING & AUTH ---
class OnboardingStepSave(BaseModel):
    contact_identifier: str
    current_step: int = Field(..., ge=1, le=8)
    form_data: Dict[str, Any]

class OnboardingFinalizeRequest(BaseModel):
    draft_id: Optional[str] = None
    # Step 1: Account
    primary_phone: str
    primary_email: Optional[str] = None
    admin_password: str
    admin_full_name: str
    # Step 2: Identity
    legal_name_en: str
    legal_name_kn: str
    slug: Optional[str] = None
    registration_number: str
    registration_date: str
    society_type: str = "PRIMARY_WEAVERS_COOP"
    # Step 3: Location
    district: str
    taluk: str
    hobli_village: str
    pincode: str
    registered_office_address: str
    # Step 4: Official Credentials
    pan: Optional[str] = None
    gstin: Optional[str] = None
    directorate_society_code: Optional[str] = None
    bank_name: Optional[str] = None
    bank_account_no: Optional[str] = None
    bank_ifsc: Optional[str] = None
    # Step 5: Operations Topology
    members_count: int = 50
    active_looms_count: int = 40
    # Step 6: Preferences
    preferred_language: str = "kn"

class LoginRequest(BaseModel):
    identifier: str
    password: str
    tenant_slug: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    tenant_id: str
    tenant_slug: str
    tenant_name_en: str
    tenant_name_kn: str
    district: str
    role: str
    preferred_language: str

# --- WEAVERS ---
class WeaverCreate(BaseModel):
    membership_no: str
    full_name_en: str
    full_name_kn: str
    phone: Optional[str] = None
    village: str
    taluk: str
    loom_type: str = "PIT_LOOM"
    active_looms_count: int = 1
    pehchan_card_id: Optional[str] = None
    bank_name: Optional[str] = None
    bank_account_no: Optional[str] = None
    bank_ifsc: Optional[str] = None
    thrift_fund_rate: float = 8.00

# --- PRODUCTION ALLOTMENT (HANCHIKE) ---
class ProductionAllotmentCreate(BaseModel):
    allotment_no: str
    weaver_id: str
    product_id: str
    warp_yarn_lot_id: str
    warp_issued_kgs: float
    weft_yarn_lot_id: str
    weft_issued_kgs: float
    target_pieces: int
    agreed_piece_wage: float
    reed_pick_specs: Optional[str] = None
    issue_date: str
    expected_return_date: str
    notes: Optional[str] = None

# --- TECHNICAL QC & GOODS INSPECTION ---
class InspectionReceiptCreate(BaseModel):
    allotment_id: str
    receiving_warehouse_id: str
    inspection_date: str
    pieces_received: int
    first_quality_count: int
    second_quality_count: int = 0
    rejected_count: int = 0
    measured_meters: float
    weft_yarn_scrap_returned_kgs: float = 0.0
    allowable_wastage_pct: float = 3.0
    inspection_notes: Optional[str] = None

# --- PRODUCTS & YARN LOTS ---
class YarnLotCreate(BaseModel):
    lot_number: str
    yarn_type: str # COTTON, MULBERRY_SILK, ZARI
    count_spec: str # 2/60s, 20/22 Silk
    shade_code: Optional[str] = None
    mill_name: str
    hsn_code: str = "5205"
    unit_cost_per_kg: float

class ProductCreate(BaseModel):
    sku: str
    name_en: str
    name_kn: str
    category: str # SARI, DHOTI, YARDAGE, KHANA
    gi_tag_certified: int = 0
    warp_count_spec: Optional[str] = None
    weft_count_spec: Optional[str] = None
    uom: str = "PCS"
    hsn_code: str = "5208"
    standard_manufacturing_cost: float = 0.0
    retail_rate: float = 0.0
    wholesale_rate: float = 0.0
    tax_rate: float = 5.0

# --- UNIFIED SALES & REBATES ---
class SalesItemCreate(BaseModel):
    product_id: str
    quantity: float
    unit_rate: Optional[float] = None
    discount_amount: float = 0.0

class SalesTransactionCreate(BaseModel):
    sale_channel: str = "RETAIL_SHOWROOM" # RETAIL_SHOWROOM, WHOLESALE_APEX, INSTITUTIONAL_CONTRACT
    warehouse_id: str
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_gstin: Optional[str] = None
    customer_address: Optional[str] = None
    apply_govt_rebate: bool = False
    scheme_id: Optional[str] = None
    payment_mode: str = "CASH" # CASH, UPI_QR, CARD, CREDIT_ACCOUNT
    payment_reference: Optional[str] = None
    items: List[SalesItemCreate]
