"use client";

import { FormEvent, useEffect, useState } from "react";

import { Icon } from "@/components/workspace/icons";
import {
  ApiError,
  ManagedAgentSetup,
  PublicProfileSettings,
  activateManagedAgent,
  addManagedCatalogItem,
  addManagedKnowledge,
  applyManagedTemplate,
  connectManagedTool,
  deleteManagedCatalogItem,
  deleteManagedKnowledge,
  disconnectManagedTool,
  getManagedAgentSetup,
  getPublicProfileSettings,
  submitManagedVerification,
  testManagedAgent,
  updateManagedAgent,
  updatePublicProfileSettings,
} from "@/lib/client-api";

type SetupTab = "overview" | "verification" | "knowledge" | "catalog" | "tools" | "behavior" | "sandbox" | "publishing";

const setupTabs: Array<{ id: SetupTab; label: string; icon: string }> = [
  { id: "overview", label: "Overview", icon: "home" },
  { id: "verification", label: "Verification", icon: "shield" },
  { id: "knowledge", label: "Knowledge", icon: "tasks" },
  { id: "catalog", label: "Catalogue", icon: "business" },
  { id: "tools", label: "Tools", icon: "link" },
  { id: "behavior", label: "Behavior", icon: "settings" },
  { id: "sandbox", label: "Test agent", icon: "spark" },
  { id: "publishing", label: "Public profile", icon: "link" },
];

const readinessLabels: Record<string, string> = {
  business_verified: "Business verified",
  template_selected: "Industry template selected",
  knowledge_added: "Business knowledge added",
  instructions_configured: "Instructions configured",
  capabilities_configured: "Capabilities configured",
  sandbox_test_passed: "Sandbox test passed",
};

export function ManagedAgentStudio({ agentId, onBack }: { agentId: string; onBack: () => void }) {
  const [setup, setSetup] = useState<ManagedAgentSetup | null>(null);
  const [tab, setTab] = useState<SetupTab>("overview");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    getManagedAgentSetup(agentId)
      .then((data) => { if (active) setSetup(data); })
      .catch((caught) => { if (active) setError((caught as ApiError).message); });
    return () => { active = false; };
  }, [agentId]);

  async function run(action: () => Promise<unknown>, refresh = true) {
    setBusy(true);
    setError("");
    try {
      const result = await action();
      if (result && typeof result === "object" && "readiness" in result) setSetup(result as ManagedAgentSetup);
      else if (refresh) setSetup(await getManagedAgentSetup(agentId));
      return result;
    } catch (caught) {
      setError((caught as ApiError).message);
      return null;
    } finally {
      setBusy(false);
    }
  }

  if (!setup) return <section className="managed-loading"><span><Icon name="spark" /></span><p>{error || "Opening managed agent studio..."}</p><button type="button" onClick={onBack}>Back</button></section>;

  const completed = Object.values(setup.readiness.checks).filter(Boolean).length;
  return (
    <section className="managed-studio">
      <header className="managed-head">
        <button type="button" onClick={onBack} className="managed-back">‹ All agents</button>
        <div className="managed-identity"><span><Icon name="business" /></span><div><small>Managed business agent</small><h2>{setup.agent.name}</h2><p>@{setup.agent.network_handle} · {setup.agent.status}</p></div></div>
        <div className="managed-head__trust"><span>Network trust</span><strong>{setup.agent.trust_score}</strong></div>
      </header>

      <div className="managed-progress"><div><span>Activation readiness</span><strong>{completed} of {Object.keys(setup.readiness.checks).length} complete</strong></div><i><b style={{ width: `${(completed / Object.keys(setup.readiness.checks).length) * 100}%` }} /></i><button type="button" disabled={!setup.readiness.ready || busy || setup.agent.status === "active"} onClick={() => run(() => activateManagedAgent(agentId))}>{setup.agent.status === "active" ? "Active on network" : "Activate agent"}</button></div>
      {error ? <div className="managed-error" role="alert">{error}</div> : null}

      <div className="managed-shell">
        <nav className="managed-nav" aria-label="Managed agent setup">{setupTabs.map((item) => <button type="button" key={item.id} className={tab === item.id ? "is-active" : ""} onClick={() => setTab(item.id)}><Icon name={item.icon} /><span>{item.label}</span>{item.id === "verification" && setup.profile.verification_status === "verified" ? <i /> : null}</button>)}</nav>
        <main className="managed-panel">
          {tab === "overview" ? <Overview setup={setup} onOpen={setTab} /> : null}
          {tab === "verification" ? <Verification setup={setup} busy={busy} onSubmit={(input) => run(() => submitManagedVerification(agentId, input))} /> : null}
          {tab === "knowledge" ? <Knowledge setup={setup} busy={busy} onAdd={(input) => run(() => addManagedKnowledge(agentId, input))} onDelete={(id) => run(() => deleteManagedKnowledge(agentId, id))} /> : null}
          {tab === "catalog" ? <Catalog setup={setup} busy={busy} onAdd={(input) => run(() => addManagedCatalogItem(agentId, input))} onDelete={(id) => run(() => deleteManagedCatalogItem(agentId, id))} /> : null}
          {tab === "tools" ? <Tools setup={setup} busy={busy} onConnect={(input) => run(() => connectManagedTool(agentId, input))} onDelete={(id) => run(() => disconnectManagedTool(agentId, id))} /> : null}
          {tab === "behavior" ? <Behavior setup={setup} busy={busy} onSave={(input) => run(() => updateManagedAgent(agentId, input))} onTemplate={(key) => run(() => applyManagedTemplate(agentId, key))} /> : null}
          {tab === "sandbox" ? <Sandbox setup={setup} busy={busy} onTest={(prompt) => run(() => testManagedAgent(agentId, prompt))} /> : null}
          {tab === "publishing" ? <Publishing agentId={agentId} setup={setup} /> : null}
        </main>
      </div>
    </section>
  );
}

