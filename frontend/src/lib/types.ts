export type AgentKind = "personal" | "business";

export type Agent = {
  id: number;
  name: string;
  slug: string;
  kind: AgentKind;
  status: "draft" | "active" | "paused";
  category: string;
  companyName: string;
  location: string;
  endpoint: string;
  summary: string;
  trustScore: number;
  verified: boolean;
  online: boolean;
  capabilities: string[];
  allowedActions: string[];
  blockedActions: string[];
};

export type DashboardSnapshot = {
  greeting: string;
  metrics: {
    my_agents: number;
    connected_agents: number;
    network_requests: number;
    successful_transactions: number;
  };
  personal_agent: Agent | null;
  featured_agents: Agent[];
  recent_activity: Array<{
    title: string;
    detail: string;
    created_at: string;
    agent__name: string;
    agent__slug: string;
  }>;
};

