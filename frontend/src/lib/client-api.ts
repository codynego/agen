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
  onboarding_completed: boolean;
  approval_mode: ApprovalMode;
  personal_agent: {
    agent_id: string;
    network_handle: string;
    name: string;
    trust_score: string;
    trust_level: string;
  };
};

export type ApprovalMode = "always_ask" | "balanced" | "auto_connect";

export type OnboardingInput = {
  agent_name: string;
  goals: string[];
  approval_mode: ApprovalMode;
  integrations: string[];
};

export type OnboardingStatus = OnboardingInput & {
  onboarding_completed: boolean;
  agent_id: string;
  network_handle: string;
  trust_score: string;
  trust_level: string;
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
  network_handle: string;
  status: string;
  trust_score: string;
  verified: boolean;
};

export type ManagedAgentSetup = {
  agent: {
    agent_id: string; network_handle: string; name: string; company_name: string; category: string;
    summary: string; status: string; verified: boolean; trust_score: string; capabilities: string[];
    allowed_actions: string[]; blocked_actions: string[];
  };
  profile: {
    template_key: string; verification_status: "unsubmitted" | "pending" | "verified" | "rejected";
    verification_level: "none" | "basic" | "business" | "enhanced";
    requested_verification_level: "basic" | "business" | "enhanced";
    verification_method: "none" | "domain_email" | "manual_review" | "development";
    business_domain: string; country: string; registration_number: string; business_phone: string;
    supporting_url: string; evidence_notes: string; instructions: string; tone: string; human_handoff: string;
  };
  knowledge: Array<{ source_id: string; kind: string; title: string; content: string; source_url: string; active: boolean }>;
  catalog: Array<{ item_id: string; name: string; sku: string; description: string; price: string | null; currency: string; availability: string; active: boolean }>;
  tools: Array<{ connection_id: string; provider: string; display_name: string; status: string; scopes: string[]; has_secret_config: boolean }>;
  tests: Array<{ run_id: string; prompt: string; response: string; status: string; matched_sources: string[]; created_at: string }>;
  audit: Array<{ event_id: string; action: string; detail: string; created_at: string }>;
  templates: Array<{ key: string; name: string; description: string; capabilities: string[]; instructions: string }>;
  development_verification_enabled: boolean;
  readiness: { ready: boolean; checks: Record<string, boolean>; required_verification_level: "basic" | "business" | "enhanced"; current_verification_level: "none" | "basic" | "business" | "enhanced" };
};

export type ResolverCandidate = {
  rank: number;
  match_score: string;
  agent_id: string;
  network_handle: string;
  name: string;
  category: string;
  location: string;
  capabilities: string[];
  trust_score: string;
  trust_level: string;
  verified: boolean;
  reasons: string[];
};

export type ResolverTask = {
  task_id: string;
  request_text: string;
  agent_response: string;
  discovery_spec: { capabilities: string[]; location?: string };
  status: string;
  risk_level: string;
  candidates: ResolverCandidate[];
};

export type AgentConnection = {
  connection_id: string;
  task_id: string;
  status: string;
  auto_approved: boolean;
  requested_scopes: string[];
  provider: { agent_id: string; network_handle: string; name: string; capabilities: string[]; endpoint?: string };
  data_grant: { grant_id: string; scopes: string[]; expires_at: string; active: boolean } | null;
};

export type ConversationMessage = {
  message_id: string;
  role: "user" | "agent" | "system";
  sequence: number;
  content: string;
  task_id: string | null;
  created_at: string;
};

export type Conversation = {
  conversation_id: string;
  title: string;
  status: "active" | "archived";
  retention_policy: "session" | "30_days" | "forever";
  expires_at: string | null;
  last_message_at: string | null;
  message_count: number;
  latest_message: string;
  created_at: string;
};

export type ConversationDetail = Conversation & { messages: ConversationMessage[] };