function PanelHead({ kicker, title, copy }: { kicker: string; title: string; copy: string }) {
  return <header className="managed-panel__head"><span>{kicker}</span><h3>{title}</h3><p>{copy}</p></header>;
}

function Overview({ setup, onOpen }: { setup: ManagedAgentSetup; onOpen: (tab: SetupTab) => void }) {
  return <><PanelHead kicker="Launch checklist" title="Prepare this agent for real work" copy="Every requirement is enforced by the backend before the agent can appear in network discovery." /><div className="readiness-grid">{Object.entries(setup.readiness.checks).map(([key, complete]) => <button type="button" key={key} className={complete ? "is-complete" : ""} onClick={() => onOpen(key === "business_verified" ? "verification" : key === "sandbox_test_passed" ? "sandbox" : key === "template_selected" || key === "instructions_configured" || key === "capabilities_configured" ? "behavior" : "knowledge")}><span>{complete ? "✓" : Object.keys(setup.readiness.checks).indexOf(key) + 1}</span><div><strong>{readinessLabels[key]}</strong><small>{complete ? "Complete" : "Needs attention"}</small></div><Icon name="chevron" /></button>)}</div><div className="managed-audit"><h4>Recent configuration activity</h4>{setup.audit.length ? setup.audit.slice(0, 6).map((event) => <article key={event.event_id}><i /><div><strong>{event.action.replaceAll("_", " ")}</strong><p>{event.detail}</p></div><time>{new Date(event.created_at).toLocaleDateString()}</time></article>) : <p>No configuration activity yet.</p>}</div></>;
}

