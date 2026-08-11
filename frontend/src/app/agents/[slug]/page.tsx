import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { PublicAgentProfile } from "@/components/public/public-agent-profile";
import type { PublicBusinessAgent } from "@/lib/client-api";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

async function loadAgent(handle: string): Promise<PublicBusinessAgent | null> {
  const response = await fetch(`${API_BASE_URL}/api/public/agents/${encodeURIComponent(handle)}/`, { cache: "no-store" });
  if (!response.ok) return null;
  return response.json();
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params;
  const agent = await loadAgent(slug);
  if (!agent) return { title: "Agent not available | Agen" };
  return {
    title: `${agent.name} by ${agent.company_name} | Agen`,
    description: agent.tagline || agent.description,
    alternates: { canonical: agent.canonical_url },
    openGraph: {
      title: `${agent.name} by ${agent.company_name}`,
      description: agent.tagline || agent.description,
      url: agent.canonical_url,
      images: agent.cover_url || agent.logo_url ? [{ url: agent.cover_url || agent.logo_url }] : [],
    },
  };
}

export default async function AgentPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const agent = await loadAgent(slug);
  if (!agent) notFound();
  return <PublicAgentProfile agent={agent} apiBaseUrl={API_BASE_URL} />;
}
