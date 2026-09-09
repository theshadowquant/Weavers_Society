# Karnataka Handloom Cooperative Management Platform
### ಕರ್ನಾಟಕ ಕೈಮಗ್ಗ ಸಹಕಾರ ಡಿಜಿಟಲ್ ವೇದಿಕೆ

A greenfield, multi-tenant digital operating platform designed specifically for **Handloom Cooperative Societies across Karnataka, India**.

Built from first principles under the statutory operational framework of the *Karnataka Co-operative Societies Act, 1959* and the *Karnataka Directorate of Handlooms & Textiles*.

---

## 🏛️ Key Capabilities

- **Operational Command Center ("Digital Headquarters")**:
  - Live pulse: Today's showroom collections, active yarn held at home looms (WIP Kgs), unpaid piece-rate wages, and accumulated statutory 8% Thrift Welfare Fund (*ಉಳಿತಾಯ ನಿಧಿ*).
  - Automated operational alerts (e.g. yarn pending >28 days on home looms).

- **Weaver Ecosystem & Custody Passbooks**:
  - Full member registry with cooperative membership IDs, loom types (Pit, Frame, Jacquard), and artisan welfare passes.
  - Transparent yarn custody balances, wage disbursements, and 8% retirement thrift reserve accounts.

- **Cottage Production Allotment (*Hanchike*) & Technical Inspection (*GRN*)**:
  - Direct yarn allotment to cottage looms, tracking count specs, hank weights, and target piece counts.
  - Technical fabric inspection (*ಗುಣಮಟ್ಟ ಪರಿಶೀಲನೆ*) with pick grading (Grade A / Grade B / Reject).
  - Standard **3% wastage tolerance allowance** accounting.
  - Automatic piece-wage calculation with 8% Thrift Fund deduction.

- **Multi-State Signed Inventory Ledger**:
  - Four distinct physical operational states:
    1. `RAW_YARN_GODOWN` (Cotton hanks, mulberry silk, art-silk zari)
    2. `WEAVER_CUSTODY_WIP` (Yarn distributed to member looms)
    3. `FINISHED_SHOWROOM` (Handloom saris, dhotis, dress goods)
    4. `WHOLESALE_DEPOT` (Bulk apex dispatches: Cauvery Handlooms, Priyadarshini)
  - Non-destructive, signed journal entries with Weighted Average Cost (WAC) valuation.

- **Unified Sales Engine & 20% Directorate Festival Rebate**:
  - Retail showroom billing & wholesale order dispatches.
  - Automatic 20% Directorate Festival Rebate calculation with financial segregation of customer net payable vs. **State Subsidy Receivable**.
  - Direct compilation of **Directorate Rebate Claims Annexure-I Schedule** for government audit submissions.

- **8-Step Serious Society Onboarding Wizard**:
  - Step-by-step registration for any cooperative society: Profile, ARCS Jurisdiction, Physical Godowns, Weaver Demographics, Office Bearers, DCC Bank / Treasury Accounts, Yarn Counts, and Admin Credentials.

- **First-Class Bilingual Localization (English + ಕನ್ನಡ)**:
  - Complete institutional cooperative typography and terminology.
  - Printable bilingual thermal receipts and Form-A daybooks.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- `fastapi`, `uvicorn`, `pydantic`

### Installation & Execution

1. **Clone the repository**:
   ```bash
   git clone https://github.com/theshadowquant/Weavers_Society.git
   cd Weavers_Society
   ```

2. **Initialize and Seed Database**:
   ```bash
   python app/database/seed.py
   ```

3. **Start the Platform Server**:
   ```bash
   python run_server.py
   ```
   The application will be live at: `http://127.0.0.1:8000`

### Demonstration Accounts:
- **Gadag Cotton Weavers Co-op**:
  - Identifier: `admin@gadag.coop`
  - Password: `admin123`
  - Tenant: `gadag-weavers-coop`
- **Ilkal Traditional Silk Sari Co-op**:
  - Identifier: `secretary@ilkal.coop`
  - Password: `admin123`
  - Tenant: `ilkal-silk-coop`

---

## 🧪 Verification & Automated Tests

```bash
# Test Cross-Tenant Data Isolation
python app/tests/test_tenant_isolation.py

# Test Multi-State Inventory Ledger Immutability
python app/tests/test_inventory_ledger.py

# Full End-to-End Operational Lifecycle
python app/tests/e2e_workflow_test.py
```

---

## 📄 License
Proprietary & Confidential - Built for Karnataka Handloom Cooperative Societies.
