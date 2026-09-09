/**
 * Bilingual i18n Dictionary: English + Kannada (ಕನ್ನಡ)
 * Karnataka Handloom Cooperative Management Platform
 */

const translations = {
  kn: {
    // Header & Brand
    "brand.title": "ಕರ್ನಾಟಕ ಕೈಮಗ್ಗ ಸಹಕಾರ ಡಿಜಿಟಲ್ ವೇದಿಕೆ",
    "brand.subtitle": "ಕೈಮಗ್ಗ ನೇಕಾರರ ಸಹಕಾರ ಸಂಘಗಳ ಡಿಜಿಟಲ್ ಕಾರ್ಯಾಚರಣೆ ತಂತ್ರಾಂಶ (SaaS)",
    "btn.switch_lang": "English",
    
    // Primary Navigation
    "nav.operations": "ಕಾರ್ಯಾಚರಣೆ ಕೇಂದ್ರ",
    "nav.weavers": "ನೇಕಾರರ ಕಾರ್ಯಕ್ಷೇತ್ರ",
    "nav.production": "ಗೃಹ ಕೈಮಗ್ಗ ಉತ್ಪಾದನೆ (ಹಂಚಿಕೆ)",
    "nav.inventory": "ವಸ್ತು ಮತ್ತು ದಾಸ್ತಾನು",
    "nav.sales": "ಮಾರಾಟ ಮತ್ತು ಮಳಿಗೆ",
    "nav.schemes": "ಸರ್ಕಾರಿ ಯೋಜನೆಗಳು (ಕ್ಲೈಮ್)",
    "nav.reports": "ಶಾಸನಬದ್ಧ ವರದಿಗಳು",
    "nav.onboard_new": "+ ಹೊಸ ಸಂಘದ ನೋಂದಣಿ",

    // Command Center KPI Cards
    "pulse.today_collections": "ಇಂದಿನ ಕೌಂಟರ್ ಸಂಗ್ರಹ (Collections)",
    "pulse.yarn_with_weavers": "ನೇಕಾರರ ಬಳಿ ಇರುವ ನೂಲು (Cottage WIP)",
    "pulse.awaiting_inspection": "ತಪಾಸಣೆಗೆ ಬಾಕಿ ಇರುವ ಬಟ್ಟೆ (Awaiting QC)",
    "pulse.unpaid_wages": "ಬಾಕಿ ಮಗ್ಗದ ಕೂಲಿ (Unsettled Wages)",
    "pulse.unclaimed_rebate": "ಸರ್ಕಾರಿ ೨೦% ರಿಯಾಯಿತಿ ಕ್ಲೈಮ್ ಬಾಕಿ",
    "pulse.active_weavers": "ಸಕ್ರಿಯ ಸದಸ್ಯ ನೇಕಾರರು",

    // Command Center Alerts & Sections
    "cmd.urgent_alerts": "ತುರ್ತು ಕಾರ್ಯಾಚರಣಾ ಎಚ್ಚರಿಕೆಗಳು",
    "cmd.recent_journal": "ಇತ್ತೀಚಿನ ದಾಸ್ತಾನು ವಹಿವಾಟು ಜರ್ನಲ್",
    "cmd.view_all": "ಎಲ್ಲವನ್ನೂ ವೀಕ್ಷಿಸಿ",
    
    // Weaver Ecosystem
    "weavers.title": "ನೋಂದಾಯಿತ ಕೈಮಗ್ಗ ನೇಕಾರ ಸದಸ್ಯರು",
    "weavers.add_btn": "+ ಹೊಸ ನೇಕಾರರನ್ನು ಸೇರಿಸಿ",
    "weavers.col_mbr": "ಸದಸ್ಯತ್ವ ಸಂಖ್ಯೆ",
    "weavers.col_name": "ನೇಕಾರರ ಹೆಸರು",
    "weavers.col_village": "ಗ್ರಾಮ / ತಾಲೂಕು",
    "weavers.col_loom": "ಮಗ್ಗದ ವಿವರ",
    "weavers.col_yarn_custody": "ಬಳಿಯಲ್ಲಿರುವ ನೂಲು (WIP)",
    "weavers.col_wage_balance": "ವೇತನ ಬಾಕಿ ಶಿಲ್ಕು",
    "weavers.col_thrift": "ಉಳಿತಾಯ ನಿಧಿ (8% TF)",
    "weavers.view_profile": "ಕಾರ್ಯಾಚರಣಾ ಪ್ರೊಫೈಲ್",

    // Production & QC
    "prod.title": "ಗೃಹ ಕೈಮಗ್ಗ ಉತ್ಪಾದನಾ ಹಂಚಿಕೆ ಮತ್ತು ತಪಾಸಣೆ",
    "prod.issue_allotment": "+ ನೂಲು ಹಂಚಿಕೆ ಮಾಡಿ (Hanchike)",
    "prod.inspect_receipt": "+ ನೇಯ್ದ ಬಟ್ಟೆ ತಪಾಸಣೆ & ಜಮೆ (GRN)",
    "prod.col_allot_no": "ಹಂಚಿಕೆ ಸಂಖ್ಯೆ",
    "prod.col_weaver": "ನೇಕಾರರು",
    "prod.col_product": "ಉತ್ಪನ್ನ",
    "prod.col_target": "ಗುರಿ (ಸಂಖ್ಯೆ)",
    "prod.col_wage_rate": "ಮಗ್ಗದ ಕೂಲಿ ದರ/ಸೀರೆಗೆ",
    "prod.col_due_date": "ನಿಗದಿತ ದಿನಾಂಕ",
    "prod.col_status": "ಸ್ಥಿತಿ",

    // Multi-State Inventory
    "inv.title": "ಬಹು-ಹಂತದ ದಾಸ್ತಾನು ಲೆಡ್ಜರ್ (Multi-State Stock)",
    "inv.tab_status": "ದಾಸ್ತಾನು ಸ್ಥಿತಿ (ಗೋದಾಮು / ಮಗ್ಗ / ಮಳಿಗೆ)",
    "inv.tab_journal": "ಅಪರಿವರ್ತನೀಯ ವಹಿವಾಟು ಜರ್ನಲ್",
    "inv.tab_valuation": "ದಾಸ್ತಾನು ಮೌಲ್ಯಮಾಪನ (WAC Valuation)",
    "inv.godown_yarn": "ಕೇಂದ್ರ ನೂಲು ಗೋದಾಮು (Raw Yarn)",
    "inv.showroom_stock": "ಮಾರಾಟ ಮಳಿಗೆ ಸಿದ್ಧ ದಾಸ್ತಾನು (Showroom Stock)",

    // Sales & Depots
    "sales.title": "ಏಕೀಕೃತ ಮಾರಾಟ ಕೌಂಟರ್ (Showroom POS & Wholesale)",
    "sales.cart_title": "ಗ್ರಾಹಕರ ಬಿಲ್ಲಿಂಗ್ ಪಟ್ಟಿ",
    "sales.festival_rebate_toggle": "ಕರ್ನಾಟಕ ಸರ್ಕಾರದ ೨೦% ವಿಶೇಷ ರಿಯಾಯಿತಿ ಯೋಜನೆ ಅನ್ವಯಿಸಿ",
    "sales.gross": "ಒಟ್ಟು ಬೆಲೆ (Gross):",
    "sales.rebate_deduction": "ಸರ್ಕಾರಿ ೨೦% ರಿಯಾಯಿತಿ:",
    "sales.tax": "ಜಿಎಸ್‍ಟಿ (GST 5%):",
    "sales.net_payable": "ಗ್ರಾಹಕರು ಪಾವತಿಸಬೇಕಾದ ಮೊತ್ತ:",
    "sales.subsidy_receivable": "ಸರ್ಕಾರದಿಂದ ಸಂಘಕ್ಕೆ ಬರಬೇಕಾದ ಸಹಾಯಧನ:",
    "sales.complete_btn": "ಬಿಲ್ ಪೂರ್ಣಗೊಳಿಸಿ ಮತ್ತು ಮುದ್ರಿಸಿ ✓",

    // Reports
    "rep.title": "ಶಾಸನಬದ್ಧ ಸಹಕಾರ ರಿಜಿಸ್ಟರ್‌ಗಳು",
    "rep.daybook": "ದಿನಚರಿ ಪುಸ್ತಕ (Daybook - Form A)",
    "rep.weaver_material": "ನೂಲು ಬ್ಯಾಲೆನ್ಸ್ ರಿಜಿಸ್ಟರ್",
    "rep.weaver_wages": "ನೇಕಾರರ ಕೂಲಿ ಮತ್ತು ಉಳಿತಾಯ ನಿಧಿ ರಿಜಿಸ್ಟರ್",
    "rep.rebate_claims": "ನಿರ್ದೇಶನಾಲಯದ ರಿಯಾಯಿತಿ ಕ್ಲೈಮ್ ಶೆಡ್ಯೂಲ್",

    // Onboarding
    "onb.hero_title": "ಕರ್ನಾಟಕದ ಕೈಮಗ್ಗ ಸಹಕಾರ ಸಂಘಗಳಿಗೆ ಡಿಜಿಟಲ್ ಕೇಂದ್ರ",
    "onb.hero_subtitle": "ಪ್ರತಿಯೊಂದು ಸಹಕಾರ ಸಂಘವು ತನ್ನದೇ ಆದ ಡಿಜಿಟಲ್ ಹೆಡ್‌ಕ್ವಾರ್ಟರ್ಸ್ ಸ್ಥಾಪಿಸಿ ನೇಕಾರರು, ನೂಲು ಹಂಚಿಕೆ, ಮಗ್ಗದ ಕೂಲಿ, ಮಾರಾಟ ಮತ್ತು ಸರ್ಕಾರಿ ರಿಯಾಯಿತಿಗಳನ್ನು ಸುಲಭವಾಗಿ ನಿರ್ವಹಿಸಬಹುದು.",
    "onb.start_btn": "ಹೊಸ ಸಂಘದ ನೋಂದಣಿ ಪ್ರಾರಂಭಿಸಿ →",
    "onb.login_btn": "ಸಂಘದ ಲಾಗಿನ್ ಪ್ರವೇಶಿಸಿ",
    "onb.step1_title": "೧. ಖಾತೆ ಮತ್ತು ಸಂಪರ್ಕ",
    "onb.step2_title": "೨. ಸಂಘದ ಶಾಸನಬದ್ಧ ಗುರುತು",
    "onb.step3_title": "೩. ಸ್ಥಳ ಮತ್ತು ವಿಳಾಸ",
    "onb.step4_title": "೪. ಅಧಿಕೃತ ಮತ್ತು ಬ್ಯಾಂಕ್ ವಿವರ",
    "onb.step5_title": "೫. ಕಾರ್ಯಾಚರಣೆ ಮತ್ತು ಮಗ್ಗಗಳು",
    "onb.step6_title": "೬. ಆಡಳಿತ ಮಂಡಳಿ / ಸಿಬ್ಬಂದಿ",
    "onb.step7_title": "೭. ಭಾಷೆ ಮತ್ತು ಆದ್ಯತೆ",
    "onb.step8_title": "೮. ಪರಿಶೀಲನೆ ಮತ್ತು ದೃಢೀಕರಣ",
    "onb.create_society_btn": "ಸಂಘದ ಡಿಜಿಟಲ್ ಕೇಂದ್ರವನ್ನು ರಚಿಸಿ (Create Society)"
  },
  
  en: {
    // Header & Brand
    "brand.title": "Karnataka Handloom Cooperative Management Platform",
    "brand.subtitle": "Digital Operating Headquarters for Handloom Weavers Cooperative Societies (SaaS)",
    "btn.switch_lang": "ಕನ್ನಡ",

    // Primary Navigation
    "nav.operations": "Operations Center",
    "nav.weavers": "Weaver Artisans",
    "nav.production": "Cottage Production (Hanchike)",
    "nav.inventory": "Multi-State Inventory",
    "nav.sales": "Sales & Depots",
    "nav.schemes": "Govt Rebate Schemes",
    "nav.reports": "Statutory Registers",
    "nav.onboard_new": "+ Register New Society",

    // Command Center KPI Cards
    "pulse.today_collections": "Today's Collections",
    "pulse.yarn_with_weavers": "Yarn with Weavers (Cottage WIP)",
    "pulse.awaiting_inspection": "Awaiting QC Inspection",
    "pulse.unpaid_wages": "Unsettled Weaving Wages",
    "pulse.unclaimed_rebate": "Unclaimed Govt 20% Rebates",
    "pulse.active_weavers": "Active Member Weavers",

    // Command Center Alerts & Sections
    "cmd.urgent_alerts": "Actionable Operational Alerts",
    "cmd.recent_journal": "Recent Stock Movement Journal",
    "cmd.view_all": "View All",

    // Weaver Ecosystem
    "weavers.title": "Registered Handloom Weaver Members",
    "weavers.add_btn": "+ Register New Weaver",
    "weavers.col_mbr": "Membership No",
    "weavers.col_name": "Weaver Name",
    "weavers.col_village": "Village / Taluk",
    "weavers.col_loom": "Loom Specs",
    "weavers.col_yarn_custody": "Yarn in Custody (WIP)",
    "weavers.col_wage_balance": "Wage Balance",
    "weavers.col_thrift": "Thrift Fund (8% TF)",
    "weavers.view_profile": "Operational Profile",

    // Production & QC
    "prod.title": "Cottage Loom Allotments & Technical Inspection",
    "prod.issue_allotment": "+ Issue Yarn Allotment (Hanchike)",
    "prod.inspect_receipt": "+ Inspect & Receive Woven Goods (GRN)",
    "prod.col_allot_no": "Allotment No",
    "prod.col_weaver": "Weaver",
    "prod.col_product": "Product",
    "prod.col_target": "Target (Pcs)",
    "prod.col_wage_rate": "Piece Wage Rate",
    "prod.col_due_date": "Due Date",
    "prod.col_status": "Status",

    // Multi-State Inventory
    "inv.title": "Multi-State Inventory Ledger",
    "inv.tab_status": "Stock State (Godown / Loom / Showroom)",
    "inv.tab_journal": "Immutable Movement Journal",
    "inv.tab_valuation": "Stock Valuation (WAC)",
    "inv.godown_yarn": "Central Yarn Godown",
    "inv.showroom_stock": "Finished Showroom Stock",

    // Sales & Depots
    "sales.title": "Unified Sales Terminal (Showroom POS & Wholesale)",
    "sales.cart_title": "Customer Billing Cart",
    "sales.festival_rebate_toggle": "Apply Karnataka Directorate 20% Special Festival Rebate",
    "sales.gross": "Gross Total:",
    "sales.rebate_deduction": "Govt 20% Rebate:",
    "sales.tax": "GST (5%):",
    "sales.net_payable": "Customer Net Payable:",
    "sales.subsidy_receivable": "Subsidy Claimable from State:",
    "sales.complete_btn": "Complete & Print Bill ✓",

    // Reports
    "rep.title": "Statutory Cooperative Registers",
    "rep.daybook": "Daily Daybook (Form A)",
    "rep.weaver_material": "Weaver Material Balance Register",
    "rep.weaver_wages": "Weaver Wage & Thrift Register",
    "rep.rebate_claims": "Directorate Rebate Claim Schedule",

    // Onboarding
    "onb.hero_title": "Digital Operating Headquarters for Karnataka Handloom Cooperatives",
    "onb.hero_subtitle": "Every Handloom Cooperative Society creates its own sovereign digital headquarters to govern weavers, yarn custody, piece wages, counter sales, and Directorate rebate subsidies.",
    "onb.start_btn": "Begin Society Registration →",
    "onb.login_btn": "Access Society Headquarters",
    "onb.step1_title": "1. Account & Credentials",
    "onb.step2_title": "2. Statutory Society Identity",
    "onb.step3_title": "3. Location & Geography",
    "onb.step4_title": "4. Official & Bank Details",
    "onb.step5_title": "5. Operations & Loom Footprint",
    "onb.step6_title": "6. Administration & Staff Roles",
    "onb.step7_title": "7. Language & Financial Year",
    "onb.step8_title": "8. Verification & Review",
    "onb.create_society_btn": "Initialize Society Digital Headquarters"
  }
};

let currentLanguage = localStorage.getItem("society_lang") || "kn";

function t(key) {
  const dict = translations[currentLanguage] || translations.kn;
  return dict[key] || translations.en[key] || key;
}

function formatCurrency(amount) {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 2
  }).format(amount || 0);
}

function setLanguage(lang) {
  currentLanguage = lang;
  localStorage.setItem("society_lang", lang);
  document.documentElement.lang = lang;
  applyTranslations();
  if (window.onLanguageChanged) {
    window.onLanguageChanged(lang);
  }
}

function toggleLanguage() {
  setLanguage(currentLanguage === "kn" ? "en" : "kn");
}

function applyTranslations() {
  document.querySelectorAll("[data-i18n]").forEach(el => {
    const key = el.getAttribute("data-i18n");
    el.innerText = t(key);
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach(el => {
    const key = el.getAttribute("data-i18n-placeholder");
    el.placeholder = t(key);
  });
  
  const langToggleBtn = document.getElementById("lang-toggle-btn");
  if (langToggleBtn) {
    langToggleBtn.innerText = t("btn.switch_lang");
  }
}
