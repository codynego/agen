const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export type AuthUser = {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  display_name: string;
};

export type AuthSession = {
  user: AuthUser;
  personal_agent: {
    agent_id: string;
    name: string;
    trust_score: string;
    trust_level: string;
  };
};

export type BusinessAgentInput = {
  name: string;
  company_name: string;
  category: string;
  hosting_type: "managed" | "external";
  endpoint?: string;
  summary?: string;
  capabilities: string[];
};

export type BusinessAgent = BusinessAgentInput & {
  agent_id: string;
  status: string;
  trust_score: string;
};

export class ApiError extends Error {
  constructor(message: string, public status: number, public fields?: Record<string, string[]>) {
    super(message);
  }
}

async function readError(response: Response): Promise<ApiError> {
  const data = await response.json().catch(() => null) as Record<string, unknown> | null;
  const detail = typeof data?.detail === "string" ? data.detail : "Something went wrong. Please try again.";
  return new ApiError(detail, response.status, data as Record<string, string[]> | undefined);
}

async function csrfToken(): Promise<string> {
  const response = await fetch(`${API_BASE_URL}/api/auth/csrf/`, { credentials: "include" });
  if (!response.ok) throw await readError(response);
  const data = await response.json() as { csrf_token: string };
  return data.csrf_token;
}

async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const method = options.method?.toUpperCase() || "GET";
  const headers = new Headers(options.headers);
  if (options.body) headers.set("Content-Type", "application/json");
  if (!["GET", "HEAD", "OPTIONS"].includes(method)) headers.set("X-CSRFToken", await csrfToken());

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
    credentials: "include",
  });
  if (!response.ok) throw await readError(response);
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export function registerAccount(input: { name: string; email: string; password: string }) {
  return apiRequest<AuthSession>("/api/auth/register/", { method: "POST", body: JSON.stringify(input) });
}

export function loginAccount(input: { email: string; password: string }) {
  return apiRequest<AuthSession>("/api/auth/login/", { method: "POST", body: JSON.stringify(input) });
}

export function getAuthSession() {
  return apiRequest<AuthSession>("/api/auth/me/");
}

export function logoutAccount() {
  return apiRequest<void>("/api/auth/logout/", { method: "POST", body: "{}" });
}

export function createBusinessAgent(input: BusinessAgentInput) {
  return apiRequest<BusinessAgent>("/api/agents/business/", { method: "POST", body: JSON.stringify(input) });
}
