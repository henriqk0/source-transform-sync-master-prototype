const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  detail?: unknown;

  constructor(status: number, detail?: unknown) {
    super(typeof detail === "string" ? detail : `Request failed (${status})`);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

function authHeaders(): Record<string, string> {
  const token =
    typeof window !== "undefined" ? window.localStorage.getItem("portal_token") : null;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...authHeaders(),
        ...(options.headers ?? {}),
      },
    });
  } catch {
    throw new ApiError(0, "Could not reach the server. Please try again.");
  }

  if (!response.ok) {
    let detail: unknown = undefined;
    try {
      const body = await response.json();
      detail = body?.detail ?? body;
    } catch {
      detail = undefined;
    }
    throw new ApiError(response.status, detail);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
  patch: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PATCH", body: JSON.stringify(body) }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};

export type ProfessorListItem = {
  id: number;
  name: string;
  affiliation: string | null;
};

export type ProfessorList = {
  items: ProfessorListItem[];
  total: number;
  page: number;
  page_size: number;
};

export type Profile = {
  id: number;
  name: string;
  affiliation: string | null;
  resume: string | null;
  current_projects: { id: number; name: string; status: string }[];
  article_counts_by_year: { year: number; count: number }[];
  locations: { id: number; name: string; type: string }[];
  articles: { id: number; title: string; year: number; type: string | null; doi: string | null }[];
  articles_total: number;
  article_page: number;
  article_page_size: number;
};