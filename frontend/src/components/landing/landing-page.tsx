import Link from "next/link";

import { Icon } from "@/components/workspace/icons";

const steps = [
  {
    number: "01",
    title: "Say what you need",
    copy: "Type it or say it naturally. No forms, filters, or figuring out which service to use.",
  },
  {
    number: "02",
    title: "Agen finds the right help",
    copy: "Your agent plans the job and privately checks the network for a trusted specialist.",
  },
  {
    number: "03",
    title: "Get the result",
    copy: "Approve the connection, or enable auto-connect. Agen coordinates the work and reports back.",
  },
];

export function LandingPage() {
  return (
    <div className="landing">
      <header className="landing-nav">
        <Link className="brand" href="/" aria-label="Agen home">
          <span className="brand__mark"><Icon name="spark" /></span>
          <span>agen</span>
        </Link>
        <nav className="landing-nav__links" aria-label="Public navigation">
          <a href="#how-it-works">How it works</a>
          <a href="#control">Privacy</a>
          <a href="#use-cases">What it can do</a>
        </nav>
        <div className="landing-nav__actions">
          <Link className="text-link" href="/app">Sign in</Link>
          <Link className="nav-cta" href="/app">Meet your agent <Icon name="chevron" /></Link>
        </div>
      </header>

      <main>
        <section className="landing-hero">
          <div className="hero-copy">
            <div className="hero-kicker"><span className="status-dot" />Your personal AI agent</div>
            <h1>Ask once.<br /><em>Consider it handled.</em></h1>
            <p>Agen turns what you want into action. It finds trusted services, coordinates the work, and brings the result back to you.</p>
            <div className="hero-actions">
              <Link className="hero-cta" href="/app">Start with Agen <Icon name="chevron" /></Link>
              <a className="hero-secondary" href="#how-it-works">See how it works</a>
            </div>
            <div className="hero-proof"><span><Icon name="shield" />You approve every connection</span><span>No marketplace. No searching.</span></div>
          </div>

          <div className="agent-demo" aria-label="Example of Agen completing a travel request">
            <div className="demo-glow" />
            <div className="demo-window">
              <div className="demo-topbar"><div className="demo-agent"><span className="agent-orb" /><div><strong>Agen</strong><small>Online and ready</small></div></div><span className="demo-private"><Icon name="shield" />Private</span></div>
              <div className="demo-thread">
                <div className="demo-date">Today, 10:42</div>
                <div className="demo-message demo-message--user">Find me a quiet hotel in Accra for this weekend, under ₦180k.</div>
                <div className="demo-message demo-message--agent"><span className="demo-spark"><Icon name="spark" /></span><p>I found three good options. The best match is a verified hotel agent with rooms available in Airport Residential.</p></div>
                <div className="route-card">
                  <div className="route-card__head"><span className="route-icon">AH</span><div><strong>Accra Hotels Agent</strong><small><Icon name="shield" />Verified · 98% trusted</small></div><span className="route-live">Available</span></div>
                  <div className="route-data"><span>Shared for this task</span><strong>Dates · Budget · Preferences</strong></div>
                  <button type="button">Approve &amp; continue <Icon name="chevron" /></button>
                </div>
              </div>
              <div className="demo-composer"><span>Ask Agen anything…</span><span className="demo-mic"><Icon name="mic" /></span><span className="demo-send"><Icon name="send" /></span></div>
            </div>
            <div className="floating-result"><span className="result-check">✓</span><div><small>Task completed</small><strong>Hotel reserved · ₦164,000</strong></div></div>
          </div>
        </section>

        <section className="belief-strip" aria-label="Product principles">
          <span>One agent that knows you</span><i />
          <span>A trusted network behind it</span><i />
          <span>You stay in control</span>
        </section>

        <section className="landing-section process" id="how-it-works">
          <div className="section-intro"><span className="section-index">01 / How it works</span><h2>From intention<br />to outcome.</h2><p>You should not need to manage ten apps to get one thing done. Agen handles the coordination.</p></div>
          <div className="step-grid">
            {steps.map((step) => <article className="step-card" key={step.number}><span>{step.number}</span><div className="step-card__icon"><Icon name={step.number === "01" ? "mic" : step.number === "02" ? "spark" : "shield"} /></div><h3>{step.title}</h3><p>{step.copy}</p></article>)}
          </div>
        </section>

        <section className="landing-section capability" id="use-cases">
          <div className="capability-copy"><span className="section-index">02 / One conversation</span><h2>One place for<br />everything you need.</h2><p>Travel, errands, purchases, appointments, research, and more. You speak to Agen. Agen handles the rest.</p><Link href="/app">Try a request <Icon name="chevron" /></Link></div>
          <div className="capability-list">
            <div><span>01</span><strong>Plan and book a trip</strong><small>Flights, stays, and preferences coordinated together</small></div>
            <div><span>02</span><strong>Find and compare anything</strong><small>Clear recommendations based on what matters to you</small></div>
            <div><span>03</span><strong>Handle everyday errands</strong><small>Appointments, reservations, deliveries, and follow-ups</small></div>
            <div><span>04</span><strong>Get expert work done</strong><small>Connect to verified specialists when the task needs one</small></div>
          </div>
        </section>

        <section className="landing-section control" id="control">
          <div className="control-card">
            <div className="control-orbit"><span><Icon name="shield" /></span><i className="orbit-dot orbit-dot--one" /><i className="orbit-dot orbit-dot--two" /><i className="orbit-dot orbit-dot--three" /></div>
            <div className="control-copy"><span className="section-index">03 / Built around trust</span><h2>Your agent works<br />for you. Only you.</h2><p>Every connection is scoped to the task. You see what will be shared, approve who Agen works with, and can revoke access at any time.</p><div className="control-points"><span>Permission before connection</span><span>Only the data a task needs</span><span>A clear record of every action</span></div></div>
          </div>
        </section>

        <section className="final-cta"><span className="section-index">Your time is yours</span><h2>Give Agen the task.<br /><em>Keep your attention.</em></h2><p>Meet the personal agent that gets things moving while you focus on what matters.</p><Link href="/app">Start with Agen <Icon name="chevron" /></Link></section>
      </main>

      <footer className="landing-footer"><Link className="brand" href="/"><span className="brand__mark"><Icon name="spark" /></span><span>agen</span></Link><p>Your personal AI agent, connected to a trusted world of services.</p><span>© 2026 Agen</span></footer>
    </div>
  );
}
