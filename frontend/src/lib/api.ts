import type { Agent, DashboardSnapshot } from "@/lib/types";
import { mockAgents, mockDashboard } from "@/lib/mock-data";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

async function safeJson<T>(response: Response): Promise<T | null> {
  if (!response.ok) {
    return null;
  }

  return (await response.json()) as T;
}

export async function getDashboardSnapshot(): Promise<DashboardSnapshot> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/dashboard/`, {
      next: { revalidate: 30 },
    });

    const data = await safeJson<DashboardSnapshot>(response);
    return data ?? mockDashboard;
  } catch {
    return mockDashboard;
  }
}

export async function getAgents(): Promise<Agent[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/agents/`, {
      next: { revalidate: 30 },
    });

    const data = await safeJson<Agent[]>(response);
    return data ?? mockAgents;
  } catch {
    return mockAgents;
  }
}

export async function getAgentBySlug(slug: string): Promise<Agent | null> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/agents/${slug}/`, {
      next: { revalidate: 30 },
    });

    const data = await safeJson<Agent>(response);
    if (data) {
      return data;
    }
  } catch {
    // fall back to local data below
  }

  return mockAgents.find((agent) => agent.slug === slug) ?? null;
}

