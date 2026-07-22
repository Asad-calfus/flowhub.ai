import type {
  AnalysisMethod,
  AnalysisOut,
  BatchAnalysisResponse,
  ContextMatchSummary,
  CostEstimate,
  FeedbackListFilters,
  FeedbackOut,
  HealthStatus,
  ImportSummary,
  Page,
  RecomputeThemesResponse,
  ReportGenerationRequest,
  ReportOut,
  ReportSummaryOut,
  RetrievalBatchResponse,
  SimilarFeedbackOut,
  ThemeDetailOut,
  ThemeOut,
} from "./types";
import { DEMO_WORKSPACE_ID, getStoredWorkspaceId } from "./workspace";

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8001/api/v1";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function toResult<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ? String(body.detail) : detail;
    } catch {
      // response had no JSON body - keep statusText
    }
    throw new ApiError(detail, res.status);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

function workspaceHeader(): Record<string, string> {
  return { "X-Workspace-Id": getStoredWorkspaceId() ?? DEMO_WORKSPACE_ID };
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE_URL}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...workspaceHeader(), ...(init?.headers || {}) },
    });
  } catch {
    throw new ApiError("Could not reach the backend API. Is it running?", 0);
  }
  return toResult<T>(res);
}

/** Like request(), but for multipart/form-data bodies - never set Content-Type manually,
 * the browser must supply its own boundary. */
async function requestForm<T>(path: string, form: FormData): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE_URL}${path}`, { method: "POST", body: form, headers: workspaceHeader() });
  } catch {
    throw new ApiError("Could not reach the backend API. Is it running?", 0);
  }
  return toResult<T>(res);
}

function queryString(params: object): string {
  const usp = new URLSearchParams();
  for (const [key, value] of Object.entries(params as Record<string, unknown>)) {
    if (value !== undefined && value !== null && value !== "") usp.set(key, String(value));
  }
  const s = usp.toString();
  return s ? `?${s}` : "";
}

export const api = {
  status: () => request<HealthStatus>("/status"),

  listFeedback: (filters: FeedbackListFilters = {}) =>
    request<Page<FeedbackOut>>(`/feedback${queryString(filters)}`),

  getFeedback: (id: string) => request<FeedbackOut>(`/feedback/${id}`),

  importFeedbackCsv: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return requestForm<ImportSummary>("/feedback/import", form);
  },

  getSimilarFeedback: (id: string, topK = 5) =>
    request<SimilarFeedbackOut[]>(`/feedback/${id}/similar${queryString({ top_k: topK })}`),

  getContextMatches: (id: string, topK = 5) =>
    request<ContextMatchSummary>(`/feedback/${id}/context-matches${queryString({ top_k: topK })}`),

  getAnalysis: (feedbackId: string) => request<AnalysisOut>(`/analysis/${feedbackId}`),

  listThemes: (page = 1, pageSize = 50) =>
    request<Page<ThemeOut>>(`/themes${queryString({ page, page_size: pageSize })}`),

  getTheme: (id: string) => request<ThemeDetailOut>(`/themes/${id}`),

  getThemeFeedback: (id: string, page = 1, pageSize = 20) =>
    request<Page<FeedbackOut>>(`/themes/${id}/feedback${queryString({ page, page_size: pageSize })}`),

  listReports: (page = 1, pageSize = 20) =>
    request<Page<ReportSummaryOut>>(`/reports${queryString({ page, page_size: pageSize })}`),

  getReport: (id: string) => request<ReportOut>(`/reports/${id}`),

  generateReport: (payload: ReportGenerationRequest) =>
    request<ReportOut>("/reports/weekly", { method: "POST", body: JSON.stringify(payload) }),

  runBatchAnalysis: (method: AnalysisMethod = "baseline", live = false) =>
    request<BatchAnalysisResponse>("/analysis/batch", { method: "POST", body: JSON.stringify({ method, live }) }),

  estimateAnalysisCost: () => request<CostEstimate>("/analysis/estimate"),

  runBatchRetrieval: () =>
    request<RetrievalBatchResponse>("/feedback/retrieval/batch", { method: "POST", body: JSON.stringify({}) }),

  recomputeThemes: () => request<RecomputeThemesResponse>("/themes/recompute", { method: "POST" }),
};

export function backendStatusUrl(): string {
  return BASE_URL.replace(/\/api\/v1\/?$/, "") + "/health";
}

export async function checkBackendHealth(): Promise<boolean> {
  try {
    const res = await fetch(backendStatusUrl(), { cache: "no-store" });
    return res.ok;
  } catch {
    return false;
  }
}
