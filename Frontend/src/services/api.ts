// Token state management
let authToken: string | null =
  typeof window !== "undefined" ? localStorage.getItem("auth_token") : null;

export const setAuthToken = (token: string | null): void => {
  authToken = token;
  if (typeof window !== "undefined") {
    if (token) {
      localStorage.setItem("auth_token", token);
    } else {
      localStorage.removeItem("auth_token");
    }
  }
};

export const getAuthToken = (): string | null => authToken;

export interface CreateProductPayload {
  sku: string;
  name: string;
  description?: string;
  unit_price: number;
  quantity: number;
  safety_stock_threshold: number;
  category_id: number;
  supplier_ids?: number[];
}

export interface AdjustStockPayload {
  delta?: number;
  target_quantity?: number;
  reason: string;
}

export interface ProductQueryParams {
  search?: string;
  category_id?: number | string;
  low_stock?: boolean | string;
  page?: number | string;
  limit?: number | string;
  [key: string]: any;
}

/**
 * Generic fetch wrapper for communicating with the Flask backend
 */
async function request<T = any>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((options.headers as Record<string, string>) || {}),
  };

  if (authToken && !headers["Authorization"]) {
    headers["Authorization"] = `Bearer ${authToken}`;
  }

  const response = await fetch(endpoint, {
    ...options,
    headers,
  });

  // Handle token expiration
  if (response.status === 401) {
    setAuthToken(null);
  }

  // Safely parse JSON or handle plain text / HTML error responses
 const json = await response.json().catch(() => null);

 if (!response.ok || !json.success) {
    const errorMsg = json?.error?.message || `Request failed with status ${response.status}`;
    const error = new Error(errorMsg) as Error & { code?: string; details?: any; status?: number };
    error.code = json?.error?.code || "UNKNOWN_ERROR";
    error.details = json?.error?.details || null;
    error.status = response.status;
    throw error;
  }

  // Return json.data if present, otherwise fall back to json directly
  return (json?.data !== undefined ? json.data : json) as T;
}

export const api = {
  // Auth
  register: (payload: { username: string; email: string; password: string; role?: string }) =>
    request("/api/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  login: (payload: { identifier: string; password: string }) =>
    request("/api/auth/login", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getMe: () => request("/api/auth/me"),

  // Products
  getProducts: (params: ProductQueryParams = {}) => {
    const query = new URLSearchParams();
    if (params.search) query.append("search", params.search);
    if (params.category_id) query.append("category_id", String(params.category_id));
    if (params.low_stock) query.append("low_stock", "true");
    if (params.page) query.append("page", String(params.page));
    if (params.limit) query.append("limit", String(params.limit));
    const qs = query.toString();
    return request(`/api/products${qs ? `?${qs}` : ""}`);
  },

  getProduct: (id: number) => request(`/api/products/${id}`),

  createProduct: (payload: CreateProductPayload) =>
    request("/api/products", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  deleteProduct: (id: number) =>
    request(`/api/products/${id}`, {
      method: "DELETE",
    }),

  adjustStock: (id: number, payload: AdjustStockPayload) =>
    request(`/api/products/${id}/stock`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),

  getProductHistory: (id: number) => request(`/api/products/${id}/history`),

  // Categories & Suppliers
  // Categories
  getCategories: () => request("/api/categories"),
  createCategory: (payload: { name: string; description?: string }) =>
    request("/api/categories", { method: "POST", body: JSON.stringify(payload) }),
  deleteCategory: (id: number) =>
    request(`/api/categories/${id}`, { method: "DELETE" }),

  // Suppliers
  getSuppliers: () => request("/api/suppliers"),
  createSupplier: (payload: { name: string; contact_email: string; phone?: string; address?: string }) =>
    request("/api/suppliers", { method: "POST", body: JSON.stringify(payload) }),
  deleteSupplier: (id: number) =>
    request(`/api/suppliers/${id}`, { method: "DELETE" }),

  // AI Features
  getInsights: () => request("/api/ai/insights"),

  naturalSearch: (query: string) =>
    request("/api/ai/search", {
      method: "POST",
      body: JSON.stringify({ query }),
    }),

  chat: (messages: { role: string; content: string }[]) =>
    request("/api/ai/chat", {
      method: "POST",
      body: JSON.stringify({ messages }),
    }),
};