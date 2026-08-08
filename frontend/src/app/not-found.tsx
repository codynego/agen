import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";

export default function NotFoundPage() {
  return (
    <AppShell>
      <section className="section">
        <span className="eyebrow">Not found</span>
        <h1 className="heading heading--hero" style={{ maxWidth: "10ch", fontSize: "clamp(2.6rem, 6vw, 5rem)" }}>
          This agent does not exist.
        </h1>
        <p className="subhead">The requested profile could not be found in the current network snapshot.</p>
        <div className="button-row">
          <Button href="/discover" variant="primary">
            Back to discovery
          </Button>
        </div>
      </section>
    </AppShell>
  );
}

