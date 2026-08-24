// ============================================================
// JiuWei CRM — Unified API client
// ============================================================

import type { ApiResponse } from "@/types";

// v0.1.2: 使用 ?? 使空字符串生效，前端通过 nginx 统一入口走相对路径访问 API
const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

// ------------------------------------------------------------------
// Helpers
// ------------------------------------------------------------------

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token");
}

function clearAuth(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem("access_token");
  localStorage.removeItem("user");
}

// ------------------------------------------------------------------
// Core fetch wrapper
// ------------------------------------------------------------------

class ApiError extends Error {
  constructor(
    public status: number,
    public errorCode: string,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  // Don't set Content-Type for FormData (browser sets it with boundary)
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  const url = `${API_BASE_URL}${path}`;

  let res: Response;
  try {
    res = await fetch(url, { ...options, headers });
  } catch {
    throw new ApiError(0, "NETWORK_ERROR", "网络连接失败，请检查后端服务是否启动");
  }

  // Handle 401 — clear auth and redirect to login
  if (res.status === 401) {
    clearAuth();
    if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
      window.location.href = "/login";
    }
    throw new ApiError(401, "UNAUTHORIZED", "登录已过期，请重新登录");
  }

  let body: ApiResponse<T>;
  try {
    body = await res.json();
  } catch {
    throw new ApiError(res.status, "PARSE_ERROR", `服务器返回异常 (${res.status})`);
  }

  if (!body.success) {
    throw new ApiError(
      res.status,
      body.error_code || "UNKNOWN",
      body.message || "请求失败",
    );
  }

  return body.data;
}

// ------------------------------------------------------------------
// Auth API
// ------------------------------------------------------------------

export const authApi = {
  login: (username: string, password: string) =>
    request<{
      access_token: string;
      token_type: string;
      user: { id: number; username: string; real_name: string; role: string };
    }>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),

  me: () =>
    request<{
      id: number;
      username: string;
      real_name: string;
      role: string;
      phone: string | null;
      email: string | null;
    }>("/api/v1/auth/me"),
};

// ------------------------------------------------------------------
// Lead API
// ------------------------------------------------------------------

export const leadApi = {
  list: (params?: {
    keyword?: string;
    status?: string;
    source_id?: number;
    owner_id?: number;
    page?: number;
    page_size?: number;
  }) => {
    const searchParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== "") {
          searchParams.set(key, String(value));
        }
      });
    }
    const qs = searchParams.toString();
    return request<{
      items: import("@/types").LeadListItem[];
      total: number;
      page: number;
      page_size: number;
    }>(`/api/v1/leads${qs ? `?${qs}` : ""}`);
  },

  create: (data: import("@/types").LeadCreate) =>
    request<{ id: number }>("/api/v1/leads", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  get: (id: number) =>
    request<import("@/types").LeadDetail>(`/api/v1/leads/${id}`),

  update: (id: number, data: import("@/types").LeadUpdate) =>
    request<{ id: number }>(`/api/v1/leads/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  delete: (id: number) =>
    request<null>(`/api/v1/leads/${id}`, { method: "DELETE" }),
};

// ------------------------------------------------------------------
// FollowUp API
// ------------------------------------------------------------------

export const followUpApi = {
  list: (leadId: number) =>
    request<import("@/types").FollowUpItem[]>(
      `/api/v1/leads/${leadId}/followups`,
    ),

  create: (leadId: number, data: import("@/types").FollowUpCreate) =>
    request<{ id: number }>(`/api/v1/leads/${leadId}/followups`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  delete: (followupId: number) =>
    request<null>(`/api/v1/followups/${followupId}`, { method: "DELETE" }),
};

// ------------------------------------------------------------------
// Resume Import API
// ------------------------------------------------------------------

export const resumeImportApi = {
  upload: (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return request<import("@/types").ResumeImportResult>(
      "/api/v1/resume-imports",
      {
        method: "POST",
        body: formData,
      },
    );
  },

  // v0.2.1 — batch import
  limits: () =>
    request<import("@/types").BatchLimits>(
      "/api/v1/resume-imports/batch-limits",
    ),

  uploadBatch: (files: File[]) => {
    const formData = new FormData();
    files.forEach((file) => formData.append("files", file));
    return request<import("@/types").BatchUploadResult>(
      "/api/v1/resume-imports/batch",
      {
        method: "POST",
        body: formData,
      },
    );
  },

  getBatch: (batchId: number) =>
    request<import("@/types").BatchDetail>(
      `/api/v1/resume-imports/batches/${batchId}`,
    ),

  confirmBatch: (
    batchId: number,
    data?: import("@/types").BatchConfirmRequest,
  ) =>
    request<import("@/types").BatchConfirmResult>(
      `/api/v1/resume-imports/batches/${batchId}/confirm`,
      {
        method: "POST",
        body: JSON.stringify(data ?? {}),
      },
    ),
};

// ------------------------------------------------------------------
// Lead Draft API
// ------------------------------------------------------------------

export const leadDraftApi = {
  get: (draftId: number) =>
    request<import("@/types").LeadDraft>(`/api/v1/lead-drafts/${draftId}`),

  update: (draftId: number, data: import("@/types").LeadDraftUpdate) =>
    request<import("@/types").LeadDraft>(`/api/v1/lead-drafts/${draftId}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  confirm: (draftId: number, data: import("@/types").LeadDraftConfirm) =>
    request<{ lead_id: number }>(`/api/v1/lead-drafts/${draftId}/confirm`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  discard: (draftId: number) =>
    request<null>(`/api/v1/lead-drafts/${draftId}/discard`, {
      method: "POST",
    }),
};

// ------------------------------------------------------------------
// Dashboard API
// ------------------------------------------------------------------

export const dashboardApi = {
  summary: () =>
    request<import("@/types").DashboardSummary>("/api/v1/dashboard/summary"),

  todayFollowups: () =>
    request<import("@/types").TodayFollowUpItem[]>(
      "/api/v1/dashboard/today-followups",
    ),

  recentLeads: () =>
    request<import("@/types").RecentLeadItem[]>(
      "/api/v1/dashboard/recent-leads",
    ),
};

// ------------------------------------------------------------------
// Config API
// ------------------------------------------------------------------

export const configApi = {
  leadSources: () =>
    request<import("@/types").LeadSource[]>("/api/v1/config/lead-sources"),

  courses: () =>
    request<import("@/types").Course[]>("/api/v1/config/courses"),
};

export { ApiError };

// ------------------------------------------------------------------
// User API
// ------------------------------------------------------------------

export const userApi = {
  list: () =>
    request<import("@/types").UserItem[]>("/api/v1/users"),

  create: (data: import("@/types").UserCreate) =>
    request<import("@/types").UserItem>("/api/v1/users", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  update: (id: number, data: import("@/types").UserUpdate) =>
    request<import("@/types").UserItem>(`/api/v1/users/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  resetPassword: (id: number) =>
    request<null>(`/api/v1/users/${id}/reset-password`, {
      method: "PUT",
    }),

  changePassword: (data: import("@/types").ChangePasswordRequest) =>
    request<null>("/api/v1/auth/change-password", {
      method: "PUT",
      body: JSON.stringify(data),
    }),
};