function Verification({ setup, busy, onSubmit }: { setup: ManagedAgentSetup; busy: boolean; onSubmit: (input: Record<string, unknown>) => void }) {
  const [method, setMethod] = useState<"domain" | "manual" | "development">("domain");
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    onSubmit({
      method,
      domain: String(form.get("domain") || ""),
      country: String(form.get("country") || ""),
      registration_number: String(form.get("registration_number") || ""),
      business_phone: String(form.get("business_phone") || ""),
      supporting_url: String(form.get("supporting_url") || ""),
      evidence_notes: String(form.get("evidence_notes") || ""),
      requested_level: String(form.get("requested_level") || "business"),
      development_code: String(form.get("development_code") || ""),
    });
  }
  return <><PanelHead kicker="Business identity" title="Verify who operates this agent" copy="Use your domain when available, or submit business evidence without a website. Verification strength is matched to the actions this agent can perform." />
    <div className={`verification-banner is-${setup.profile.verification_status}`}><Icon name="shield" /><div><strong>{setup.profile.verification_status.replace("_", " ")} · {setup.profile.verification_level}</strong><p>Current level: {setup.readiness.current_verification_level}. Activation requires: {setup.readiness.required_verification_level}.</p></div></div>
    <div className="verification-routes" role="tablist" aria-label="Verification method"><button type="button" className={method === "domain" ? "is-active" : ""} onClick={() => setMethod("domain")}>I have a domain</button><button type="button" className={method === "manual" ? "is-active" : ""} onClick={() => setMethod("manual")}>No website</button>{setup.development_verification_enabled ? <button type="button" className={method === "development" ? "is-active" : ""} onClick={() => setMethod("development")}>Local testing</button> : null}</div>
    <form className="managed-form managed-form--grid" onSubmit={submit}>
      {method === "domain" ? <label className="is-wide"><span>Business domain</span><input name="domain" required defaultValue={setup.profile.business_domain} placeholder="acme.com" /><small>Your signed-in email should use this domain for instant verification. Non-matching domains go to review.</small></label> : null}
      {method === "manual" ? <><label><span>Country</span><input name="country" required defaultValue={setup.profile.country} placeholder="Nigeria" /></label><label><span>Business phone</span><input name="business_phone" required defaultValue={setup.profile.business_phone} placeholder="+234..." /></label><label><span>Registration number</span><input name="registration_number" defaultValue={setup.profile.registration_number} placeholder="Optional if informal" /></label><label><span>Requested level</span><select name="requested_level" defaultValue={setup.profile.requested_verification_level}><option value="basic">Basic</option><option value="business">Business</option><option value="enhanced">Enhanced</option></select></label><label className="is-wide"><span>Business profile or marketplace URL</span><input name="supporting_url" type="url" defaultValue={setup.profile.supporting_url} placeholder="https://instagram.com/yourbusiness" /></label><label className="is-wide"><span>Supporting information</span><textarea name="evidence_notes" rows={4} defaultValue={setup.profile.evidence_notes} placeholder="Describe the business and the evidence an administrator should review." /></label></> : null}
      {method === "development" ? <><label><span>Verification level</span><select name="requested_level" defaultValue="enhanced"><option value="basic">Basic</option><option value="business">Business</option><option value="enhanced">Enhanced</option></select></label><label><span>Local test code</span><input name="development_code" required inputMode="numeric" maxLength={6} placeholder="246810" /><small>Default local code: 246810</small></label><div className="dev-verification-note is-wide"><Icon name="shield" /><p>This shortcut only works while Django is in development mode. It is unavailable in production.</p></div></> : null}
      <button type="submit" disabled={busy}>{busy ? "Checking..." : method === "manual" ? "Submit for review" : "Verify business"}</button>
    </form></>;
}

function Knowledge({ setup, busy, onAdd, onDelete }: { setup: ManagedAgentSetup; busy: boolean; onAdd: (input: { kind: string; title: string; content: string }) => void; onDelete: (id: string) => void }) {
  function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); const form = new FormData(event.currentTarget); onAdd({ kind: String(form.get("kind")), title: String(form.get("title")), content: String(form.get("content")) }); event.currentTarget.reset(); }
  return <><PanelHead kicker="Encrypted knowledge" title="Teach the agent about your business" copy="Add policies, FAQs, services, and operating information. Content is encrypted at rest and isolated to this agent." /><form className="managed-form managed-form--grid" onSubmit={submit}><label><span>Type</span><select name="kind"><option value="note">Business note</option><option value="faq">FAQ</option><option value="document">Document text</option><option value="website">Website content</option></select></label><label><span>Title</span><input name="title" required placeholder="Returns policy" /></label><label className="is-wide"><span>Information</span><textarea name="content" required rows={5} placeholder="Add the exact information this agent should use..." /></label><button type="submit" disabled={busy}>Add knowledge</button></form><div className="managed-list">{setup.knowledge.map((source) => <article key={source.source_id}><span><Icon name="tasks" /></span><div><strong>{source.title}</strong><small>{source.kind}</small><p>{source.content}</p></div><button type="button" onClick={() => onDelete(source.source_id)}>Remove</button></article>)}</div></>;
}

