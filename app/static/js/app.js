/**
 * UI Controller & Domain Workflow Engine
 * Karnataka Handloom Cooperative Platform
 */

const state = {
  currentSection: "operations",
  currentTenant: null,
  warehouses: [],
  activeShowroomWarehouseId: null,
  activeGodownWarehouseId: null,
  cart: [],
  applyRebate: true,
  paymentMode: "CASH",
  onboardingStep: 1,
  onboardingDraftId: null,
  onboardingData: {},
  cachedProducts: []
};

// -------------------------------------------------------------------
// CLIENT-SIDE BIDIRECTIONAL AUTO-TRANSLATION (Kannada <-> English)
// -------------------------------------------------------------------
async function translateText(text, fromLang = "kn", toLang = "en") {
  if (!text || !text.trim()) return "";
  try {
    const url = `https://translate.googleapis.com/translate_a/single?client=gtx&sl=${fromLang}&tl=${toLang}&dt=t&q=${encodeURIComponent(text.trim())}`;
    const res = await fetch(url);
    const data = await res.json();
    if (data && data[0]) {
      return data[0].map(item => item[0]).join("").trim();
    }
  } catch (err) {
    console.warn("Auto-translate error:", err);
  }
  return "";
}

let translationDebounceTimer = null;
function setupAutoTranslate(sourceId, targetId, fromLang, toLang) {
  const src = document.getElementById(sourceId);
  const tgt = document.getElementById(targetId);
  if (!src || !tgt) return;

  src.addEventListener("input", () => {
    clearTimeout(translationDebounceTimer);
    translationDebounceTimer = setTimeout(async () => {
      const val = src.value.trim();
      if (!val) return;
      if (!tgt.value || tgt.dataset.autoFilled === "true") {
        const translated = await translateText(val, fromLang, toLang);
        if (translated) {
          tgt.value = translated;
          tgt.dataset.autoFilled = "true";
        }
      }
    }, 650);
  });

  tgt.addEventListener("input", () => {
    tgt.dataset.autoFilled = "false";
  });
}

async function triggerFieldTranslation(sourceId, targetId, fromLang, toLang) {
  const src = document.getElementById(sourceId);
  const tgt = document.getElementById(targetId);
  if (!src || !tgt) return;
  const val = src.value.trim();
  if (!val) return;

  const btn = event?.currentTarget;
  const originalLabel = btn ? btn.innerText : "";
  if (btn) btn.innerText = "⏳...";

  const translated = await translateText(val, fromLang, toLang);
  if (translated) {
    tgt.value = translated;
    tgt.dataset.autoFilled = "true";
  }
  if (btn) btn.innerText = originalLabel || (fromLang === "kn" ? "🔄 English" : "🔄 ಕನ್ನಡ");
}

// Application Bootstrap
document.addEventListener("DOMContentLoaded", async () => {
  try {
    setLanguage(localStorage.getItem("society_lang") || "kn");
    
    if (api.token && api.tenantInfo) {
      state.currentTenant = api.tenantInfo;
      await refreshTenantStorageNodes();
      updateTenantUI();
      showAppShell();
      navigateTo("operations");
    } else {
      showLandingPage();
    }
  } catch (err) {
    console.error("Initialization error:", err);
    showLandingPage();
  }

  setupGlobalListeners();
  initFirebaseStatus();
});

async function initFirebaseStatus() {
  const dot = document.getElementById("firebase-status-dot");
  const txt = document.getElementById("firebase-status-text");
  if (!dot || !txt) return;

  try {
    const status = await api.getFirebaseStatus();
    if (status.connected) {
      dot.style.background = "#10b981";
      const proj = status.project_id || "Live";
      txt.innerText = `☁️ Cloud: ${proj} (Active)`;
      txt.style.color = "#d1fae5";
    } else {
      dot.style.background = "#ef4444";
      txt.innerText = "☁️ Cloud: Offline";
      txt.style.color = "#fecaca";
    }
  } catch (err) {
    dot.style.background = "#f59e0b";
    txt.innerText = "☁️ Cloud: Connecting...";
    txt.style.color = "#fef3c7";
  }
}

async function handleCloudSyncClick() {
  if (!state.currentTenant) {
    alert("ದಯವಿಟ್ಟು ಮೊದಲು ನಿಮ್ಮ ಸಂಘದ ಖಾತೆಗೆ ಲಾಗಿನ್ ಮಾಡಿ (Please login to your society first).");
    return;
  }

  const txt = document.getElementById("firebase-status-text");
  const originalText = txt ? txt.innerText : "";
  if (txt) txt.innerText = "☁️ Syncing...";

  try {
    const res = await api.syncTenantToFirebase();
    if (res.synced) {
      alert(`ಸಂಘದ ಮಾಹಿತಿಯನ್ನು Cloud Firestore ಗೆ ಯಶಸ್ವಿಯಾಗಿ ಸಿಂಕ್ ಮಾಡಲಾಗಿದೆ!\nಸಂಘ: ${res.society_name || state.currentTenant.tenant_name_kn}\nನೇಕಾರರು: ${res.members_synced}\nಉತ್ಪನ್ನಗಳು: ${res.products_synced}\nಸ್ಥಿತಿ: Cloud Firestore Connected`);
    } else {
      alert("ಸಿಂಕ್ ವಿಫಲವಾಗಿದೆ: " + (res.reason || res.error || "Unknown error"));
    }
  } catch (err) {
    alert("ಕ್ಲೌಡ್ ಸಿಂಕ್ ದೋಷ: " + err.message);
  } finally {
    await initFirebaseStatus();
  }
}


function showLandingPage() {
  const l = document.getElementById("landing-section");
  const a = document.getElementById("app-shell");
  if (l) l.style.display = "block";
  if (a) a.style.display = "none";
}

function showAppShell() {
  const l = document.getElementById("landing-section");
  const a = document.getElementById("app-shell");
  if (l) l.style.display = "none";
  if (a) a.style.display = "block";
}

async function refreshTenantStorageNodes() {
  if (!state.currentTenant) return;
  try {
    const whs = await api.getTenantWarehouses();
    state.warehouses = whs || [];
    const showroom = state.warehouses.find(w => w.storage_type === 'FINISHED_SHOWROOM');
    state.activeShowroomWarehouseId = showroom ? showroom.id : null;
    const godown = state.warehouses.find(w => w.storage_type === 'RAW_YARN_GODOWN');
    state.activeGodownWarehouseId = godown ? godown.id : null;
  } catch (err) {
    console.warn("Could not load tenant warehouses:", err);
  }
}

function updateTenantUI() {
  const badge = document.getElementById("tenant-name-badge");
  if (badge && state.currentTenant) {
    const isKn = currentLanguage === "kn";
    badge.innerText = isKn ? state.currentTenant.tenant_name_kn : state.currentTenant.tenant_name_en;
  }

  const userBadge = document.getElementById("user-profile-badge");
  if (userBadge && state.currentTenant) {
    userBadge.innerText = `👤 ${state.currentTenant.user_full_name || 'User'} (${state.currentTenant.role || 'Member'})`;
  }

  // Handle Multi-Society Switcher Dropdown
  const switchSelect = document.getElementById("society-switch-select");
  if (switchSelect) {
    const authTenants = state.currentTenant?.authorized_tenants || [];
    if (authTenants.length > 1) {
      switchSelect.style.display = "inline-block";
      switchSelect.innerHTML = authTenants.map(t => `
        <option value="${t.tenant_id}" ${t.tenant_id === state.currentTenant.tenant_id ? 'selected' : ''}>
          🏛️ ${currentLanguage === 'kn' ? t.tenant_name_kn : t.tenant_name_en}
        </option>
      `).join("");
    } else {
      switchSelect.style.display = "none";
    }
  }
}

window.onLanguageChanged = () => {
  updateTenantUI();
  renderCurrentSection();
};

function openLoginModal() {
  const modal = document.getElementById("modal-login");
  const errBox = document.getElementById("login-error-msg");
  if (errBox) errBox.style.display = "none";
  const choiceGrp = document.getElementById("login-society-choice-group");
  if (choiceGrp) choiceGrp.style.display = "none";
  if (modal) modal.style.display = "flex";
}

async function handleLoginSubmit(e) {
  e.preventDefault();
  const ident = document.getElementById("login-identifier")?.value?.trim();
  const pwd = document.getElementById("login-password")?.value;
  const errBox = document.getElementById("login-error-msg");
  const btn = document.getElementById("btn-login-submit");

  if (!ident || !pwd) {
    if (errBox) {
      errBox.innerText = "ದಯವಿಟ್ಟು ಮೊಬೈಲ್/ಇಮೇಲ್ ಮತ್ತು ಪಾಸ್‌ವರ್ಡ್ ನಮೂದಿಸಿ.";
      errBox.style.display = "block";
    }
    return;
  }

  if (btn) btn.innerText = "ಪ್ರವೇಶಿಸಲಾಗುತ್ತಿದೆ...";

  try {
    const data = await api.login(ident, pwd);
    state.currentTenant = data;
    state.cart = [];
    await refreshTenantStorageNodes();
    updateTenantUI();
    closeAllModals();
    showAppShell();
    navigateTo("operations");
  } catch (err) {
    if (errBox) {
      errBox.innerText = "ಲಾಗಿನ್ ವಿಫಲವಾಗಿದೆ: " + err.message;
      errBox.style.display = "block";
    }
  } finally {
    if (btn) btn.innerText = "ಪ್ರವೇಶಿಸಿ (Login) ✓";
  }
}

async function handleTenantSwitch(targetTenantId) {
  if (!targetTenantId || targetTenantId === state.currentTenant?.tenant_id) return;
  try {
    const data = await api.switchTenant(targetTenantId);
    state.currentTenant = data;
    state.cart = [];
    await refreshTenantStorageNodes();
    updateTenantUI();
    renderCurrentSection();
  } catch (err) {
    alert("ಸಂಘ ಬದಲಾವಣೆ ವಿಫಲವಾಗಿದೆ: " + err.message);
  }
}

function handleLogout() {
  api.clearSession();
  state.currentTenant = null;
  state.warehouses = [];
  state.cart = [];
  showLandingPage();
}


// Navigation Controller
function navigateTo(sectionName) {
  state.currentSection = sectionName;
  document.querySelectorAll(".op-nav-btn").forEach(btn => {
    btn.classList.toggle("active", btn.getAttribute("data-section") === sectionName);
  });
  renderCurrentSection();
}

function renderCurrentSection() {
  document.querySelectorAll(".content-section").forEach(sec => sec.classList.remove("active"));
  const activeSec = document.getElementById(`sec-${state.currentSection}`);
  if (activeSec) activeSec.classList.add("active");

  switch (state.currentSection) {
    case "operations":
      loadCommandCenter();
      break;
    case "weavers":
      loadWeaversSection();
      break;
    case "production":
      loadProductionSection();
      break;
    case "inventory":
      loadInventorySection();
      break;
    case "sales":
      loadSalesSection();
      break;
    case "schemes":
      loadSchemesSection();
      break;
    case "reports":
      loadReportsSection("daybook");
      break;
    case "onboarding":
      startOnboardingWizard();
      break;
  }
}

