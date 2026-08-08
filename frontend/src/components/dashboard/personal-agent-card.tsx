import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { Agent } from "@/lib/types";

export function PersonalAgentCard({ agent }: { agent: Agent }) {
  return (
    <Card className="agent-card">
      <div className="agent-card__top">
        <div>
          <Badge>Personal Agent</Badge>
          <h2 className="agent-card__name">{agent.name}</h2>
          <p className="agent-card__meta">
            Agent ID: <strong>{agent.slug.replaceAll("-", "_")}_8F29</strong>
          </p>
        </div>
        <Badge className="tag--soft">{agent.status === "active" ? "Active" : agent.status}</Badge>
      </div>

      <p className="agent-card__body">{agent.summary}</p>

      <div className="tag-row">
        {agent.capabilities.map((capability) => (
          <Badge key={capability}>{capability}</Badge>
        ))}
      </div>

      <div className="divider" />

      <div className="panel__header">
        <div>
          <p className="agent-card__meta">Trust score</p>
          <p className="metric__value">{agent.trustScore.toFixed(1)}</p>
        </div>
        <Button href={`/agents/${agent.slug}`} variant="primary">
          Open agent
        </Button>
      </div>
    </Card>
  );
}