function Catalog({ setup, busy, onAdd, onDelete }: { setup: ManagedAgentSetup; busy: boolean; onAdd: (input: Record<string, unknown>) => void; onDelete: (id: string) => void }) {
  function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); const form = new FormData(event.currentTarget); const price = String(form.get("price") || ""); onAdd({ name: String(form.get("name")), sku: String(form.get("sku")), description: String(form.get("description")), price: price || null, currency: String(form.get("currency")), availability: String(form.get("availability")) }); event.currentTarget.reset(); }
  return <><PanelHead kicker="Products and services" title="Build a searchable catalogue" copy="Catalogue items become grounded context for discovery, quoting, and availability questions." /><form className="managed-form managed-form--grid" onSubmit={submit}><label><span>Name</span><input name="name" required placeholder="Premium support plan" /></label><label><span>SKU</span><input name="sku" placeholder="SUPPORT-PRO" /></label><label><span>Price</span><input name="price" type="number" min="0" step="0.01" placeholder="25000" /></label><label><span>Currency</span><input name="currency" defaultValue="NGN" /></label><label className="is-wide"><span>Description</span><textarea name="description" rows={3} /></label><label><span>Availability</span><input name="availability" defaultValue="Available" /></label><button type="submit" disabled={busy}>Add item</button></form><div className="catalog-grid">{setup.catalog.map((item) => <article key={item.item_id}><small>{item.sku || "No SKU"}</small><h4>{item.name}</h4><p>{item.description || "No description"}</p><div><strong>{item.price ? `${item.currency} ${item.price}` : "Price on request"}</strong><span>{item.availability}</span></div><button type="button" onClick={() => onDelete(item.item_id)}>Remove</button></article>)}</div></>;
}

function Tools({ setup, busy, onConnect, onDelete }: { setup: ManagedAgentSetup; busy: boolean; onConnect: (input: Record<string, unknown>) => void; onDelete: (id: string) => void }) {
  function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); const form = new FormData(event.currentTarget); const raw = String(form.get("config") || "{}"); let config = {}; try { config = JSON.parse(raw); } catch { config = { token: raw }; } onConnect({ provider: String(form.get("provider")), display_name: String(form.get("display_name")), scopes: String(form.get("scopes") || "").split(",").map((v) => v.trim()).filter(Boolean), secret_config: config }); }
  return <><PanelHead kicker="Action layer" title="Connect tools without exposing credentials" copy="This MVP registers encrypted credentials and scopes. Provider-specific OAuth and execution adapters plug into these records next." /><form className="managed-form managed-form--grid" onSubmit={submit}><label><span>Provider key</span><input name="provider" required pattern="[a-z][a-z0-9_-]+" placeholder="shopify" /></label><label><span>Display name</span><input name="display_name" required placeholder="Acme Store" /></label><label className="is-wide"><span>Scopes</span><input name="scopes" placeholder="inventory_read, orders_read" /></label><label className="is-wide"><span>Secret configuration</span><textarea name="config" rows={3} placeholder={'{"api_key":"..."}'} /><small>Encrypted before storage and never returned by the API.</small></label><button type="submit" disabled={busy}>Connect tool</button></form><div className="managed-list">{setup.tools.map((tool) => <article key={tool.connection_id}><span><Icon name="link" /></span><div><strong>{tool.display_name}</strong><small>{tool.provider} · {tool.status}</small><p>{tool.scopes.join(", ") || "No scopes"}</p></div><button type="button" onClick={() => onDelete(tool.connection_id)}>Disconnect</button></article>)}</div></>;
}

