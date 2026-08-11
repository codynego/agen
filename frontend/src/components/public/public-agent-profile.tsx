"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";

import { Icon } from "@/components/workspace/icons";
import { ApiError, PublicBusinessAgent, sendPublicAgentMessage } from "@/lib/client-api";

type ChatMessage = { id: string; role: "guest" | "agent"; content: string };

export function PublicAgentProfile({ agent, apiBaseUrl }: { agent: PublicBusinessAgent; apiBaseUrl: string }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessionId, setSessionId] = useState<string>();
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const [shared, setShared] = useState(false);

  async function share() {
    if (navigator.share) await navigator.share({ title: agent.name, text: agent.tagline, url: agent.canonical_url });
    else await navigator.clipboard.writeText(agent.canonical_url);
    setShared(true); setTimeout(() => setShared(false), 1800);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const input = form.elements.namedItem("message") as HTMLTextAreaElement;
    const message = input.value.trim();
    if (!message || sending) return;
    const guestMessage = { id: `guest-${Date.now()}`, role: "guest" as const, content: message };
    setMessages((items) => [...items, guestMessage]); input.value = ""; setSending(true); setError("");
    try {
      const result = await sendPublicAgentMessage(agent.network_handle, message, sessionId);
      setSessionId(result.session_id);
      setMessages((items) => [...items, { id: result.message_id, role: "agent", content: result.response }]);
    } catch (caught) { setError((caught as ApiError).message); }
    finally { setSending(false); }
  }

  return <main className="public-agent-page">
    <nav className="public-agent-nav"><Link href="/" className="public-agent-brand"><span><Icon name="spark" /></span><strong>agen</strong></Link><div><span><Icon name="shield" />Verified agent identity</span><button type="button" onClick={share}>{shared ? "Link copied" : "Share profile"}</button></div></nav>
    <section className="public-agent-hero">
      <div className="public-agent-cover" style={agent.cover_url ? { backgroundImage: `linear-gradient(90deg,rgba(19,43,31,.76),rgba(19,43,31,.2)),url(${agent.cover_url})` } : undefined} />
      <div className="public-agent-hero__content">
        <div className="public-agent-logo">{agent.logo_url ? <img src={agent.logo_url} alt="" /> : <Icon name="business" />}</div>
        <div className="public-agent-title"><div><span>{agent.category}</span><h1>{agent.name}</h1><p>by {agent.company_name} · @{agent.network_handle}</p></div><div className="public-agent-live"><i />{agent.online ? "Available" : "Offline"}</div></div>
        <p className="public-agent-tagline">{agent.tagline || agent.description}</p>
        <div className="public-agent-badges"><span><Icon name="shield" />{agent.verification_level} verified</span><span>Trust {agent.trust_score}</span>{agent.location ? <span>{agent.location}</span> : null}</div>
      </div>
    </section>

    <div className="public-agent-grid">
      <div className="public-agent-main">
        <section className="public-agent-card"><span className="public-kicker">About this agent</span><h2>A trusted digital representative for {agent.company_name}</h2><p>{agent.description}</p>{agent.capabilities.length ? <div className="public-capabilities">{agent.capabilities.map((capability) => <span key={capability}>{capability.replaceAll("_", " ")}</span>)}</div> : null}</section>
        {agent.catalog.length ? <section className="public-agent-card"><span className="public-kicker">Products and services</span><h2>Published catalogue</h2><div className="public-catalog">{agent.catalog.map((item) => <article key={item.item_id}><small>{item.sku || "Available from business"}</small><h3>{item.name}</h3><p>{item.description}</p><div><strong>{item.price ? `${item.currency} ${item.price}` : "Price on request"}</strong><span>{item.availability}</span></div></article>)}</div></section> : null}
        {agent.public_chat_enabled ? <section className="public-agent-card public-chat"><span className="public-kicker">Guest chat</span><h2>Ask {agent.name}</h2><p>Responses use only information this business has chosen to publish. External actions are not available in guest chat.</p><div className="public-chat-thread">{messages.length ? messages.map((message) => <div key={message.id} className={`public-chat-message is-${message.role}`}>{message.role === "agent" ? <span><Icon name="spark" /></span> : null}<div>{message.content}</div></div>) : <div className="public-chat-empty"><Icon name="spark" /><span>Ask about published products, services, policies, or availability.</span></div>}{sending ? <div className="public-chat-working"><i /><i /><i />Checking published business information</div> : null}{error ? <div className="public-chat-error">{error}</div> : null}</div><form onSubmit={submit}><textarea name="message" rows={2} required maxLength={2000} placeholder={`Ask ${agent.name}...`} /><button type="submit" disabled={sending}><Icon name="send" /></button></form></section> : null}
      </div>
      <aside className="public-agent-side">
        <section className="public-trust-card"><span className="public-kicker">Network identity</span><div className="public-trust-score"><strong>{agent.trust_score}</strong><span>{agent.trust_level.replaceAll("_", " ")}</span></div><dl><div><dt>Verification</dt><dd>{agent.verification_level}</dd></div><div><dt>Completed work</dt><dd>{agent.completed_tasks}</dd></div><div><dt>Languages</dt><dd>{agent.languages.join(", ") || "Not specified"}</dd></div></dl><a href={`${apiBaseUrl}/api/public/agents/${agent.network_handle}/manifest/`} target="_blank" rel="noreferrer">View agent manifest <Icon name="chevron" /></a></section>
        <section className="public-share-card"><img src={`${apiBaseUrl}/api/public/agents/${agent.network_handle}/qr/`} alt={`QR code for ${agent.name}`} /><h3>Connect anywhere</h3><p>Scan to verify this agent or open its public profile.</p><button type="button" onClick={share}>{shared ? "Copied" : "Copy profile link"}</button></section>
        {(agent.website_url || agent.social_links.length) ? <section className="public-links-card"><span className="public-kicker">Official links</span>{agent.website_url ? <a href={agent.website_url} target="_blank" rel="noreferrer">Business website <Icon name="chevron" /></a> : null}{agent.social_links.map((link) => <a key={link.url} href={link.url} target="_blank" rel="noreferrer">{link.label}<Icon name="chevron" /></a>)}</section> : null}
      </aside>
    </div>
    <footer className="public-agent-footer"><span><Icon name="shield" />Identity and trust verified through Agen</span><Link href="/auth">Create your personal agent</Link></footer>
  </main>;
}
