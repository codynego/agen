"use client";

import { useMemo, useState } from "react";

import { AgentCard } from "@/components/discovery/agent-card";
import type { Agent } from "@/lib/types";

const categories = ["All", "Hospitality", "Payments", "Hardware", "Commerce", "Finance"];

type SearchPanelProps = {
  agents: Agent[];
};

export function SearchPanel({ agents }: SearchPanelProps) {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("All");
  const [verifiedOnly, setVerifiedOnly] = useState(true);

  const filteredAgents = useMemo(() => {
    return agents.filter((agent) => {
      const matchesQuery =
        query.trim().length === 0 ||
        [agent.name, agent.category, agent.location, agent.summary, agent.capabilities.join(" ")]
          .join(" ")
          .toLowerCase()
          .includes(query.toLowerCase());
      const matchesCategory = category === "All" || agent.category === category;
      const matchesVerified = !verifiedOnly || agent.verified;

      return matchesQuery && matchesCategory && matchesVerified;
    });
  }, [agents, category, query, verifiedOnly]);

  return (
    <div className="page-grid">
      <div className="search-bar">
        <span aria-hidden="true">⌕</span>
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search agents by capability, industry, or task..."
          aria-label="Search agents"
        />
      </div>

      <div className="filters">
        <select value={category} onChange={(event) => setCategory(event.target.value)} aria-label="Filter by category">
          {categories.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>
        <button type="button" onClick={() => setVerifiedOnly((current) => !current)}>
          {verifiedOnly ? "Verified only" : "All agents"}
        </button>
      </div>

      <div className="grid grid--cards">
        {filteredAgents.map((agent) => (
          <AgentCard key={agent.slug} agent={agent} />
        ))}
      </div>
    </div>
  );
}

