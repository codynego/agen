import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { Agent } from "@/lib/types";

export function AgentCard({ agent }: { agent: Agent }) {
  return (
    <Card className="agent-card">
      <div className="agent-card__top">
        <div>
          <Badge>{agent.verified ? "Verified" : "Unverified"}</Badge>
          <h3 className="agent-card__name">{agent.name}</h3>
          <p className="agent-card__meta">
            {agent.category} · {agent.location}
          </p>
        </div>
        <Badge className="tag--soft">Trust {agent.trustScore.toFixed(1)}</Badge>
      </div>

      <p className="agent-card__body">{agent.summary}</p>

      <div className="tag-row">
        {agent.capabilities.map((capability) => (
          <Badge key={capability}>{capability}</Badge>
        ))}
      </div>

      <div className="divider" />

      <p className="agent-card__meta">
        Endpoint:{" "}
        <a href={`https://${agent.endpoint}`} target="_blank" rel="noreferrer">
          {agent.endpoint}
        </a>
      </p>

      <div className="button-row">
        <Button href={`/agents/${agent.slug}`} variant="primary">
          View agent
        </Button>
        <Button href={`/agents/${agent.slug}`} variant="secondary">
          Connect
        </Button>
      </div>
    </Card>
  );
}