function Behavior({ setup, busy, onSave, onTemplate }: { setup: ManagedAgentSetup; busy: boolean; onSave: (input: Record<string, unknown>) => void; onTemplate: (key: string) => void }) {
  function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); const form = new FormData(event.currentTarget); onSave({ instructions: String(form.get("instructions")), tone: String(form.get("tone")), human_handoff: String(form.get("handoff")), capabilities: String(form.get("capabilities")).split(",").map((v) => v.trim()).filter(Boolean), allowed_actions: String(form.get("allowed")).split(",").map((v) => v.trim()).filter(Boolean), blocked_actions: String(form.get("blocked")).split(",").map((v) => v.trim()).filter(Boolean) }); }
  return <><PanelHead kicker="Behavior and policy" title="Define how this agent should operate" copy="Start from an industry template, then make the instructions and action boundaries specific to your business." /><div className="template-grid">{setup.templates.map((template) => <button type="button" key={template.key} className={setup.profile.template_key === template.key ? "is-selected" : ""} onClick={() => onTemplate(template.key)}><span><Icon name="spark" /></span><strong>{template.name}</strong><p>{template.description}</p></button>)}</div><form className="managed-form" onSubmit={submit}><label><span>Core instructions</span><textarea name="instructions" rows={6} defaultValue={setup.profile.instructions} /></label><label><span>Tone</span><input name="tone" defaultValue={setup.profile.tone} /></label><label><span>Human handoff</span><textarea name="handoff" rows={3} defaultValue={setup.profile.human_handoff} placeholder="When and how should this agent escalate?" /></label><label><span>Capabilities</span><input name="capabilities" defaultValue={setup.agent.capabilities.join(", ")} /></label><label><span>Allowed actions</span><input name="allowed" defaultValue={setup.agent.allowed_actions.join(", ")} placeholder="search_catalog, create_ticket" /></label><label><span>Blocked actions</span><input name="blocked" defaultValue={setup.agent.blocked_actions.join(", ")} placeholder="issue_refund, disclose_credentials" /></label><button type="submit" disabled={busy}>Save behavior</button></form></>;
}

function Sandbox({ setup, busy, onTest }: { setup: ManagedAgentSetup; busy: boolean; onTest: (prompt: string) => void }) {
  const latest = setup.tests[0]; function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); onTest(String(new FormData(event.currentTarget).get("prompt") || "")); }
  return <><PanelHead kicker="Safe preview" title="Test against this agent's own data" copy="The sandbox retrieves only this business agent's knowledge and catalogue. It does not execute external actions." /><form className="sandbox-composer" onSubmit={submit}><textarea name="prompt" required rows={3} placeholder="Ask a realistic customer question..." /><button type="submit" disabled={busy}>{busy ? "Testing..." : "Run sandbox test"}</button></form>{latest ? <article className={`sandbox-result is-${latest.status}`}><header><span><Icon name="spark" /></span><div><strong>{latest.status.replace("_", " ")}</strong><small>{latest.matched_sources.length ? `Sources: ${latest.matched_sources.join(", ")}` : "No matching sources"}</small></div></header><p>{latest.response}</p></article> : <div className="managed-empty"><Icon name="spark" /><p>No tests yet. Ask a question your customers are likely to send.</p></div>}</>;
}

