import { Button } from "@/components/ui/button";

export function Hero() {
  return (
    <section className="hero">
      <div>
        <span className="eyebrow">Autonomous Personal Agent Platform</span>
        <h1 className="heading heading--hero">The agent that works for you.</h1>
        <p className="subhead">
          Abednego Agent learns your preferences, coordinates with trusted business agents, and executes tasks with
          a strict permission model.
        </p>
        <div className="button-row">
          <Button href="/dashboard" variant="primary">
            Open dashboard
          </Button>
          <Button href="/discover" variant="secondary">
            Explore agents
          </Button>
        </div>
      </div>

      <div className="panel panel--padded">
        <div className="panel__header">
          <div>
            <p className="agent-card__meta">Current focus</p>
            <h2 className="section__title">Personal autonomy with controlled delegation.</h2>
          </div>
          <span className="tag">MVP</span>
        </div>
        <p className="section__meta">
          The first release centers on the supply side: a personal agent that can search, compare, negotiate, and
          connect to verified business agents.
        </p>
        <div className="divider" />
        <div className="tag-row" style={{ marginTop: 16 }}>
          <span className="tag">Preference learning</span>
          <span className="tag">Trust scoring</span>
          <span className="tag">Agent discovery</span>
          <span className="tag">Approval gates</span>
        </div>
      </div>
    </section>
  );
}

