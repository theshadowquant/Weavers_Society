/**
 * Multi-Tenant API Client for Karnataka Handloom Cooperative Platform
 */
const API_BASE = "/api/v1";

class ApiClient {
  constructor() {
    this.token = localStorage.getItem("society_token") || null;
    this.tenantInfo = JSON.parse(localStorage.getItem("society_tenant") || "null");
  }

  setSession(token, tenantData) {
    this.token = token;
    this.tenantInfo = tenantData;
    localStorage.setItem("society_token", token);
    localStorage.setItem("society_tenant", JSON.stringify(tenantData));
  }

  clearSession() {
    this.token = null;
    this.tenantInfo = null;
    localStorage.removeItem("society_token");
    localStorage.removeItem("society_tenant");
  }

  async request(endpoint, options = {}) {
    const headers = {
      "Content-Type": "application/json",
      ...(options.headers || {})
    };

    if (this.token) {
      headers["Authorization"] = `Bearer ${this.token}`;
    }

    try {
      const response = await fetch(`${API_BASE}${endpoint}`, {
        ...options,
        headers
      });

      if (response.status === 401) {
        console.warn("Session expired or unauthorized. Clearing session.");
        this.clearSession();
        if (window.onAuthExpired) window.onAuthExpired();
      }

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(errorData.detail || `Request failed with status ${response.status}`);
      }

      return await response.json();
    } catch (err) {
      console.error(`API Error [${endpoint}]:`, err);
      throw err;
    }
  }

  // Auth
  async login(identifier, password, tenantSlug = null, tenantId = null) {
    const data = await this.request("/auth/login", {
      method: "POST",
      body: JSON.stringify({ identifier, password, tenant_slug: tenantSlug, tenant_id: tenantId })
    });
    this.setSession(data.access_token, data);
    return data;
  }

  async switchTenant(targetTenantId) {
    const data = await this.request("/auth/switch-tenant", {
      method: "POST",
      body: JSON.stringify({ target_tenant_id: targetTenantId })
    });
    this.setSession(data.access_token, data);
    return data;
  }

  async getMe() {
    return await this.request("/auth/me");
  }

  async getTenantWarehouses() {
    return await this.request("/inventory/warehouses");
  }

  // Operational Command Center
  async getCommandCenter() {
    return await this.request("/dashboard/command-center");
  }

  // Onboarding
  async saveOnboardingStep(payload) {
    return await this.request("/onboarding/step", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  }

  async getOnboardingDraft(contact) {
    return await this.request(`/onboarding/draft/${encodeURIComponent(contact)}`);
  }

  async finalizeOnboarding(payload) {
    return await this.request("/onboarding/finalize", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  }

  // Weavers
  async getWeavers(search = "") {
    const q = search ? `?search=${encodeURIComponent(search)}` : "";
    return await this.request(`/weavers${q}`);
  }

  async createWeaver(payload) {
    return await this.request("/weavers", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  }

  async getWeaverProfile(weaverId) {
    return await this.request(`/weavers/${weaverId}/profile`);
  }

  // Production & QC
  async getProductionAllotments() {
    return await this.request("/production/allotments");
  }

  async createProductionAllotment(payload) {
    return await this.request("/production/allotments", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  }

  async processTechnicalInspection(payload) {
    return await this.request("/production/inspections", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  }

  // Multi-State Inventory & Raw Materials
  async getInventoryStatus() {
    return await this.request("/inventory/status");
  }

  async getYarnLots() {
    return await this.request("/inventory/yarn-lots");
  }

  async createYarnLot(payload) {
    return await this.request("/inventory/yarn-lots", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  }

  async getSuppliers() {
    return await this.request("/purchases/suppliers");
  }

  async createSupplier(payload) {
    return await this.request("/purchases/suppliers", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  }

  async getPurchases() {
    return await this.request("/purchases/invoices");
  }

  async createPurchase(payload) {
    return await this.request("/purchases/invoices", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  }

  async postPurchase(invoiceId) {
    return await this.request(`/purchases/invoices/${invoiceId}/post`, {
      method: "POST"
    });
  }

  async getInventoryJournal(limit = 40) {
    return await this.request(`/inventory/journal?limit=${limit}`);
  }

  async getInventoryValuation() {
    return await this.request("/inventory/valuation");
  }

  // Sales & Rebates
  async createSale(payload) {
    return await this.request("/sales/transactions", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  }

  async getSaleBill(saleId) {
    return await this.request(`/sales/bills/${saleId}`);
  }

  async getRecentSales() {
    return await this.request("/sales/recent");
  }

  // Statutory Reports
  async getDaybook(date = "") {
    const q = date ? `?date=${encodeURIComponent(date)}` : "";
    return await this.request(`/reports/daybook${q}`);
  }

  async getWeaverMaterialRegister() {
    return await this.request("/reports/weaver-material");
  }

  async getWeaverWagesRegister() {
    return await this.request("/reports/weaver-wages");
  }

  async getRebateClaimsSchedule() {
    return await this.request("/reports/rebate-claims");
  }

  // Cloud & Firebase Services
  async getFirebaseStatus() {
    return await this.request("/system/firebase-status");
  }

  async syncTenantToFirebase() {
    return await this.request("/system/firebase-sync", {
      method: "POST"
    });
  }

  async firebaseLogin(idToken, tenantSlug = null, tenantId = null) {
    const data = await this.request("/auth/firebase-login", {
      method: "POST",
      body: JSON.stringify({ id_token: idToken, tenant_slug: tenantSlug, tenant_id: tenantId })
    });
    this.setSession(data.access_token, data);
    return data;
  }

  async getFirebaseCustomToken() {
    return await this.request("/auth/firebase-token");
  }
}

const api = new ApiClient();