export type ConversationSendResult = {
  user_message: ConversationMessage;
  agent_message: ConversationMessage;
  task: ResolverTask;
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

export type LoginCodeChallenge = {
  detail: string;
  challenge_id: string;
  expires_in_seconds: number;
};

export function requestLoginCode(input: { email: string; name?: string }) {
  return apiRequest<LoginCodeChallenge>("/api/auth/request-code/", { method: "POST", body: JSON.stringify(input) });
}

export function verifyLoginCode(input: { challenge_id: string; code: string }) {
  return apiRequest<AuthSession>("/api/auth/verify-code/", { method: "POST", body: JSON.stringify(input) });
}

export function getAuthSession() {
  return apiRequest<AuthSession>("/api/auth/me/");
}

export function logoutAccount() {
  return apiRequest<void>("/api/auth/logout/", { method: "POST", body: "{}" });
}

export function getOnboardingStatus() {
  return apiRequest<OnboardingStatus>("/api/profile/onboarding/");
}

export function completeOnboarding(input: OnboardingInput) {
  return apiRequest<OnboardingStatus>("/api/profile/onboarding/", { method: "POST", body: JSON.stringify(input) });
}

export function createBusinessAgent(input: BusinessAgentInput) {
  return apiRequest<BusinessAgent>("/api/agents/business/", { method: "POST", body: JSON.stringify(input) });
}

export function listBusinessAgents() {
  return apiRequest<BusinessAgent[]>("/api/agents/business/");
}

export function getManagedAgentSetup(agentId: string) {
  return apiRequest<ManagedAgentSetup>(`/api/agents/business/${agentId}/setup/`);
}

export function updateManagedAgent(agentId: string, input: Record<string, unknown>) {
  return apiRequest<ManagedAgentSetup>(`/api/agents/business/${agentId}/setup/`, { method: "PATCH", body: JSON.stringify(input) });
}

export function applyManagedTemplate(agentId: string, templateKey: string) {
  return apiRequest<ManagedAgentSetup>(`/api/agents/business/${agentId}/template/${templateKey}/`, { method: "POST", body: "{}" });
}

export function submitManagedVerification(agentId: string, input: Record<string, unknown>) {
  return apiRequest<ManagedAgentSetup>(`/api/agents/business/${agentId}/verification/`, { method: "POST", body: JSON.stringify(input) });
}

export function addManagedKnowledge(agentId: string, input: { kind: string; title: string; content: string; source_url?: string }) {
  return apiRequest<ManagedAgentSetup["knowledge"][number]>(`/api/agents/business/${agentId}/knowledge/`, { method: "POST", body: JSON.stringify(input) });
}

export function deleteManagedKnowledge(agentId: string, sourceId: string) {
  return apiRequest<void>(`/api/agents/business/${agentId}/knowledge/${sourceId}/`, { method: "DELETE", body: "{}" });
}

export function addManagedCatalogItem(agentId: string, input: Record<string, unknown>) {
  return apiRequest<ManagedAgentSetup["catalog"][number]>(`/api/agents/business/${agentId}/catalog/`, { method: "POST", body: JSON.stringify(input) });
}

export function deleteManagedCatalogItem(agentId: string, itemId: string) {
  return apiRequest<void>(`/api/agents/business/${agentId}/catalog/${itemId}/`, { method: "DELETE", body: "{}" });
}

export function connectManagedTool(agentId: string, input: Record<string, unknown>) {
  return apiRequest<ManagedAgentSetup["tools"][number]>(`/api/agents/business/${agentId}/tools/`, { method: "POST", body: JSON.stringify(input) });
}

export function disconnectManagedTool(agentId: string, connectionId: string) {
  return apiRequest<void>(`/api/agents/business/${agentId}/tools/${connectionId}/`, { method: "DELETE", body: "{}" });
}

export function testManagedAgent(agentId: string, prompt: string) {
  return apiRequest<ManagedAgentSetup["tests"][number]>(`/api/agents/business/${agentId}/sandbox/`, { method: "POST", body: JSON.stringify({ prompt }) });
}

export function activateManagedAgent(agentId: string) {
  return apiRequest<ManagedAgentSetup>(`/api/agents/business/${agentId}/activate/`, { method: "POST", body: "{}" });
}

export function discoverAgents(request_text: string) {
  return apiRequest<ResolverTask>("/api/resolver/discover/", { method: "POST", body: JSON.stringify({ request_text }) });
}

export function getResolverTask(taskId: string) {
  return apiRequest<ResolverTask>(`/api/resolver/tasks/${taskId}/`);
}

export function listConversations() {
  return apiRequest<Conversation[]>("/api/conversations/");
}

export function createConversation(retention_policy: Conversation["retention_policy"] = "30_days") {
  return apiRequest<Conversation>("/api/conversations/", {
    method: "POST",
    body: JSON.stringify({ retention_policy }),
  });
}

export function getConversation(conversationId: string) {
  return apiRequest<ConversationDetail>(`/api/conversations/${conversationId}/`);
}

export function sendConversationMessage(conversationId: string, content: string) {
  return apiRequest<ConversationSendResult>(`/api/conversations/${conversationId}/messages/`, {
    method: "POST",
    body: JSON.stringify({ content }),
  });
}

export function updateConversation(conversationId: string, input: { title?: string; status?: "active" | "archived" }) {
  return apiRequest<Conversation>(`/api/conversations/${conversationId}/`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

export function deleteConversation(conversationId: string) {
  return apiRequest<void>(`/api/conversations/${conversationId}/`, { method: "DELETE", body: "{}" });
}

export function requestAgentConnection(taskId: string, candidateHandle: string, scopes: string[]) {
  return apiRequest<AgentConnection>(`/api/resolver/tasks/${taskId}/connect/`, {
    method: "POST",
    body: JSON.stringify({ candidate_handle: candidateHandle, scopes }),
  });
}

export function approveAgentConnection(connectionId: string, scopes: string[]) {
  return apiRequest<AgentConnection>(`/api/resolver/connections/${connectionId}/approve/`, {
    method: "POST",
    body: JSON.stringify({ scopes }),
  });
}