// -------------------------------------------------------------------
// 1. OPERATIONAL COMMAND CENTER ("What is happening in my Society today?")
// -------------------------------------------------------------------
async function loadCommandCenter() {
  const container = document.getElementById("sec-operations");
  if (!container) return;

  try {
    const data = await api.getCommandCenter();

    container.innerHTML = `
      <!-- Operational Pulse KPI Grid -->
      <div class="pulse-grid">
        <div class="pulse-card">
          <div class="pulse-card-label" data-i18n="pulse.today_collections">ಇಂದಿನ ಕೌಂಟರ್ ಸಂಗ್ರಹ</div>
          <div class="pulse-card-value">${formatCurrency(data.today_sales.collections)}</div>
          <div class="pulse-card-sub">${data.today_sales.bills_count} ಬಿಲ್‌ಗಳು (ಒಟ್ಟು: ${formatCurrency(data.today_sales.gross_sales)})</div>
        </div>
        <div class="pulse-card">
          <div class="pulse-card-label" data-i18n="pulse.yarn_with_weavers">ನೇಕಾರರ ಬಳಿ ಇರುವ ನೂಲು (Cottage WIP)</div>
          <div class="pulse-card-value" style="color:var(--primary-gold);">${data.cottage_production.active_yarn_with_weavers_kgs} <small style="font-size:1rem;">Kgs</small></div>
          <div class="pulse-card-sub">${data.cottage_production.active_allotments_count} ಸಕ್ರಿಯ ಮಗ್ಗದ ಹಂಚಿಕೆಗಳು</div>
        </div>
        <div class="pulse-card">
          <div class="pulse-card-label" data-i18n="pulse.unpaid_wages">ಬಾಕಿ ಮಗ್ಗದ ಕೂಲಿ (Unsettled Wages)</div>
          <div class="pulse-card-value" style="color:var(--primary-crimson);">${formatCurrency(data.weavers_summary.total_unpaid_wages)}</div>
          <div class="pulse-card-sub">ಉಳಿತಾಯ ನಿಧಿ ಠೇವಣಿ: ${formatCurrency(data.weavers_summary.total_thrift_reserve)}</div>
        </div>
        <div class="pulse-card emerald-border">
          <div class="pulse-card-label" data-i18n="pulse.unclaimed_rebate">ಸರ್ಕಾರಿ ೨೦% ರಿಯಾಯಿತಿ ಕ್ಲೈಮ್ ಬಾಕಿ</div>
          <div class="pulse-card-value" style="color:var(--accent-emerald);">${formatCurrency(data.schemes_summary.unclaimed_rebate_subsidy)}</div>
          <div class="pulse-card-sub">${data.schemes_summary.rebate_sales_count} ರಿಯಾಯಿತಿ ಮಾರಾಟಗಳು ಸಲ್ಲಿಕೆಗೆ ಬಾಕಿ</div>
        </div>
      </div>

      <!-- Actionable Alerts Section -->
      ${data.actionable_alerts.length > 0 ? `
        <div class="card-inst" style="border-left:4px solid var(--primary-crimson);">
          <div class="card-inst-header">
            <div class="card-inst-title" style="color:var(--primary-crimson);">⚠️ ತುರ್ತು ಕಾರ್ಯಾಚರಣಾ ಎಚ್ಚರಿಕೆಗಳು (Actionable Alerts)</div>
          </div>
          <div class="alerts-container">
            ${data.actionable_alerts.map(a => `
              <div class="alert-banner ${a.type === 'WARNING' ? 'danger' : ''}">
                <div>
                  <div class="alert-text">${currentLanguage === 'kn' ? a.title_kn : a.title_en}</div>
                  ${a.code === 'OVERDUE_YARN_ALLOTMENTS' ? `
                    <div style="font-size:0.75rem; color:#78350f; margin-top:0.35rem;">
                      ${a.items.map(it => `• ${it.full_name_kn} (${it.village}) - ಹಂಚಿಕೆ: ${it.allotment_no} (${it.issue_date} ರಿಂದ ಬಾಕಿ)`).join('<br>')}
                    </div>
                  ` : ''}
                </div>
                <button class="btn-inst btn-inst-secondary" style="font-size:0.75rem;" onclick="navigateTo('production')">ಪರಿಶೀಲಿಸಿ</button>
              </div>
            `).join("")}
          </div>
        </div>
      ` : ''}

      <!-- Recent Operational Movement Journal -->
      <div class="card-inst">
        <div class="card-inst-header">
          <div class="card-inst-title">📜 ಇತ್ತೀಚಿನ ದಾಸ್ತಾನು ವಹಿವಾಟು ಜರ್ನಲ್ (Operational Activity)</div>
          <button class="btn-inst btn-inst-secondary" onclick="navigateTo('inventory')">ಸಂಪೂರ್ಣ ಲೆಡ್ಜರ್ ವೀಕ್ಷಿಸಿ →</button>
        </div>
        <div class="ledger-table-wrap">
          <table class="ledger-table">
            <thead>
              <tr>
                <th>ಸಮಯ</th>
                <th>ಚಲನೆಯ ವಿಧ (Movement)</th>
                <th>ಉತ್ಪನ್ನ / ನೂಲು</th>
                <th>ಶೇಖರಣಾ ಹಂತ (Storage Node)</th>
                <th>ಪ್ರಮಾಣ</th>
                <th>ವಿವರ</th>
              </tr>
            </thead>
            <tbody>
              ${data.recent_activity.map(m => `
                <tr>
                  <td>${m.created_at.slice(0, 19)}</td>
                  <td><span class="badge-state ${m.quantity_delta > 0 ? 'active' : 'wip'}">${m.movement_type}</span></td>
                  <td><strong>${currentLanguage === 'kn' ? m.item_name_kn : m.item_name_en}</strong></td>
                  <td>${currentLanguage === 'kn' ? m.warehouse_name_kn : m.warehouse_name_en}</td>
                  <td style="font-weight:700; color:${m.quantity_delta > 0 ? 'var(--accent-emerald)' : 'var(--primary-crimson)'};">
                    ${m.quantity_delta > 0 ? '+' : ''}${m.quantity_delta}
                  </td>
                  <td><small style="color:var(--text-muted);">${m.notes || ''}</small></td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        </div>
      </div>
    `;
  } catch (err) {
    container.innerHTML = `<div style="color:var(--primary-crimson); padding:2rem;">ಕಾರ್ಯಾಚರಣೆ ಕೇಂದ್ರ ಲೋಡ್ ಆಗುವಲ್ಲಿ ದೋಷ: ${err.message}</div>`;
  }
}

// -------------------------------------------------------------------
// 2. WEAVER ARTISANS ECOSYSTEM
// -------------------------------------------------------------------
async function loadWeaversSection() {
  const container = document.getElementById("sec-weavers");
  if (!container) return;

  try {
    const weavers = await api.getWeavers();
    container.innerHTML = `
      <div class="card-inst">
        <div class="card-inst-header">
          <div class="card-inst-title">🧵 ನೋಂದಾಯಿತ ಕೈಮಗ್ಗ ನೇಕಾರ ಸದಸ್ಯರು (Artisanal Profiles)</div>
          <button class="btn-inst btn-inst-primary" onclick="openModal('modal-add-weaver')">+ ಹೊಸ ನೇಕಾರರನ್ನು ನೋಂದಾಯಿಸಿ</button>
        </div>
        <div class="ledger-table-wrap">
          <table class="ledger-table">
            <thead>
              <tr>
                <th>ಸದಸ್ಯತ್ವ ಸಂಖ್ಯೆ</th>
                <th>ನೇಕಾರರ ಹೆಸರು</th>
                <th>ಗ್ರಾಮ / ತಾಲೂಕು</th>
                <th>ಮಗ್ಗದ ಮಾದರಿ</th>
                <th>ಬಳಿಯಲ್ಲಿರುವ ನೂಲು (WIP)</th>
                <th>ವೇತನ ಬಾಕಿ ಶಿಲ್ಕು</th>
                <th>ಉಳಿತಾಯ ನಿಧಿ (8% TF)</th>
                <th>ಕಾರ್ಯ</th>
              </tr>
            </thead>
            <tbody>
              ${weavers.map(w => `
                <tr>
                  <td style="font-weight:700; color:var(--primary-navy);">${w.membership_no}</td>
                  <td>
                    <div style="font-weight:700;">${w.full_name_kn}</div>
                    <small style="color:var(--text-muted);">${w.full_name_en} (Pehchan: ${w.pehchan_card_id || 'N/A'})</small>
                  </td>
                  <td>${w.village}, ${w.taluk}</td>
                  <td><span class="badge-state wip">${w.loom_type} (${w.active_looms_count} ಮಗ್ಗ)</span></td>
                  <td style="font-weight:700; color:var(--primary-gold);">${w.active_yarn_in_custody_kgs} Kgs</td>
                  <td style="font-weight:700; color:var(--accent-emerald);">${formatCurrency(w.passbook_wage_balance)}</td>
                  <td style="font-weight:700; color:var(--text-muted);">${formatCurrency(w.thrift_fund_balance)}</td>
                  <td>
                    <button class="btn-inst btn-inst-secondary" style="padding:0.25rem 0.5rem; font-size:0.75rem;" onclick="viewWeaverOperationalProfile('${w.id}')">
                      ಕಾರ್ಯಾಚರಣಾ ಪ್ರೊಫೈಲ್ →
                    </button>
                  </td>
                </tr>
              `).join("") || '<tr><td colspan="8" style="text-align:center;">ಯಾವುದೇ ನೇಕಾರರು ನೋಂದಣಿಯಾಗಿಲ್ಲ</td></tr>'}
            </tbody>
          </table>
        </div>
      </div>
    `;
  } catch (err) {
    container.innerHTML = `<div style="color:var(--primary-crimson);">ದೋಷ: ${err.message}</div>`;
  }
}

async function viewWeaverOperationalProfile(weaverId) {
  try {
    const profile = await api.getWeaverProfile(weaverId);
    const w = profile.weaver;
    const yarn = profile.yarn_in_custody;
    const allotments = profile.allotments;
    const receipts = profile.receipts;

    const modalBody = document.getElementById("profile-modal-body");
    modalBody.innerHTML = `
      <div style="background:#f8fafc; border:1px solid var(--border-card); padding:1rem; border-radius:var(--radius-sm); margin-bottom:1.25rem;">
        <div style="display:flex; justify-content:space-between; align-items:flex-start;">
          <div>
            <h3 style="color:var(--primary-navy); font-size:1.15rem;">${w.full_name_kn} (${w.full_name_en})</h3>
            <p style="color:var(--text-muted); font-size:0.8rem; margin-top:0.25rem;">
              ಸದಸ್ಯತ್ವ: <strong>${w.membership_no}</strong> | ಮಗ್ಗ: <strong>${w.loom_type} (${w.active_looms_count} ಕಾರ್ಯನಿರತ ಮಗ್ಗಗಳು)</strong> | ಗ್ರಾಮ: ${w.village}
            </p>
            <p style="color:var(--text-muted); font-size:0.8rem;">
              ಪೆಹ್ಚಾನ್ ಕಾರ್ಡ್: <strong>${w.pehchan_card_id || 'N/A'}</strong> | ಬ್ಯಾಂಕ್ ಖಾತೆ: ${w.bank_name || 'Co-op Bank'} (${w.bank_account_no || 'N/A'})
            </p>
          </div>
          <div style="text-align:right;">
            <div style="font-size:0.75rem; color:var(--text-muted);">ಮನೆಯಲ್ಲಿರುವ ಚಾಲ್ತಿ ನೂಲು (Cottage WIP)</div>
            <div style="font-size:1.4rem; font-weight:800; color:var(--primary-gold);">${yarn.total_kgs} Kgs</div>
            <small style="color:var(--text-dim);">${yarn.warp_kgs}kg Warp + ${yarn.weft_kgs}kg Weft</small>
          </div>
        </div>
        <div style="display:flex; gap:1.5rem; margin-top:1rem; border-top:1px dashed var(--border-card); padding-top:0.75rem;">
          <div>
            <div style="font-size:0.75rem; color:var(--text-muted);">ಬಾಕಿ ವೇತನ ಶಿಲ್ಕು (Unpaid Wages)</div>
            <div style="font-size:1.2rem; font-weight:800; color:var(--accent-emerald);">${formatCurrency(w.passbook_wage_balance)}</div>
          </div>
          <div>
            <div style="font-size:0.75rem; color:var(--text-muted);">ಉಳಿತಾಯ ನಿಧಿ ಠೇವಣಿ (8% Thrift Fund)</div>
            <div style="font-size:1.2rem; font-weight:800; color:var(--primary-navy);">${formatCurrency(w.thrift_fund_balance)}</div>
          </div>
        </div>
      </div>

      <h4 style="font-size:0.9rem; color:var(--primary-navy); margin-bottom:0.5rem;">ನೂಲು ಹಂಚಿಕೆ ಇತಿಹಾಸ (Loom Allotments / Hanchike)</h4>
      <table class="ledger-table" style="font-size:0.75rem; margin-bottom:1.5rem;">
        <thead>
          <tr><th>ಹಂಚಿಕೆ ಸಂಖ್ಯೆ</th><th>ಉತ್ಪನ್ನ</th><th>ನೂಲು ಪ್ರಮಾಣ</th><th>ಗುರಿ</th><th>ದಿನಾಂಕ</th><th>ಸ್ಥಿತಿ</th></tr>
        </thead>
        <tbody>
          ${allotments.map(a => `
            <tr>
              <td>${a.allotment_no}</td>
              <td>${a.product_name_kn}</td>
              <td>${a.warp_issued_kgs}kg Warp + ${a.weft_issued_kgs}kg Weft</td>
              <td>${a.target_pieces} ಸೀರೆಗಳು</td>
              <td>${a.issue_date}</td>
              <td><span class="badge-state ${a.status === 'COMPLETED' ? 'active' : 'wip'}">${a.status}</span></td>
            </tr>
          `).join("") || '<tr><td colspan="6" style="text-align:center;">ಯಾವುದೇ ಹಂಚಿಕೆ ಇಲ್ಲ</td></tr>'}
        </tbody>
      </table>

      <h4 style="font-size:0.9rem; color:var(--primary-navy); margin-bottom:0.5rem;">ಬಟ್ಟೆ ತಪಾಸಣೆ ಮತ್ತು ಜಮೆ ವೇತನ (Inspection & Wages Earned)</h4>
      <table class="ledger-table" style="font-size:0.75rem;">
        <thead>
          <tr><th>ರಶೀದಿ</th><th>ದಿನಾಂಕ</th><th>ಸ್ವೀಕೃತ</th><th>ಗುಣಮಟ್ಟ</th><th>ಉಳಿತಾಯ ನಿಧಿ ಕಡಿತ</th><th>ನಿವ್ವಳ ಜಮೆ ವೇತನ</th></tr>
        </thead>
        <tbody>
          ${receipts.map(r => `
            <tr>
              <td>${r.receipt_no}</td>
              <td>${r.inspection_date}</td>
              <td>${r.pieces_received} ಸೀರೆಗಳು</td>
              <td>1st: ${r.first_quality_count}, 2nd: ${r.second_quality_count}</td>
              <td style="color:var(--text-muted);">- ${formatCurrency(r.thrift_fund_deduction)}</td>
              <td style="font-weight:700; color:var(--accent-emerald);">${formatCurrency(r.net_wages_credited)}</td>
            </tr>
          `).join("") || '<tr><td colspan="6" style="text-align:center;">ಯಾವುದೇ ಜಮೆ ದಾಖಲಾಗಿಲ್ಲ</td></tr>'}
        </tbody>
      </table>
    `;

    openModal("modal-weaver-profile");
  } catch (err) {
    alert("ಪ್ರೊಫೈಲ್ ತೆರೆಯಲು ವಿಫಲವಾಗಿದೆ: " + err.message);
  }
}

// -------------------------------------------------------------------
// 3. COTTAGE PRODUCTION & INSPECTION
// -------------------------------------------------------------------
async function loadProductionSection() {
  const container = document.getElementById("sec-production");
  if (!container) return;

  try {
    const allotments = await api.getProductionAllotments();
    container.innerHTML = `
      <div class="card-inst">
        <div class="card-inst-header">
          <div class="card-inst-title">⚙️ ಗೃಹ ಕೈಮಗ್ಗ ಉತ್ಪಾದನಾ ಹಂಚಿಕೆ ಪುಸ್ತಕ (Hanchike Allotments)</div>
          <div style="display:flex; gap:0.5rem;">
            <button class="btn-inst btn-inst-secondary" onclick="openModal('modal-issue-allotment')">+ ನೂಲು ಹಂಚಿಕೆ (Hanchike Issue)</button>
            <button class="btn-inst btn-inst-primary" onclick="openModal('modal-inspect-receipt')">+ ನೇಯ್ದ ಬಟ್ಟೆ ತಪಾಸಣೆ & ಜಮೆ (QC Receipt)</button>
          </div>
        </div>
        <div class="ledger-table-wrap">
          <table class="ledger-table">
            <thead>
              <tr>
                <th>ಹಂಚಿಕೆ ಸಂಖ್ಯೆ</th>
                <th>ನೇಕಾರ ಸದಸ್ಯರು</th>
                <th>ಉತ್ಪನ್ನ ವಿವರ</th>
                <th>ಹಂಚಿದ ನೂಲು</th>
                <th>ಗುರಿ</th>
                <th>ಮಗ್ಗದ ಕೂಲಿ</th>
                <th>ಹಂಚಿದ ದಿನಾಂಕ</th>
                <th>ನಿಗದಿತ ವಾಪಸಾತಿ</th>
                <th>ಸ್ಥಿತಿ</th>
              </tr>
            </thead>
            <tbody>
              ${allotments.map(a => `
                <tr>
                  <td style="font-weight:700; color:var(--primary-navy);">${a.allotment_no}</td>
                  <td><strong>${a.weaver_name_kn}</strong><br><small style="color:var(--text-muted);">${a.membership_no} (${a.village})</small></td>
                  <td>${a.product_name_kn}<br><small style="color:var(--text-dim);">${a.reed_pick_specs || a.sku}</small></td>
                  <td>${a.warp_issued_kgs}kg + ${a.weft_issued_kgs}kg</td>
                  <td><strong>${a.target_pieces}</strong> ಸೀರೆಗಳು</td>
                  <td>${formatCurrency(a.agreed_piece_wage)}/ಸೀರೆಗೆ</td>
                  <td>${a.issue_date}</td>
                  <td><span style="color:${a.status === 'WITH_WEAVER' ? 'var(--accent-amber)' : 'inherit'};">${a.expected_return_date}</span></td>
                  <td><span class="badge-state ${a.status === 'COMPLETED' ? 'active' : 'wip'}">${a.status}</span></td>
                </tr>
              `).join("") || '<tr><td colspan="9" style="text-align:center;">ಯಾವುದೇ ಹಂಚಿಕೆ ದಾಖಲಾಗಿಲ್ಲ</td></tr>'}
            </tbody>
          </table>
        </div>
      </div>
    `;
  } catch (err) {
    container.innerHTML = `<div style="color:var(--primary-crimson);">ದೋಷ: ${err.message}</div>`;
  }
}

// -------------------------------------------------------------------
// 4. MULTI-STATE INVENTORY
// -------------------------------------------------------------------
// -------------------------------------------------------------------
// 4. MULTI-STATE INVENTORY & RAW MATERIAL PROCUREMENT
// -------------------------------------------------------------------
async function loadInventorySection() {
  const container = document.getElementById("sec-inventory");
  if (!container) return;

  try {
    const [status, journal, purchases] = await Promise.all([
      api.getInventoryStatus(),
      api.getInventoryJournal(30),
      api.getPurchases().catch(() => [])
    ]);

    const totalYarnKgs = (status.raw_yarn_godown || []).reduce((acc, y) => acc + (parseFloat(y.stock_kgs) || 0), 0);
    const totalYarnVal = (status.raw_yarn_godown || []).reduce((acc, y) => acc + ((parseFloat(y.stock_kgs) || 0) * (parseFloat(y.unit_cost_per_kg) || 0)), 0);
    const totalShowroomPcs = (status.showroom_stock || []).reduce((acc, s) => acc + (parseInt(s.available_pieces) || 0), 0);
    const totalPurchasesCount = (purchases || []).length;

    container.innerHTML = `
      <!-- Top Action Toolbar -->
      <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:1rem; margin-bottom:1.25rem; background:#ffffff; padding:1rem 1.25rem; border-radius:8px; border:1px solid #e2e8f0; box-shadow:0 1px 3px rgba(0,0,0,0.05);">
        <div>
          <h2 style="margin:0; font-size:1.15rem; color:var(--primary-navy); font-weight:700;">
            🧶 ವಸ್ತು ಮತ್ತು ದಾಸ್ತಾನು ನಿರ್ವಹಣೆ (Multi-State Handloom Inventory)
          </h2>
          <div style="font-size:0.8rem; color:var(--text-muted); margin-top:0.25rem;">
            ಕಚ್ಚಾ ನೂಲು ಖರೀದಿ, ಗೋದಾಮು ದಾಸ್ತಾನು, ನೇಕಾರರ ಚಾಲ್ತಿ (WIP) ಮತ್ತು ಮಳಿಗೆಯ ಸಿದ್ಧ ಸರಕುಗಳ ಸಂಪೂರ್ಣ ನಿರ್ವಹಣೆ
          </div>
        </div>
        <div style="display:flex; gap:0.5rem; flex-wrap:wrap;">
          <button class="btn-inst btn-inst-primary" onclick="openAddPurchaseModal()" style="font-weight:700; box-shadow:0 2px 4px rgba(220,38,38,0.2);">
            + ಹೊಸ ನೂಲು ಖರೀದಿ / ಇನ್ವಾಯ್ಸ್ (Add Yarn Purchase)
          </button>
          <button class="btn-inst btn-inst-secondary" onclick="openAddYarnLotModal()">
            + ಹೊಸ ನೂಲು ಲಾಟ್ (Add Lot)
          </button>
          <button class="btn-inst btn-inst-secondary" onclick="openAddSupplierModal()">
            🏢 ಸರಬರಾಜುದಾರರ ನೋಂದಣಿ (Add Supplier)
          </button>
        </div>
      </div>

      <!-- Quick Metrics Ribbon -->
      <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(200px, 1fr)); gap:1rem; margin-bottom:1.5rem;">
        <div style="background:#ffffff; border-left:4px solid var(--accent-emerald); border-radius:6px; padding:0.85rem 1rem; border-top:1px solid #e2e8f0; border-right:1px solid #e2e8f0; border-bottom:1px solid #e2e8f0;">
          <div style="font-size:0.75rem; color:#64748b; font-weight:600;">ಒಟ್ಟು ನೂಲು ದಾಸ್ತಾನು (Yarn Stock)</div>
          <div style="font-size:1.25rem; font-weight:800; color:var(--primary-navy); margin-top:0.25rem;">${totalYarnKgs.toFixed(2)} <span style="font-size:0.85rem; font-weight:500;">Kgs</span></div>
        </div>
        <div style="background:#ffffff; border-left:4px solid var(--primary-navy); border-radius:6px; padding:0.85rem 1rem; border-top:1px solid #e2e8f0; border-right:1px solid #e2e8f0; border-bottom:1px solid #e2e8f0;">
          <div style="font-size:0.75rem; color:#64748b; font-weight:600;">ನೂಲು ದಾಸ್ತಾನು ಮೌಲ್ಯ (Valuation)</div>
          <div style="font-size:1.25rem; font-weight:800; color:var(--accent-emerald); margin-top:0.25rem;">${formatCurrency(totalYarnVal)}</div>
        </div>
        <div style="background:#ffffff; border-left:4px solid var(--primary-crimson); border-radius:6px; padding:0.85rem 1rem; border-top:1px solid #e2e8f0; border-right:1px solid #e2e8f0; border-bottom:1px solid #e2e8f0;">
          <div style="font-size:0.75rem; color:#64748b; font-weight:600;">ಸಿದ್ಧ ಸರಕುಗಳು (Showroom Goods)</div>
          <div style="font-size:1.25rem; font-weight:800; color:var(--primary-navy); margin-top:0.25rem;">${totalShowroomPcs} <span style="font-size:0.85rem; font-weight:500;">Pcs</span></div>
        </div>
        <div style="background:#ffffff; border-left:4px solid #f59e0b; border-radius:6px; padding:0.85rem 1rem; border-top:1px solid #e2e8f0; border-right:1px solid #e2e8f0; border-bottom:1px solid #e2e8f0;">
          <div style="font-size:0.75rem; color:#64748b; font-weight:600;">ದಾಖಲಾದ ಖರೀದಿ ಬಿಲ್‌ಗಳು (Inward Invoices)</div>
          <div style="font-size:1.25rem; font-weight:800; color:var(--primary-navy); margin-top:0.25rem;">${totalPurchasesCount}</div>
        </div>
      </div>

      <!-- Main Storage Split -->
      <div style="display:grid; grid-template-columns:1fr 1fr; gap:1.25rem; margin-bottom:1.5rem;">
        <!-- Central Yarn Godown -->
        <div class="card-inst">
          <div class="card-inst-header" style="display:flex; justify-content:space-between; align-items:center;">
            <div class="card-inst-title">🧶 ಕೇಂದ್ರ ನೂಲು ಗೋದಾಮು (Raw Yarn Godown)</div>
            <button class="btn-inst btn-inst-secondary" style="font-size:0.75rem; padding:0.25rem 0.5rem;" onclick="openAddPurchaseModal()">+ ಖರೀದಿ ಜಮಾ</button>
          </div>
          <table class="ledger-table" style="font-size:0.8rem;">
            <thead><tr><th>ಲಾಟ್ ಸಂಖ್ಯೆ</th><th>ಕೌಂಟ್ / ನೂಲು</th><th>ಗಿರಣಿ</th><th>ದಾಸ್ತಾನು (Kgs)</th><th>ದರ/Kg</th><th>ಕ್ರಮ</th></tr></thead>
            <tbody>
              ${status.raw_yarn_godown.map(y => `
                <tr>
                  <td><strong>${y.lot_number}</strong></td>
                  <td>${y.count_spec} <br/><small style="color:#64748b;">(${y.yarn_type})</small></td>
                  <td>${y.mill_name}</td>
                  <td style="font-weight:700; color:${parseFloat(y.stock_kgs) > 0 ? 'var(--accent-emerald)' : 'var(--primary-crimson)'};">
                    ${y.stock_kgs} Kgs
                  </td>
                  <td>${formatCurrency(y.unit_cost_per_kg)}</td>
                  <td>
                    <button class="btn-inst btn-inst-secondary" style="font-size:0.7rem; padding:0.15rem 0.4rem;" 
                            onclick="openAddPurchaseModal('${y.lot_number}', '${y.count_spec}', '${y.mill_name}', ${y.unit_cost_per_kg}, '${y.yarn_type}')">
                      + ಖರೀದಿ
                    </button>
                  </td>
                </tr>
              `).join("") || '<tr><td colspan="6" style="text-align:center; padding:1.5rem;">ಗೋದಾಮಿನಲ್ಲಿ ನೂಲು ಇಲ್ಲ. ಮೇಲಿನ "+ ಹೊಸ ನೂಲು ಖರೀದಿ" ಕ್ಲಿಕ್ ಮಾಡಿ ಸೇರಿಸಿ.</td></tr>'}
            </tbody>
          </table>
        </div>

        <!-- Finished Goods in Showrooms -->
        <div class="card-inst">
          <div class="card-inst-header">
            <div class="card-inst-title">🏬 ಮಳಿಗೆಯ ಸಿದ್ಧ ದಾಸ್ತಾನು (Showroom Stock)</div>
          </div>
          <table class="ledger-table" style="font-size:0.8rem;">
            <thead><tr><th>SKU</th><th>ಉತ್ಪನ್ನ</th><th>ಮಳಿಗೆ</th><th>ಲಭ್ಯ ದಾಸ್ತಾನು</th><th>ಚಿಲ್ಲರೆ ಬೆಲೆ</th></tr></thead>
            <tbody>
              ${status.showroom_stock.map(s => `
                <tr>
                  <td><strong>${s.sku}</strong></td>
                  <td>${s.name_kn}</td>
                  <td>${s.showroom_name_kn}</td>
                  <td style="font-weight:700; color:${s.available_pieces < 5 ? 'var(--primary-crimson)' : 'var(--accent-emerald)'};">
                    ${s.available_pieces} ${s.uom}
                  </td>
                  <td>${formatCurrency(s.retail_rate)}</td>
                </tr>
              `).join("") || '<tr><td colspan="5" style="text-align:center; padding:1.5rem;">ಸಿದ್ಧ ದಾಸ್ತಾನು ಖಾಲಿಯಾಗಿದೆ</td></tr>'}
            </tbody>
          </table>
        </div>
      </div>

      <!-- Raw Material Inward Purchase Invoices Ledger -->
      <div class="card-inst" style="margin-bottom:1.5rem;">
        <div class="card-inst-header" style="display:flex; justify-content:space-between; align-items:center;">
          <div class="card-inst-title">📋 ಕಚ್ಚಾ ವಸ್ತು ಖರೀದಿ ಬಿಲ್‌ಗಳ ಲೆಡ್ಜರ್ (Raw Material Purchase Invoices)</div>
          <button class="btn-inst btn-inst-primary" style="font-size:0.8rem;" onclick="openAddPurchaseModal()">+ ಹೊಸ ಖರೀದಿ ಇನ್ವಾಯ್ಸ್ ದಾಖಲಿಸಿ</button>
        </div>
        <div class="ledger-table-wrap">
          <table class="ledger-table" style="font-size:0.8rem;">
            <thead>
              <tr>
                <th>ಸಂಘದ ಜಮಾ ನಂ (Entry No)</th>
                <th>ಸರಬರಾಜುದಾರರ ಬಿಲ್ ನಂ</th>
                <th>ದಿನಾಂಕ</th>
                <th>ಸರಬರಾಜುದಾರ / ಗಿರಣಿ</th>
                <th>ಖರೀದಿಸಿದ ನೂಲು ವಿವರಗಳು</th>
                <th>ಒಟ್ಟು ಮೊತ್ತ (₹)</th>
                <th>ಸ್ಥಿತಿ (Status)</th>
                <th>ಕ್ರಮ</th>
              </tr>
            </thead>
            <tbody>
              ${purchases.map(p => `
                <tr>
                  <td><strong>${p.society_entry_no}</strong></td>
                  <td>${p.invoice_no}</td>
                  <td>${p.invoice_date}</td>
                  <td>${p.supplier_name}</td>
                  <td>
                    ${(p.items && p.items.length) ? p.items.map(it => `
                      <span style="display:inline-block; background:#f1f5f9; padding:2px 6px; border-radius:4px; margin:2px; font-size:0.75rem;">
                        <strong>${it.lot_number || 'Yarn'}</strong>: ${it.quantity_kgs} Kgs @ ${formatCurrency(it.rate_per_unit)}
                      </span>
                    `).join("") : '<span style="color:#94a3b8;">ವಿವರವಿಲ್ಲ</span>'}
                  </td>
                  <td style="font-weight:700; color:var(--primary-navy);">${formatCurrency(p.total_amount)}</td>
                  <td>
                    <span class="badge-state ${p.status === 'POSTED' ? 'active' : 'wip'}">
                      ${p.status === 'POSTED' ? 'ದಾಸ್ತಾನು ಜಮಾ ಆಗಿದೆ ✓' : 'ಕರಡು (DRAFT)'}
                    </span>
                  </td>
                  <td>
                    ${p.status === 'DRAFT' ? `
                      <button class="btn-inst btn-inst-primary" style="font-size:0.7rem; padding:0.2rem 0.5rem;" onclick="postExistingPurchase('${p.id}')">
                        ದಾಸ್ತಾನು ಜಮಾ ಮಾಡಿ
                      </button>
                    ` : `
                      <span style="font-size:0.75rem; color:#10b981; font-weight:600;">ಪೂರ್ಣಗೊಂಡಿದೆ</span>
                    `}
                  </td>
                </tr>
              `).join("") || '<tr><td colspan="8" style="text-align:center; padding:1.5rem;">ಯಾವುದೇ ಖರೀದಿ ಇನ್ವಾಯ್ಸ್ ದಾಖಲಾಗಿಲ್ಲ. ಮೇಲಿನ "+ ಹೊಸ ನೂಲು ಖರೀದಿ / ಇನ್ವಾಯ್ಸ್" ಕ್ಲಿಕ್ ಮಾಡಿ.</td></tr>'}
            </tbody>
          </table>
        </div>
      </div>

      <!-- Signed Immutable Movement Journal -->
      <div class="card-inst">
        <div class="card-inst-header">
          <div class="card-inst-title">📖 ಅಪರಿವರ್ತನೀಯ ದಾಸ್ತಾನು ವಹಿವಾಟು ಜರ್ನಲ್ (Movement Journal)</div>
        </div>
        <div class="ledger-table-wrap">
          <table class="ledger-table">
            <thead>
              <tr><th>ಸಮಯ</th><th>ಸ್ಥಳ / ಹಂತ</th><th>ಚಲನೆಯ ವಿಧ</th><th>ಉತ್ಪನ್ನ / ನೂಲು</th><th>ಬದಲಾವಣೆ</th><th>ಘಟಕ ಮೌಲ್ಯ</th><th>ಉಲ್ಲೇಖ</th></tr>
            </thead>
            <tbody>
              ${journal.map(j => `
                <tr>
                  <td>${j.created_at.slice(0, 19)}</td>
                  <td>${j.warehouse_name_kn}</td>
                  <td><span class="badge-state ${j.quantity_delta > 0 ? 'active' : 'wip'}">${j.movement_type}</span></td>
                  <td>${j.item_name_kn} (${j.item_code})</td>
                  <td style="font-weight:700; color:${j.quantity_delta > 0 ? 'var(--accent-emerald)' : 'var(--primary-crimson)'};">
                    ${j.quantity_delta > 0 ? '+' : ''}${j.quantity_delta} ${j.uom}
                  </td>
                  <td>${formatCurrency(j.unit_cost)}</td>
                  <td><small style="color:var(--text-muted);">${j.notes || j.reference_type}</small></td>
                </tr>
              `).join("") || '<tr><td colspan="7" style="text-align:center; padding:1rem;">ದಾಸ್ತಾನು ಜರ್ನಲ್ ವಹಿವಾಟುಗಳು ಲಭ್ಯವಿಲ್ಲ</td></tr>'}
            </tbody>
          </table>
        </div>
      </div>
    `;
  } catch (err) {
    container.innerHTML = `
      <div style="background:#fef2f2; border:1px solid #fecaca; border-radius:8px; padding:1.5rem; text-align:center;">
        <div style="font-size:1.1rem; font-weight:700; color:#b91c1c; margin-bottom:0.5rem;">ದಾಸ್ತಾನು ವಿವರಗಳನ್ನು ಲೋಡ್ ಮಾಡಲು ಸಾಧ್ಯವಾಗಿಲ್ಲ</div>
        <div style="color:#7f1d1d; margin-bottom:1rem;">${err.message}</div>
        <button class="btn-inst btn-inst-primary" onclick="window.location.reload()">ಪುಟವನ್ನು ಮರುಲೋಡ್ ಮಾಡಿ (Reload Page)</button>
      </div>
    `;
  }
}

// Purchase & Yarn Modal Handlers
async function openAddPurchaseModal(prefillLotNo = "", prefillCount = "", prefillMill = "", prefillRate = 0, prefillType = "COTTON") {
  try {
    const whs = await api.getTenantWarehouses().catch(() => []);
    const whSelect = document.getElementById("pi-wh");
    if (whSelect) {
      whSelect.innerHTML = whs.map(w => `
        <option value="${w.id}" ${w.storage_type === 'RAW_YARN_GODOWN' ? 'selected' : ''}>
          ${w.name_kn} (${w.name_en})
        </option>
      `).join("") || '<option value="">ಕೇಂದ್ರ ನೂಲು ಉಗ್ರಾಣ (Central Yarn Godown)</option>';
    }

    const suppliers = await api.getSuppliers().catch(() => []);
    const supSelect = document.getElementById("pi-supplier");
    if (supSelect) {
      if (suppliers.length === 0) {
        const defSup = await api.createSupplier({
          name: "ಕರ್ನಾಟಕ ಅಪೆಕ್ಸ್ ನೂಲು ಡಿಪೋ (NHDC / State Apex Yarn Depot)",
          supplier_type: "YARN_MILL",
          phone: "9845011223"
        }).catch(() => null);
        if (defSup) suppliers.push(defSup);
      }
      supSelect.innerHTML = suppliers.map(s => `
        <option value="${s.id}">${s.name} ${s.gstin ? `(${s.gstin})` : ''}</option>
      `).join("");
    }

    const today = new Date().toISOString().split("T")[0];
    document.getElementById("pi-date").value = today;
    document.getElementById("pi-entry-no").value = `INW-${new Date().getFullYear()}-${Math.floor(1000 + Math.random() * 9000)}`;
    document.getElementById("pi-inv-no").value = prefillLotNo ? `INV-${prefillLotNo}` : `INV-${Math.floor(10000 + Math.random() * 90000)}`;

    if (prefillLotNo) {
      document.getElementById("pi-lot-no").value = prefillLotNo;
      document.getElementById("pi-count-spec").value = prefillCount;
      document.getElementById("pi-mill").value = prefillMill;
      document.getElementById("pi-rate").value = prefillRate || "";
      document.getElementById("pi-yarn-type").value = prefillType || "COTTON";
    } else {
      document.getElementById("pi-lot-no").value = `LOT-${new Date().getFullYear()}-C${Math.floor(10 + Math.random() * 90)}`;
      document.getElementById("pi-count-spec").value = "2/60s Combed Cotton";
      document.getElementById("pi-mill").value = "Gokak Mills Ltd";
      document.getElementById("pi-rate").value = "380.00";
      document.getElementById("pi-yarn-type").value = "COTTON";
    }
    document.getElementById("pi-qty").value = "50.00";
    document.getElementById("pi-tax-rate").value = "5.0";

    recalcPurchaseTotals();
    openModal("modal-add-purchase");
  } catch (err) {
    alert("ಖರೀದಿ ಫಾರ್ಮ್ ತೆರೆಯಲು ಸಾಧ್ಯವಾಗಿಲ್ಲ: " + err.message);
  }
}

function recalcPurchaseTotals() {
  const qty = parseFloat(document.getElementById("pi-qty")?.value) || 0;
  const rate = parseFloat(document.getElementById("pi-rate")?.value) || 0;
  const taxRate = parseFloat(document.getElementById("pi-tax-rate")?.value) || 5.0;

  const subtotal = qty * rate;
  const tax = subtotal * (taxRate / 100.0);
  const total = subtotal + tax;

  const dispSub = document.getElementById("pi-disp-sub");
  const dispTax = document.getElementById("pi-disp-tax");
  const dispTotal = document.getElementById("pi-disp-total");

  if (dispSub) dispSub.textContent = formatCurrency(subtotal);
  if (dispTax) dispTax.textContent = formatCurrency(tax);
  if (dispTotal) dispTotal.textContent = formatCurrency(total);
}

async function handlePurchaseSubmit(e) {
  e.preventDefault();
  const btn = document.getElementById("btn-save-purchase");
  if (btn) btn.disabled = true;

  try {
    const supplierId = document.getElementById("pi-supplier").value;
    const invoiceNo = document.getElementById("pi-inv-no").value;
    const entryNo = document.getElementById("pi-entry-no").value;
    const invoiceDate = document.getElementById("pi-date").value;
    const warehouseId = document.getElementById("pi-wh").value || null;

    const lotNo = document.getElementById("pi-lot-no").value;
    const yarnType = document.getElementById("pi-yarn-type").value;
    const countSpec = document.getElementById("pi-count-spec").value;
    const millName = document.getElementById("pi-mill").value;
    const shadeCode = document.getElementById("pi-shade").value;
    const qty = parseFloat(document.getElementById("pi-qty").value);
    const rate = parseFloat(document.getElementById("pi-rate").value);
    const taxRate = parseFloat(document.getElementById("pi-tax-rate").value) || 5.0;

    const payload = {
      supplier_id: supplierId,
      invoice_no: invoiceNo,
      society_entry_no: entryNo,
      invoice_date: invoiceDate,
      receiving_warehouse_id: warehouseId,
      auto_post: true,
      items: [
        {
          lot_number: lotNo,
          yarn_type: yarnType,
          count_spec: countSpec,
          mill_name: millName,
          shade_code: shadeCode,
          quantity: qty,
          unit_cost: rate,
          tax_rate: taxRate
        }
      ]
    };

    const res = await api.createPurchase(payload);
    closeAllModals();
    await loadInventorySection();
    alert(`ಖರೀದಿ ಇನ್ವಾಯ್ಸ್ ಯಶಸ್ವಿಯಾಗಿ ದಾಖಲಾಗಿದೆ!\nಜಮಾ ಸಂಖ್ಯೆ: ${res.society_entry_no || entryNo}\nದಾಸ್ತಾನು ಕೇಂದ್ರ ನೂಲು ಗೋದಾಮಿಗೆ ಸೇರ್ಪಡೆಗೊಂಡಿದೆ.`);
  } catch (err) {
    alert("ಖರೀದಿ ದಾಖಲಿಸಲು ವಿಫಲವಾಗಿದೆ: " + err.message);
  } finally {
    if (btn) btn.disabled = false;
  }
}

function openAddYarnLotModal() {
  document.getElementById("nyl-lot-no").value = `LOT-${new Date().getFullYear()}-${Math.floor(100 + Math.random() * 900)}`;
  openModal("modal-add-yarn-lot");
}

async function handleYarnLotSubmit(e) {
  e.preventDefault();
  try {
    const payload = {
      lot_number: document.getElementById("nyl-lot-no").value,
      yarn_type: document.getElementById("nyl-type").value,
      count_spec: document.getElementById("nyl-count").value,
      mill_name: document.getElementById("nyl-mill").value,
      shade_code: document.getElementById("nyl-shade").value,
      unit_cost_per_kg: parseFloat(document.getElementById("nyl-rate").value) || 0
    };
    await api.createYarnLot(payload);
    closeAllModals();
    await loadInventorySection();
    alert("ನೂಲು ಲಾಟ್ ಯಶಸ್ವಿಯಾಗಿ ನೋಂದಾಯಿಸಲಾಗಿದೆ!");
  } catch (err) {
    alert("ನೂಲು ಲಾಟ್ ನೋಂದಣಿ ವಿಫಲವಾಗಿದೆ: " + err.message);
  }
}

function openAddSupplierModal() {
  openModal("modal-add-supplier");
}

async function handleSupplierSubmit(e) {
  e.preventDefault();
  try {
    const payload = {
      name: document.getElementById("ns-name").value,
      supplier_type: document.getElementById("ns-type").value,
      contact_person: document.getElementById("ns-contact").value,
      phone: document.getElementById("ns-phone").value,
      gstin: document.getElementById("ns-gstin").value,
      address: document.getElementById("ns-address").value
    };
    const res = await api.createSupplier(payload);
    closeAllModals();
    const supSelect = document.getElementById("pi-supplier");
    if (supSelect) {
      const opt = document.createElement("option");
      opt.value = res.id;
      opt.textContent = res.name;
      opt.selected = true;
      supSelect.appendChild(opt);
    }
    alert("ಸರಬರಾಜುದಾರರನ್ನು ಯಶಸ್ವಿಯಾಗಿ ಉಳಿಸಲಾಗಿದೆ!");
  } catch (err) {
    alert("ಸರಬರಾಜುದಾರರ ನೋಂದಣಿ ವಿಫಲವಾಗಿದೆ: " + err.message);
  }
}

async function postExistingPurchase(invoiceId) {
  try {
    await api.postPurchase(invoiceId);
    await loadInventorySection();
    alert("ದಾಸ್ತಾನು ಯಶಸ್ವಿಯಾಗಿ ಗೋದಾಮಿಗೆ ಜಮಾ ಆಗಿದೆ!");
  } catch (err) {
    alert("ದಾಸ್ತಾನು ಜಮಾ ವಿಫಲವಾಗಿದೆ: " + err.message);
  }
}

// -------------------------------------------------------------------
// 5. SALES & SHOWROOM POS
// -------------------------------------------------------------------
async function loadSalesSection() {
  const container = document.getElementById("sec-sales");
  if (!container) return;

  try {
    const inv = await api.getInventoryStatus();
    state.cachedProducts = inv.showroom_stock;

    container.innerHTML = `
      <div style="display:grid; grid-template-columns:1fr 400px; gap:1.25rem;">
        <!-- Left Product Selection -->
        <div class="card-inst">
          <div class="card-inst-header">
            <div class="card-inst-title">🏷️ ಮಳಿಗೆ ಮಾರಾಟ ಕೌಂಟರ್ (Showroom Billing)</div>
            <input type="text" id="sales-search-box" class="form-input" placeholder="ಸೀರೆ ಅಥವಾ SKU ಹುಡುಕಿ..." style="width:260px;" oninput="filterSalesProducts(this.value)" />
          </div>
          <div style="display:grid; grid-template-columns:repeat(auto-fill, minmax(220px, 1fr)); gap:0.75rem;" id="sales-products-grid">
            ${renderSalesProductCards(state.cachedProducts)}
          </div>
        </div>

        <!-- Right Cart & Rebate Engine -->
        <div class="card-inst" style="background:#fdfefe; border:1px solid #cbd5e1; display:flex; flex-direction:column;">
          <div class="card-inst-header" style="background:#f1f5f9; margin:-1.25rem -1.25rem 1rem -1.25rem; padding:0.85rem 1.25rem;">
            <div class="card-inst-title" style="font-size:0.95rem;">🛒 ಗ್ರಾಹಕರ ಬಿಲ್ಲಿಂಗ್ ಪಟ್ಟಿ</div>
          </div>

          <div style="margin-bottom:0.75rem;">
            <input type="text" id="sale-cust-name" class="form-input" placeholder="ಗ್ರಾಹಕರ ಹೆಸರು (Customer Name)" style="width:100%; margin-bottom:0.4rem;" />
            <input type="text" id="sale-cust-phone" class="form-input" placeholder="ಮೊಬೈಲ್ ಸಂಖ್ಯೆ (Phone)" style="width:100%;" />
          </div>

          <!-- Cart Lines -->
          <div id="sales-cart-lines" style="flex:1; max-height:260px; overflow-y:auto; margin-bottom:1rem; border:1px solid var(--border-card); border-radius:var(--radius-sm); padding:0.5rem; background:#fff;">
            ${renderCartLinesHtml()}
          </div>

          <!-- 20% Directorate Rebate Switch -->
          <div style="background:#fef3c7; border:1px solid #f59e0b; padding:0.6rem 0.75rem; border-radius:var(--radius-sm); margin-bottom:0.75rem;">
            <label style="display:flex; align-items:center; justify-content:space-between; font-size:0.8rem; font-weight:700; color:#92400e; cursor:pointer;">
              <span>🏛️ ಕರ್ನಾಟಕ ಸರ್ಕಾರ ೨೦% ಹಬ್ಬದ ರಿಯಾಯಿತಿ</span>
              <input type="checkbox" id="rebate-toggle-chk" ${state.applyRebate ? 'checked' : ''} onchange="toggleRebateSwitch(this.checked)" style="width:18px; height:18px;" />
            </label>
            <small style="font-size:0.7rem; color:#78350f;">ಕೈಮಗ್ಗ ನಿರ್ದೇಶನಾಲಯದಿಂದ ಸಂಘಕ್ಕೆ ಮರುಪಾವತಿ ಲಭ್ಯ</small>
          </div>

          <!-- Totals Calculation -->
          <div style="font-size:0.85rem; border-top:1px dashed var(--border-strong); padding-top:0.6rem; display:flex; flex-direction:column; gap:0.35rem;">
            <div style="display:flex; justify-content:space-between; color:var(--text-muted);">
              <span>ಒಟ್ಟು ಬೆಲೆ (Gross):</span>
              <span id="lbl-gross-val">${formatCurrency(calculateGrossCart())}</span>
            </div>
            <div style="display:flex; justify-content:space-between; color:var(--accent-emerald); font-weight:700;">
              <span>ಸರ್ಕಾರಿ ೨೦% ರಿಯಾಯಿತಿ:</span>
              <span id="lbl-rebate-val">- ${formatCurrency(calculateRebateCart())}</span>
            </div>
            <div style="display:flex; justify-content:space-between; color:var(--text-muted);">
              <span>ಜಿಎಸ್‍ಟಿ (GST 5%):</span>
              <span id="lbl-tax-val">${formatCurrency(calculateTaxCart())}</span>
            </div>
            <div style="display:flex; justify-content:space-between; font-size:1.15rem; font-weight:800; color:var(--primary-navy); border-top:1px solid var(--border-strong); padding-top:0.4rem;">
              <span>ಗ್ರಾಹಕರು ಪಾವತಿಸಬೇಕಾದ ಮೊತ್ತ:</span>
              <span id="lbl-net-val">${formatCurrency(calculateNetPayableCart())}</span>
            </div>
          </div>

          <button class="btn-inst btn-inst-primary" style="width:100%; justify-content:center; padding:0.75rem; margin-top:1rem; font-size:0.95rem;" onclick="submitSaleTransaction()">
            ಬಿಲ್ ಪೂರ್ಣಗೊಳಿಸಿ ಮತ್ತು ಮುದ್ರಿಸಿ ✓
          </button>
        </div>
      </div>
    `;
  } catch (err) {
    container.innerHTML = `<div style="color:var(--primary-crimson);">ದೋಷ: ${err.message}</div>`;
  }
}

function renderSalesProductCards(products) {
  return products.map(p => `
    <div style="border:1px solid var(--border-card); border-radius:var(--radius-sm); padding:0.75rem; background:#fff; cursor:pointer;" onclick="addItemToCart('${p.sku}')">
      <div style="font-size:0.7rem; color:var(--primary-gold); font-weight:700;">${p.sku}</div>
      <div style="font-size:0.875rem; font-weight:700; color:var(--primary-navy); margin:0.2rem 0;">${p.name_kn}</div>
      <div style="display:flex; justify-content:space-between; align-items:center; margin-top:0.4rem; border-top:1px solid #f1f5f9; padding-top:0.35rem;">
        <span style="font-weight:700; color:var(--primary-crimson);">${formatCurrency(p.retail_rate)}</span>
        <span class="badge-state ${p.available_pieces < 5 ? 'warning' : 'active'}">${p.available_pieces} ಲಭ್ಯ</span>
      </div>
    </div>
  `).join("") || '<div style="grid-column:1/-1; text-align:center; padding:1.5rem; color:var(--text-muted);">ಯಾವುದೇ ಉತ್ಪನ್ನ ಲಭ್ಯವಿಲ್ಲ</div>';
}

function addItemToCart(sku) {
  const prod = state.cachedProducts.find(p => p.sku === sku);
  if (!prod) return;
  if (prod.available_pieces <= 0) {
    alert("ಈ ಉತ್ಪನ್ನದ ದಾಸ್ತಾನು ಖಾಲಿಯಾಗಿದೆ!");
    return;
  }
  const existing = state.cart.find(c => c.sku === sku);
  if (existing) {
    if (existing.qty + 1 > prod.available_pieces) {
      alert(`ಗರಿಷ್ಠ ಲಭ್ಯವಿರುವ ದಾಸ್ತಾನು: ${prod.available_pieces}`);
      return;
    }
    existing.qty += 1;
  } else {
    state.cart.push({
      product_id: prod.product_id || prod.sku,
      sku: prod.sku,
      name_kn: prod.name_kn,
      rate: prod.retail_rate,
      qty: 1,
      max_avail: prod.available_pieces
    });
  }
  refreshCartUI();
}

function refreshCartUI() {
  const box = document.getElementById("sales-cart-lines");
  if (box) box.innerHTML = renderCartLinesHtml();
  const g = calculateGrossCart();
  const r = calculateRebateCart();
  const t = calculateTaxCart();
  const n = calculateNetPayableCart();
  if (document.getElementById("lbl-gross-val")) document.getElementById("lbl-gross-val").innerText = formatCurrency(g);
  if (document.getElementById("lbl-rebate-val")) document.getElementById("lbl-rebate-val").innerText = `- ${formatCurrency(r)}`;
  if (document.getElementById("lbl-tax-val")) document.getElementById("lbl-tax-val").innerText = formatCurrency(t);
  if (document.getElementById("lbl-net-val")) document.getElementById("lbl-net-val").innerText = formatCurrency(n);
}

function renderCartLinesHtml() {
  if (state.cart.length === 0) {
    return `<div style="text-align:center; color:var(--text-dim); padding:2rem 0; font-size:0.8rem;">ಬಿಲ್ಲಿಂಗ್ ಪಟ್ಟಿ ಖಾಲಿಯಾಗಿದೆ</div>`;
  }
  return state.cart.map((c, idx) => `
    <div style="display:flex; justify-content:space-between; align-items:center; padding:0.35rem 0; border-bottom:1px dashed #e2e8f0; font-size:0.8rem;">
      <div style="flex:1;">
        <strong>${c.name_kn}</strong><br>
        <small style="color:var(--text-muted);">${formatCurrency(c.rate)} × ${c.qty}</small>
      </div>
      <div style="display:flex; align-items:center; gap:0.3rem;">
        <button style="width:20px; height:20px; cursor:pointer;" onclick="changeCartQty(${idx}, -1)">−</button>
        <span>${c.qty}</span>
        <button style="width:20px; height:20px; cursor:pointer;" onclick="changeCartQty(${idx}, 1)">+</button>
      </div>
      <div style="font-weight:700; width:70px; text-align:right;">${formatCurrency(c.qty * c.rate)}</div>
    </div>
  `).join("");
}

function changeCartQty(idx, delta) {
  const item = state.cart[idx];
  if (!item) return;
  const newQ = item.qty + delta;
  if (newQ <= 0) state.cart.splice(idx, 1);
  else if (newQ > item.max_avail) alert("ದಾಸ್ತಾನು ಮಿತಿಯನ್ನು ಮೀರಿದೆ");
  else item.qty = newQ;
  refreshCartUI();
}

function calculateGrossCart() {
  return state.cart.reduce((acc, c) => acc + (c.qty * c.rate), 0);
}
function calculateRebateCart() {
  if (!state.applyRebate) return 0;
  return Math.round(calculateGrossCart() * 0.20 * 100) / 100;
}
function calculateTaxCart() {
  const taxable = calculateGrossCart() - calculateRebateCart();
  return Math.round(taxable * 0.05 * 100) / 100;
}
function calculateNetPayableCart() {
  return Math.round(calculateGrossCart() - calculateRebateCart() + calculateTaxCart());
}
function toggleRebateSwitch(checked) {
  state.applyRebate = checked;
  refreshCartUI();
}

async function submitSaleTransaction() {
  if (state.cart.length === 0) {
    alert("ದಯವಿಟ್ಟು ಮಾರಾಟ ಮಾಡಲು ಕನಿಷ್ಠ ಒಂದು ಉತ್ಪನ್ನವನ್ನು ಆಯ್ಕೆಮಾಡಿ.");
    return;
  }
  const custName = document.getElementById("sale-cust-name")?.value || "Retail Walk-in (ಚಿಲ್ಲರೆ ಗ್ರಾಹಕರು)";
  const custPhone = document.getElementById("sale-cust-phone")?.value || "9999999999";

  const warehouseId = state.activeShowroomWarehouseId || state.warehouses.find(w => w.storage_type === 'FINISHED_SHOWROOM')?.id;
  if (!warehouseId) {
    alert("ಮಳಿಗೆಯ ದಾಸ್ತಾನು ಶೇಖರಣಾ ಹಂತ ಲಭ್ಯವಿಲ್ಲ! (Showroom storage node not resolved)");
    return;
  }

  const payload = {
    sale_channel: "RETAIL_SHOWROOM",
    warehouse_id: warehouseId,
    customer_name: custName,
    customer_phone: custPhone,
    apply_govt_rebate: state.applyRebate,
    payment_mode: state.paymentMode,
    items: state.cart.map(c => ({
      product_id: c.product_id,
      quantity: c.qty
    }))
  };

  try {
    const res = await api.createSale(payload);
    state.cart = [];
    refreshCartUI();
    showPrintableBill(res.sale_id);
    loadSalesSection();
  } catch (err) {
    alert("ಮಾರಾಟ ಪ್ರಕ್ರಿಯೆ ವಿಫಲವಾಗಿದೆ: " + err.message);
  }
}

async function showPrintableBill(saleId) {
  try {
    const data = await api.getSaleBill(saleId);
    const b = data.bill;
    const items = data.items;

    const modal = document.getElementById("modal-bill");
    const container = document.getElementById("bill-document-content");

    container.innerHTML = `
      <div class="paper-bill">
        <div class="bill-header-inst">
          <h2>${b.society_name_kn}</h2>
          <h3>${b.society_name_en}</h3>
          <p>${b.registered_office_address} | ದೂರವಾಣಿ: ${b.primary_phone}</p>
          <p>ನೋಂದಣಿ ಸಂಖ್ಯೆ: <strong>${b.registration_number}</strong> | ಜಿಎಸ್‍ಟಿ: ${b.society_gstin || 'EXEMPT'}</p>
        </div>

        <div style="display:flex; justify-content:space-between; margin-bottom:0.75rem;">
          <div>ಬಿಲ್ ಸಂಖ್ಯೆ: <strong>${b.bill_number}</strong></div>
          <div>ದಿನಾಂಕ: <strong>${b.created_at.slice(0, 19)}</strong></div>
        </div>
        <div style="margin-bottom:0.75rem;">ಗ್ರಾಹಕರ ಹೆಸರು: <strong>${b.customer_name || 'Walk-in'}</strong> (${b.customer_phone || ''})</div>

        <table class="ledger-table" style="font-size:0.75rem; border-top:1px solid #111; border-bottom:1px solid #111;">
          <thead>
            <tr><th>ಕ್ರ.ಸಂ.</th><th>ವಿವರ</th><th>ಪ್ರಮಾಣ</th><th>ದರ</th><th>ಮೊತ್ತ</th></tr>
          </thead>
          <tbody>
            ${items.map((it, idx) => `
              <tr>
                <td>${idx + 1}</td>
                <td>${it.name_kn} <br><small>${it.sku} (HSN: ${it.hsn_code})</small></td>
                <td>${it.quantity} ${it.uom}</td>
                <td>${formatCurrency(it.unit_rate)}</td>
                <td>${formatCurrency(it.line_total)}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>

        <div style="border-bottom:1px solid #111; padding:0.5rem 0; margin-bottom:0.75rem;">
          <div style="display:flex; justify-content:space-between;"><span>ಒಟ್ಟು ಬೆಲೆ:</span><span>${formatCurrency(b.gross_amount)}</span></div>
          ${b.rebate_amount > 0 ? `<div style="display:flex; justify-content:space-between; color:var(--accent-emerald); font-weight:700;"><span>ಸರ್ಕಾರಿ ೨೦% ರಿಯಾಯಿತಿ:</span><span>- ${formatCurrency(b.rebate_amount)}</span></div>` : ''}
          <div style="display:flex; justify-content:space-between;"><span>ಜಿಎಸ್‍ಟಿ (GST 5%):</span><span>${formatCurrency(b.tax_amount)}</span></div>
          <div style="display:flex; justify-content:space-between; font-weight:800; font-size:1.05rem; border-top:1px dashed #555; padding-top:0.35rem; margin-top:0.25rem;">
            <span>ಗ್ರಾಹಕರು ಪಾವತಿಸಿದ ಮೊತ್ತ:</span><span>${formatCurrency(b.net_customer_payable)}</span>
          </div>
        </div>

        ${b.rebate_amount > 0 ? `
          <div style="background:#f0fdf4; border:1px dashed #16a34a; padding:0.5rem; text-align:center; font-size:0.75rem; color:#166534; margin-bottom:0.75rem;">
            ಕರ್ನಾಟಕ ಸರ್ಕಾರದ ಕೈಮಗ್ಗ ಮತ್ತು ಜವಳಿ ನಿರ್ದೇಶನಾಲಯದ ೨೦% ವಿಶೇಷ ಹಬ್ಬದ ರಿಯಾಯಿತಿ ಅನ್ವಯಿಸಲಾಗಿದೆ.<br>
            ಸಹಾಯಧನ ಮೊತ್ತ: <strong>${formatCurrency(b.govt_subsidy_receivable)}</strong>
          </div>
        ` : ''}

        <div style="display:flex; justify-content:space-between; margin-top:2rem; font-size:0.75rem;">
          <div>ಕ್ಯಾಷಿಯರ್ ಸಹಿ</div>
          <div>ಕಾರ್ಯದರ್ಶಿ ಸಹಿ</div>
        </div>
      </div>
    `;

    openModal("modal-bill");
  } catch (err) {
    alert("ರಶೀದಿ ಡೌನ್‌ಲೋಡ್ ವಿಫಲವಾಗಿದೆ: " + err.message);
  }
}

// -------------------------------------------------------------------
// 6. STATUTORY COOPERATIVE REGISTERS & DAYBOOK
// -------------------------------------------------------------------
async function loadReportsSection(subTab = "daybook") {
  const container = document.getElementById("sec-reports");
  if (!container) return;

  try {
    if (subTab === "daybook") {
      const db = await api.getDaybook();
      container.innerHTML = `
        <div class="card-inst">
          <div class="card-inst-header">
            <div class="card-inst-title">📖 ಶಾಸನಬದ್ಧ ದಿನಚರಿ ಪುಸ್ತಕ (Daily Daybook - Form A)</div>
            <div style="display:flex; gap:0.5rem;">
              <button class="btn-inst btn-inst-secondary" onclick="loadReportsSection('weaver_material')">ನೂಲು ಬ್ಯಾಲೆನ್ಸ್ ರಿಜಿಸ್ಟರ್</button>
              <button class="btn-inst btn-inst-secondary" onclick="loadReportsSection('weaver_wages')">ನೇಕಾರ ಕೂಲಿ & TF ರಿಜಿಸ್ಟರ್</button>
              <button class="btn-inst btn-inst-secondary" onclick="loadReportsSection('rebate_claims')">ರಿಯಾಯಿತಿ ಕ್ಲೈಮ್ ಶೆಡ್ಯೂಲ್</button>
            </div>
          </div>

          <div class="pulse-grid" style="margin-bottom:1.25rem;">
            <div class="pulse-card emerald-border">
              <div class="pulse-card-label">ಇಂದಿನ ಒಟ್ಟು ಜಮೆಗಳು (Receipts)</div>
              <div class="pulse-card-value" style="color:var(--accent-emerald);">${formatCurrency(db.total_receipts)}</div>
            </div>
            <div class="pulse-card alert-border">
              <div class="pulse-card-label">ಇಂದಿನ ಒಟ್ಟು ಪಾವತಿಗಳು (Disbursements)</div>
              <div class="pulse-card-value" style="color:var(--primary-crimson);">${formatCurrency(db.total_payments)}</div>
            </div>
            <div class="pulse-card">
              <div class="pulse-card-label">ನಿವ್ವಳ ನಗದು ಶಿಲ್ಕು (Net Cash Position)</div>
              <div class="pulse-card-value">${formatCurrency(db.net_cash_flow)}</div>
            </div>
          </div>

          <div style="display:grid; grid-template-columns:1fr 1fr; gap:1.25rem;">
            <div>
              <h4 style="color:var(--accent-emerald); margin-bottom:0.5rem;">ಜಮೆಗಳು (Receipts)</h4>
              <table class="ledger-table" style="font-size:0.75rem;">
                <thead><tr><th>ವೋಚರ್/ಬಿಲ್</th><th>ವಿವರ</th><th>ಮೊತ್ತ</th></tr></thead>
                <tbody>
                  ${db.receipts.map(r => `<tr><td>${r.voucher_ref}</td><td>${r.description}</td><td style="font-weight:700; color:var(--accent-emerald);">${formatCurrency(r.amount)}</td></tr>`).join("") || '<tr><td colspan="3" style="text-align:center;">ಯಾವುದೇ ಜಮೆ ಇಲ್ಲ</td></tr>'}
                </tbody>
              </table>
            </div>
            <div>
              <h4 style="color:var(--primary-crimson); margin-bottom:0.5rem;">ಖರ್ಚು/ಪಾವತಿಗಳು (Payments)</h4>
              <table class="ledger-table" style="font-size:0.75rem;">
                <thead><tr><th>ವೋಚರ್/ರಶೀದಿ</th><th>ವಿವರ</th><th>ಮೊತ್ತ</th></tr></thead>
                <tbody>
                  ${db.payments.map(p => `<tr><td>${p.voucher_ref}</td><td>${p.description}</td><td style="font-weight:700; color:var(--primary-crimson);">${formatCurrency(p.amount)}</td></tr>`).join("") || '<tr><td colspan="3" style="text-align:center;">ಯಾವುದೇ ಪಾವತಿ ಇಲ್ಲ</td></tr>'}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      `;
    } else if (subTab === "weaver_material") {
      const mat = await api.getWeaverMaterialRegister();
      container.innerHTML = `
        <div class="card-inst">
          <div class="card-inst-header">
            <div class="card-inst-title">🧵 ನೇಕಾರರ ನೂಲು ಬ್ಯಾಲೆನ್ಸ್ ರಿಜಿಸ್ಟರ್ (Loom Custody Balance)</div>
            <button class="btn-inst btn-inst-secondary" onclick="loadReportsSection('daybook')">← ದಿನಚರಿ ಪುಸ್ತಕಕ್ಕೆ ಹಿಂತಿರುಗಿ</button>
          </div>
          <div class="ledger-table-wrap">
            <table class="ledger-table">
              <thead><tr><th>ಸದಸ್ಯತ್ವ</th><th>ನೇಕಾರರು</th><th>ಗ್ರಾಮ</th><th>ಮಗ್ಗ</th><th>ಒಟ್ಟು ಹಂಚಿದ ನೂಲು</th><th>ಮನೆಯಲ್ಲಿರುವ ಚಾಲ್ತಿ ನೂಲು (WIP)</th><th>ಪೂರ್ಣಗೊಂಡ ಸೀರೆಗಳು</th></tr></thead>
              <tbody>
                ${mat.map(m => `
                  <tr>
                    <td><strong>${m.membership_no}</strong></td>
                    <td>${m.full_name_kn}</td>
                    <td>${m.village}</td>
                    <td>${m.loom_type}</td>
                    <td>${m.total_yarn_issued_kgs} Kgs</td>
                    <td style="font-weight:700; color:var(--primary-gold);">${m.active_yarn_at_looms_kgs} Kgs</td>
                    <td>${m.completed_pieces} / ${m.total_pieces_targeted}</td>
                  </tr>
                `).join("")}
              </tbody>
            </table>
          </div>
        </div>
      `;
    } else if (subTab === "weaver_wages") {
      const wgs = await api.getWeaverWagesRegister();
      container.innerHTML = `
        <div class="card-inst">
          <div class="card-inst-header">
            <div class="card-inst-title">💰 ನೇಕಾರರ ಮಗ್ಗದ ಕೂಲಿ & ಶಾಸನಬದ್ಧ ಉಳಿತಾಯ ನಿಧಿ ರಿಜಿಸ್ಟರ್ (KCS Act Form)</div>
            <button class="btn-inst btn-inst-secondary" onclick="loadReportsSection('daybook')">← ದಿನಚರಿ ಪುಸ್ತಕಕ್ಕೆ ಹಿಂತಿರುಗಿ</button>
          </div>
          <div class="ledger-table-wrap">
            <table class="ledger-table">
              <thead><tr><th>ಸದಸ್ಯತ್ವ</th><th>ನೇಕಾರರು</th><th>ನೇಯ್ದ ಸೀರೆಗಳು</th><th>ಒಟ್ಟು ಗಳಿಸಿದ ಕೂಲಿ</th><th>ಉಳಿತಾಯ ನಿಧಿ (8% TF)</th><th>ನಿವ್ವಳ ಜಮೆ ಕೂಲಿ</th><th>ವೇತನ ಬಾಕಿ ಶಿಲ್ಕು</th></tr></thead>
              <tbody>
                ${wgs.map(w => `
                  <tr>
                    <td><strong>${w.membership_no}</strong></td>
                    <td>${w.full_name_kn}</td>
                    <td>${w.total_saris_woven} ಸೀರೆಗಳು</td>
                    <td>${formatCurrency(w.total_gross_wages)}</td>
                    <td style="color:var(--primary-navy); font-weight:700;">${formatCurrency(w.total_thrift_deducted)}</td>
                    <td style="color:var(--accent-emerald); font-weight:700;">${formatCurrency(w.total_net_wages_credited)}</td>
                    <td style="font-weight:800; color:var(--primary-crimson);">${formatCurrency(w.passbook_wage_balance)}</td>
                  </tr>
                `).join("")}
              </tbody>
            </table>
          </div>
        </div>
      `;
    } else if (subTab === "rebate_claims") {
      const claims = await api.getRebateClaimsSchedule();
      container.innerHTML = `
        <div class="card-inst">
          <div class="card-inst-header">
            <div>
              <div class="card-inst-title">🏛️ ಕೈಮಗ್ಗ ನಿರ್ದೇಶನಾಲಯದ ೨೦% ರಿಯಾಯಿತಿ ಕ್ಲೈಮ್ ಶೆಡ್ಯೂಲ್ (Annexure-I)</div>
              <p style="font-size:0.8rem; color:var(--text-muted); margin-top:0.25rem;">ಕೈಮಗ್ಗ ಮತ್ತು ಜವಳಿ ಇಲಾಖೆಗೆ ಸಲ್ಲಿಸಲು ಅಧಿಕೃತವಾಗಿ ಸಿದ್ಧಪಡಿಸಲಾದ ಕ್ಲೈಮ್ ಪಟ್ಟಿ</p>
            </div>
            <button class="btn-inst btn-inst-secondary" onclick="loadReportsSection('daybook')">← ದಿನಚರಿ ಪುಸ್ತಕಕ್ಕೆ ಹಿಂತಿರುಗಿ</button>
          </div>
          <div class="pulse-card emerald-border" style="margin-bottom:1.25rem; max-width:320px;">
            <div class="pulse-card-label">ಸರ್ಕಾರದಿಂದ ಸಂಘಕ್ಕೆ ಬರಬೇಕಾದ ಸಹಾಯಧನ</div>
            <div class="pulse-card-value" style="color:var(--accent-emerald);">${formatCurrency(claims.total_claimable_subsidy)}</div>
            <div class="pulse-card-sub">${claims.total_bills_count} ಸಬ್ಸಿಡಿ ಬಿಲ್‌ಗಳು ಸಲ್ಲಿಕೆಗೆ ಸಿದ್ಧ</div>
          </div>
          <div class="ledger-table-wrap">
            <table class="ledger-table">
              <thead><tr><th>ಬಿಲ್ ಸಂಖ್ಯೆ</th><th>ದಿನಾಂಕ</th><th>ಗ್ರಾಹಕರ ವಿವರ</th><th>ಒಟ್ಟು ಬೆಲೆ</th><th>೨೦% ರಿಯಾಯಿತಿ ಮೊತ್ತ</th><th>ಗ್ರಾಹಕರು ಪಾವತಿಸಿದ್ದು</th><th>ಕ್ಲೈಮ್ ಸಹಾಯಧನ</th></tr></thead>
              <tbody>
                ${claims.claims.map(c => `
                  <tr>
                    <td><strong>${c.bill_number}</strong></td>
                    <td>${c.created_at.slice(0, 10)}</td>
                    <td>${c.customer_name}</td>
                    <td>${formatCurrency(c.gross_amount)}</td>
                    <td style="color:var(--accent-emerald); font-weight:700;">- ${formatCurrency(c.rebate_amount)}</td>
                    <td>${formatCurrency(c.net_customer_payable)}</td>
                    <td style="font-weight:800; color:var(--accent-emerald);">${formatCurrency(c.govt_subsidy_receivable)}</td>
                  </tr>
                `).join("") || '<tr><td colspan="7" style="text-align:center;">ಯಾವುದೇ ಕ್ಲೈಮ್ ಇಲ್ಲ</td></tr>'}
              </tbody>
            </table>
          </div>
        </div>
      `;
    }
  } catch (err) {
    container.innerHTML = `<div style="color:var(--primary-crimson);">ದೋಷ: ${err.message}</div>`;
  }
}

// -------------------------------------------------------------------
// 7. 8-STEP RESUMABLE DIGITAL ONBOARDING WIZARD
// -------------------------------------------------------------------
function startOnboardingWizard() {
  state.onboardingStep = 1;
  showAppShell();
  state.currentSection = "onboarding";
  document.querySelectorAll(".op-nav-btn").forEach(btn => btn.classList.remove("active"));
  document.querySelectorAll(".content-section").forEach(sec => sec.classList.remove("active"));
  document.getElementById("sec-onboarding").classList.add("active");
  renderWizardStep();
}

function renderWizardStep() {
  const container = document.getElementById("sec-onboarding");
  if (!container) return;

  const s = state.onboardingStep;
  const d = state.onboardingData;

  let formFields = "";
  if (s === 1) {
    formFields = `
      <h3 style="color:var(--primary-navy); margin-bottom:1rem;" data-i18n="onb.step1_title">೧. ಖಾತೆ ಮತ್ತು ಸಂಪರ್ಕ (Account Credentials)</h3>
      <div class="form-grid">
        <div class="form-group">
          <label class="form-label">ಮೊಬೈಲ್ ಸಂಖ್ಯೆ *</label>
          <input type="text" id="ob-phone" class="form-input" placeholder="ಉದಾ: 9845012345" value="${d.phone || ''}" />
        </div>
        <div class="form-group">
          <label class="form-label">ಇಮೇಲ್ (Email)</label>
          <input type="email" id="ob-email" class="form-input" placeholder="secretary@society.coop" value="${d.email || ''}" />
        </div>
        <div class="form-group full">
          <label class="form-label">ಲಾಗಿನ್ ಪಾಸ್‌ವರ್ಡ್ *</label>
          <input type="password" id="ob-password" class="form-input" placeholder="ಪಾಸ್‌ವರ್ಡ್ ನಮೂದಿಸಿ" value="${d.password || 'admin123'}" />
        </div>
      </div>
    `;
  } else if (s === 2) {
    formFields = `
      <h3 style="color:var(--primary-navy); margin-bottom:1rem;" data-i18n="onb.step2_title">೨. ಸಂಘದ ಶಾಸನಬದ್ಧ ಗುರುತು (Legal Identity)</h3>
      <div class="form-grid">
        <div class="form-group">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.35rem;">
            <label class="form-label" style="margin-bottom:0;">ಸಂಘದ ಹೆಸರು (ಕನ್ನಡದಲ್ಲಿ) *</label>
            <button type="button" class="btn-inst btn-inst-secondary" style="font-size:0.75rem; padding:0.2rem 0.55rem;" onclick="triggerFieldTranslation('ob-name-kn', 'ob-name-en', 'kn', 'en')">🔄 Translate to English</button>
          </div>
          <input type="text" id="ob-name-kn" class="form-input" placeholder="ಉದಾ: ಗದಗ ಹತ್ತಿ ಕೈಮಗ್ಗ ನೇಕಾರರ ಸಹಕಾರ ಸಂಘ ನಿಯಮಿತ" value="${d.name_kn || ''}" />
        </div>
        <div class="form-group">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.35rem;">
            <label class="form-label" style="margin-bottom:0;">Legal Society Name (English) *</label>
            <button type="button" class="btn-inst btn-inst-secondary" style="font-size:0.75rem; padding:0.2rem 0.55rem;" onclick="triggerFieldTranslation('ob-name-en', 'ob-name-kn', 'en', 'kn')">🔄 ಕನ್ನಡಕ್ಕೆ ಅನುವಾದಿಸು</button>
          </div>
          <input type="text" id="ob-name-en" class="form-input" placeholder="e.g. Gadag Cotton Handloom Weavers Co-op Society Ltd." value="${d.name_en || ''}" />
        </div>
        <div class="form-group">
          <label class="form-label">ನೋಂದಣಿ ಸಂಖ್ಯೆ (KCS Act 1959) *</label>
          <input type="text" id="ob-reg-no" class="form-input" placeholder="ಉದಾ: DR/KCS/UDP/1985/412" value="${d.reg_no || ''}" />
        </div>
        <div class="form-group">
          <label class="form-label">ನೋಂದಣಿ ದಿನಾಂಕ *</label>
          <input type="date" id="ob-reg-date" class="form-input" value="${d.reg_date || '1985-04-12'}" />
        </div>
      </div>
    `;
  } else if (s === 3) {
    formFields = `
      <h3 style="color:var(--primary-navy); margin-bottom:1rem;" data-i18n="onb.step3_title">೩. ಸ್ಥಳ ಮತ್ತು ವಿಳಾಸ (Geography & Address)</h3>
      <div class="form-grid">
        <div class="form-group">
          <label class="form-label">ಕರ್ನಾಟಕ ಜಿಲ್ಲೆ (District) *</label>
          <input type="text" id="ob-district" class="form-input" value="${d.district || 'Udupi'}" />
        </div>
        <div class="form-group">
          <label class="form-label">ತಾಲೂಕು (Taluk) *</label>
          <input type="text" id="ob-taluk" class="form-input" value="${d.taluk || 'Brahmavar'}" />
        </div>
        <div class="form-group">
          <label class="form-label">ಹೋಬಳಿ / ಗ್ರಾಮ / ನಗರ *</label>
          <input type="text" id="ob-village" class="form-input" value="${d.village || 'Brahmavar Town'}" />
        </div>
        <div class="form-group">
          <label class="form-label">ಪಿನ್ ಕೋಡ್ (PIN) *</label>
          <input type="text" id="ob-pin" class="form-input" value="${d.pin || '576213'}" />
        </div>
        <div class="form-group full">
          <label class="form-label">ನೋಂದಾಯಿತ ಕಛೇರಿ ವಿಳಾಸ *</label>
          <input type="text" id="ob-address" class="form-input" value="${d.address || 'Handloom Bhavan, Main Road, Brahmavar, Udupi - 576213'}" />
        </div>
      </div>
    `;
  } else if (s === 4) {
    formFields = `
      <h3 style="color:var(--primary-navy); margin-bottom:1rem;" data-i18n="onb.step4_title">೪. ಅಧಿಕೃತ ಮತ್ತು ಬ್ಯಾಂಕ್ ವಿವರ (Official Credentials)</h3>
      <div class="form-grid">
        <div class="form-group">
          <label class="form-label">ಕೈಮಗ್ಗ ನಿರ್ದೇಶನಾಲಯದ ಕೋಡ್</label>
          <input type="text" id="ob-dept-code" class="form-input" value="${d.dept_code || 'DTH/UDP/302'}" />
        </div>
        <div class="form-group">
          <label class="form-label">PAN ಸಂಖ್ಯೆ</label>
          <input type="text" id="ob-pan" class="form-input" value="${d.pan || 'AAAAU0000U'}" />
        </div>
        <div class="form-group">
          <label class="form-label">ಜಿಎಸ್‍ಟಿ (GSTIN - ಐಚ್ಛಿಕ)</label>
          <input type="text" id="ob-gstin" class="form-input" value="${d.gstin || '29CCCCC0000C1Z8'}" />
        </div>
        <div class="form-group">
          <label class="form-label">ಸಹಕಾರ ಬ್ಯಾಂಕ್ ಖಾತೆ ಸಂಖ್ಯೆ</label>
          <input type="text" id="ob-bank-acc" class="form-input" value="${d.bank_acc || '4009101009'}" />
        </div>
      </div>
    `;
  } else if (s === 5) {
    formFields = `
      <h3 style="color:var(--primary-navy); margin-bottom:1rem;" data-i18n="onb.step5_title">೫. ಕಾರ್ಯಾಚರಣೆ ಮತ್ತು ಮಗ್ಗಗಳು (Operations Footprint)</h3>
      <div class="form-grid">
        <div class="form-group">
          <label class="form-label">ನೋಂದಾಯಿತ ನೇಕಾರ ಸದಸ್ಯರ ಸಂಖ್ಯೆ</label>
          <input type="number" id="ob-members-count" class="form-input" value="${d.members_count || 85}" />
        </div>
        <div class="form-group">
          <label class="form-label">ಕಾರ್ಯನಿರತ ಮಗ್ಗಗಳ ಸಂಖ್ಯೆ</label>
          <input type="number" id="ob-looms-count" class="form-input" value="${d.looms_count || 64}" />
        </div>
      </div>
    `;
  } else if (s === 6) {
    formFields = `
      <h3 style="color:var(--primary-navy); margin-bottom:1rem;" data-i18n="onb.step6_title">೬. ಆಡಳಿತ ಮಂಡಳಿ / ಸಿಬ್ಬಂದಿ (Administrator)</h3>
      <div class="form-grid">
        <div class="form-group full">
          <label class="form-label">ಮುಖ್ಯ ಕಾರ್ಯನಿರ್ವಾಹಕರ ಹೆಸರು (Secretary / MD Full Name) *</label>
          <input type="text" id="ob-admin-name" class="form-input" value="${d.admin_name || 'Anand Madhyastha'}" />
        </div>
      </div>
    `;
  } else if (s === 7) {
    formFields = `
      <h3 style="color:var(--primary-navy); margin-bottom:1rem;" data-i18n="onb.step7_title">೭. ಭಾಷೆ ಮತ್ತು ಆದ್ಯತೆ (Language)</h3>
      <div class="form-grid">
        <div class="form-group full">
          <label class="form-label">ಸಂಸ್ಥೆಯ ಪ್ರಾಥಮಿಕ ಭಾಷೆ (Preferred Operating Language)</label>
          <select id="ob-lang" class="form-input">
            <option value="kn" selected>ಕನ್ನಡ (Kannada - ಶಿಫಾರಸು ಮಾಡಲಾಗಿದೆ)</option>
            <option value="en">English</option>
          </select>
        </div>
      </div>
    `;
  } else if (s === 8) {
    formFields = `
      <h3 style="color:var(--primary-navy); margin-bottom:1rem;" data-i18n="onb.step8_title">೮. ಪರಿಶೀಲನೆ ಮತ್ತು ದೃಢೀಕರಣ (Verification Review)</h3>
      <div style="background:#f8fafc; border:1px solid var(--border-card); padding:1rem; border-radius:var(--radius-sm); font-size:0.85rem; line-height:1.6;">
        <p><strong>ಸಂಸ್ಥೆ:</strong> ${d.name_kn} (${d.name_en})</p>
        <p><strong>ನೋಂದಣಿ ಸಂಖ್ಯೆ:</strong> ${d.reg_no} | ದಿನಾಂಕ: ${d.reg_date}</p>
        <p><strong>ಸ್ಥಳ:</strong> ${d.village}, ${d.taluk}, ${d.district} - ${d.pin}</p>
        <p><strong>ಮುಖ್ಯಸ್ಥರು:</strong> ${d.admin_name} | ಸಂಪರ್ಕ: ${d.phone}</p>
      </div>
    `;
  }

  container.innerHTML = `
    <div class="wizard-box">
      <div class="wizard-steps-tracker">
        ${[1, 2, 3, 4, 5, 6, 7, 8].map(stepNum => `
          <div class="wizard-step-node">
            <div class="wizard-node-circle ${stepNum === s ? 'active' : (stepNum < s ? 'completed' : '')}">${stepNum}</div>
            <div class="wizard-node-label">${getStepShortLabel(stepNum)}</div>
          </div>
        `).join("")}
      </div>

      ${formFields}

      <div style="display:flex; justify-content:space-between; margin-top:2rem; border-top:1px solid var(--border-card); padding-top:1rem;">
        ${s > 1 ? `<button class="btn-inst btn-inst-secondary" onclick="prevOnboardingStep()">← ಹಿಂದಿನ ಹಂತ</button>` : `<div></div>`}
        <div style="display:flex; gap:0.5rem;">
          <button class="btn-inst btn-inst-secondary" onclick="saveDraftCurrentStep()">ಡ್ರಾಫ್ಟ್ ಉಳಿಸಿ</button>
          ${s < 8 ? `<button class="btn-inst btn-inst-primary" onclick="nextOnboardingStep()">ಮುಂದಿನ ಹಂತ →</button>` : `<button class="btn-inst btn-inst-gold" onclick="submitFinalizeSociety()">ಸಂಘದ ಡಿಜಿಟಲ್ ಕೇಂದ್ರ ರಚಿಸಿ ✓</button>`}
        </div>
      </div>
    </div>
  `;

  if (s === 2) {
    setupAutoTranslate("ob-name-kn", "ob-name-en", "kn", "en");
    setupAutoTranslate("ob-name-en", "ob-name-kn", "en", "kn");
  }
}

function getStepShortLabel(num) {
  const labels = ["ಖಾತೆ", "ಗುರುತು", "ಸ್ಥಳ", "ಅಧಿಕೃತ", "ಮಗ್ಗಗಳು", "ಮುಖ್ಯಸ್ಥರು", "ಭಾಷೆ", "ಪರಿಶೀಲನೆ"];
  return labels[num - 1] || "";
}

function captureCurrentStepValues() {
  const s = state.onboardingStep;
  const d = state.onboardingData;
  if (s === 1) {
    d.phone = document.getElementById("ob-phone")?.value || d.phone;
    d.email = document.getElementById("ob-email")?.value || d.email;
    d.password = document.getElementById("ob-password")?.value || "admin123";
  } else if (s === 2) {
    d.name_kn = document.getElementById("ob-name-kn")?.value || d.name_kn;
    d.name_en = document.getElementById("ob-name-en")?.value || d.name_en;
    d.reg_no = document.getElementById("ob-reg-no")?.value || d.reg_no;
    d.reg_date = document.getElementById("ob-reg-date")?.value || d.reg_date;
  } else if (s === 3) {
    d.district = document.getElementById("ob-district")?.value || d.district;
    d.taluk = document.getElementById("ob-taluk")?.value || d.taluk;
    d.village = document.getElementById("ob-village")?.value || d.village;
    d.pin = document.getElementById("ob-pin")?.value || d.pin;
    d.address = document.getElementById("ob-address")?.value || d.address;
  } else if (s === 4) {
    d.dept_code = document.getElementById("ob-dept-code")?.value || d.dept_code;
    d.pan = document.getElementById("ob-pan")?.value || d.pan;
    d.gstin = document.getElementById("ob-gstin")?.value || d.gstin;
    d.bank_acc = document.getElementById("ob-bank-acc")?.value || d.bank_acc;
  } else if (s === 5) {
    d.members_count = parseInt(document.getElementById("ob-members-count")?.value) || 80;
    d.looms_count = parseInt(document.getElementById("ob-looms-count")?.value) || 60;
  } else if (s === 6) {
    d.admin_name = document.getElementById("ob-admin-name")?.value || d.admin_name;
  } else if (s === 7) {
    d.lang = document.getElementById("ob-lang")?.value || "kn";
  }
}

function nextOnboardingStep() {
  captureCurrentStepValues();
  state.onboardingStep += 1;
  renderWizardStep();
}

function prevOnboardingStep() {
  captureCurrentStepValues();
  state.onboardingStep -= 1;
  renderWizardStep();
}

async function saveDraftCurrentStep() {
  captureCurrentStepValues();
  try {
    const res = await api.saveOnboardingStep({
      contact_identifier: state.onboardingData.phone || "9845012345",
      current_step: state.onboardingStep,
      form_data: state.onboardingData
    });
    alert("ಡ್ರಾಫ್ಟ್ ಉಳಿಸಲಾಗಿದೆ! (Draft ID: " + res.draft_id + ")");
  } catch (err) {
    alert("ಡ್ರಾಫ್ಟ್ ಉಳಿಸಲು ವಿಫಲವಾಗಿದೆ: " + err.message);
  }
}

async function submitFinalizeSociety() {
  captureCurrentStepValues();
  const d = state.onboardingData;

  const randSuffix = Math.floor(1000 + Math.random() * 9000);
  let nameEn = d.name_en?.trim();
  let nameKn = d.name_kn?.trim();

  // Bidirectional auto-fill if one is empty
  if (!nameEn && nameKn) {
    nameEn = await translateText(nameKn, "kn", "en");
  } else if (!nameKn && nameEn) {
    nameKn = await translateText(nameEn, "en", "kn");
  }

  const payload = {
    primary_phone: d.phone || ("98450" + randSuffix),
    primary_email: d.email || (`admin-${randSuffix}@society.coop`),
    admin_password: d.password || "admin123",
    admin_full_name: d.admin_name || "Society Administrator",
    legal_name_en: nameEn || "Karnataka Handloom Weavers Co-operative Society Ltd.",
    legal_name_kn: nameKn || "ಕರ್ನಾಟಕ ಕೈಮಗ್ಗ ನೇಕಾರರ ಸಹಕಾರ ಸಂಘ ನಿಯಮಿತ",
    registration_number: d.reg_no || (`DR/KCS/${randSuffix}/${new Date().getFullYear()}`),
    registration_date: d.reg_date || "1985-04-12",
    society_type: d.society_type || "PRIMARY_WEAVERS_COOP",
    district: d.district || "Karnataka",
    taluk: d.taluk || "",
    hobli_village: d.village || "",
    pincode: d.pin || "560001",
    registered_office_address: d.address || "",
    directorate_society_code: d.dept_code || null,
    pan: d.pan || null,
    gstin: d.gstin || null,
    bank_account_no: d.bank_acc || null,
    members_count: d.members_count || 50,
    active_looms_count: d.looms_count || 40,
    preferred_language: d.lang || currentLanguage
  };

  try {
    const res = await api.finalizeOnboarding(payload);
    alert(`ಸಂಘದ ಡಿಜಿಟಲ್ ಕೇಂದ್ರ ಸೃಷ್ಟಿಯಾಗಿದೆ!\nಸಂಘ: ${res.legal_name_kn}\nಲಾಗಿನ್ ಸ್ಲಗ್: ${res.slug}`);
    
    // Immediately log into the newly created society workspace
    try {
      const authData = await api.login(payload.primary_phone, payload.admin_password, res.slug);
      state.currentTenant = authData;
      state.cart = [];
      await refreshTenantStorageNodes();
      updateTenantUI();
      showAppShell();
      closeAllModals();
      navigateTo("operations");
    } catch (loginErr) {
      showLandingPage();
    }
  } catch (err) {
    alert("ಸಂಘ ರಚನೆ ವಿಫಲವಾಗಿದೆ: " + err.message);
  }
}

// -------------------------------------------------------------------
// MODAL & GLOBAL HELPERS
// -------------------------------------------------------------------
function setupGlobalListeners() {
  document.querySelectorAll(".op-nav-btn").forEach(btn => {
    btn.addEventListener("click", () => navigateTo(btn.getAttribute("data-section")));
  });
}

function openModal(modalId) {
  const m = document.getElementById(modalId);
  if (m) m.style.display = "flex";
}

function closeAllModals() {
  document.querySelectorAll(".modal-overlay").forEach(m => m.style.display = "none");
}

function printBillDocument() {
  window.print();
}