function Publishing({ agentId, setup }: { agentId: string; setup: ManagedAgentSetup }) {
  const [profile, setProfile] = useState<PublicProfileSettings | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => { getPublicProfileSettings(agentId).then(setProfile).catch((caught) => setError((caught as ApiError).message)); }, [agentId]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!profile) return;
    setSaving(true); setError("");
    const form = new FormData(event.currentTarget);
    try {
      const updated = await updatePublicProfileSettings(agentId, {
        visibility: String(form.get("visibility")),
        tagline: String(form.get("tagline")),
        public_description: String(form.get("description")),
        logo_url: String(form.get("logo_url")),
        cover_url: String(form.get("cover_url")),
        website_url: String(form.get("website_url")),
        public_location: String(form.get("location")),
        languages: String(form.get("languages")).split(",").map((value) => value.trim()).filter(Boolean),
        published_capabilities: setup.agent.capabilities.filter((capability) => form.getAll("capability").includes(capability)),
        social_links: String(form.get("social_links")).split("\n").map((line) => line.trim()).filter(Boolean).map((line) => { const [label, url] = line.split("|").map((value) => value.trim()); return { label: label || "Link", url }; }),
        public_chat_enabled: form.get("public_chat_enabled") === "on",
        show_catalog: form.get("show_catalog") === "on",
        show_trust_history: form.get("show_trust_history") === "on",
        guest_daily_limit: Number(form.get("guest_daily_limit") || 20),
        published_source_ids: form.getAll("knowledge").map(String),
        published_item_ids: form.getAll("catalog_item").map(String),
      });
      setProfile(updated);
    } catch (caught) { setError((caught as ApiError).message); }
    finally { setSaving(false); }
  }

  if (!profile) return <div className="managed-empty"><Icon name="link" /><p>{error || "Loading public profile settings..."}</p></div>;
  return <><PanelHead kicker="Publishing" title="Give this agent a public home" copy="Choose exactly what visitors and external agents can see. Private instructions, secrets, and audit logs are never published." />
    <div className="public-profile-status"><div><span>Canonical profile</span><strong>{profile.canonical_url}</strong></div>{profile.publishable && profile.visibility !== "private" ? <a href={profile.canonical_url} target="_blank" rel="noreferrer">Preview profile <Icon name="chevron" /></a> : <span>Not live yet</span>}</div>
    {profile.publish_blockers.length ? <div className="managed-error">{profile.publish_blockers.join(" ")}</div> : null}
    {error ? <div className="managed-error">{error}</div> : null}
    <form className="managed-form managed-form--grid" onSubmit={submit}>
      <label><span>Visibility</span><select name="visibility" defaultValue={profile.publishable ? profile.visibility : "private"}><option value="private">Private</option><option value="unlisted" disabled={!profile.publishable}>Unlisted link</option><option value="public" disabled={!profile.publishable}>Public and discoverable</option></select><small>{profile.publishable ? "Publishing is available." : "Resolve the publishing requirements above first."}</small></label>
      <label><span>Public location</span><input name="location" defaultValue={profile.public_location} placeholder="Lagos, Nigeria" /></label>
      <label className="is-wide"><span>Tagline</span><input name="tagline" maxLength={160} defaultValue={profile.tagline} placeholder="Trusted support for every order" /></label>
      <label className="is-wide"><span>Public description</span><textarea name="description" rows={4} defaultValue={profile.public_description} placeholder="Explain what this agent can help visitors accomplish." /></label>
      <label><span>Logo URL</span><input name="logo_url" type="url" defaultValue={profile.logo_url} placeholder="https://..." /></label><label><span>Cover image URL</span><input name="cover_url" type="url" defaultValue={profile.cover_url} placeholder="https://..." /></label>
      <label><span>Business website</span><input name="website_url" type="url" defaultValue={profile.website_url} placeholder="https://..." /></label><label><span>Languages</span><input name="languages" defaultValue={profile.languages.join(", ")} placeholder="English, Yoruba" /></label>
      <label className="is-wide"><span>Social links</span><textarea name="social_links" rows={3} defaultValue={profile.social_links.map((link) => `${link.label} | ${link.url}`).join("\n")} placeholder={"Instagram | https://instagram.com/business\nLinkedIn | https://linkedin.com/company/business"} /><small>One per line: Label | HTTPS URL</small></label>
      <fieldset className="publishing-options is-wide"><legend>Published capabilities</legend>{setup.agent.capabilities.map((capability) => <label key={capability}><input type="checkbox" name="capability" value={capability} defaultChecked={profile.published_capabilities.includes(capability)} /><span>{capability.replaceAll("_", " ")}</span></label>)}</fieldset>
      <fieldset className="publishing-options is-wide"><legend>Published knowledge</legend>{setup.knowledge.length ? setup.knowledge.map((source) => <label key={source.source_id}><input type="checkbox" name="knowledge" value={source.source_id} defaultChecked={profile.published_source_ids.includes(source.source_id)} /><span>{source.title}</span></label>) : <p>Add knowledge before publishing it.</p>}</fieldset>
      <fieldset className="publishing-options is-wide"><legend>Published catalogue</legend>{setup.catalog.length ? setup.catalog.map((item) => <label key={item.item_id}><input type="checkbox" name="catalog_item" value={item.item_id} defaultChecked={profile.published_item_ids.includes(item.item_id)} /><span>{item.name}</span></label>) : <p>Add catalogue items before publishing them.</p>}</fieldset>
      <div className="publishing-switches is-wide"><label><input type="checkbox" name="public_chat_enabled" defaultChecked={profile.public_chat_enabled} /><span><strong>Guest chat</strong><small>Visitors can ask about published information.</small></span></label><label><input type="checkbox" name="show_catalog" defaultChecked={profile.show_catalog} /><span><strong>Show catalogue</strong><small>Display selected products and services.</small></span></label><label><input type="checkbox" name="show_trust_history" defaultChecked={profile.show_trust_history} /><span><strong>Show trust</strong><small>Display verification and network performance.</small></span></label></div>
      <label><span>Guest messages per day</span><input name="guest_daily_limit" type="number" min={1} max={500} defaultValue={profile.guest_daily_limit} /></label>
      <button type="submit" disabled={saving}>{saving ? "Publishing..." : "Save public profile"}</button>
    </form></>;
}
