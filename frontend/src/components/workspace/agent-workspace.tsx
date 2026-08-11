"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, KeyboardEvent, useEffect, useState } from "react";

import { Icon } from "@/components/workspace/icons";
import { SettingsView } from "@/components/workspace/settings-view";
import { AgentConnection, ApiError, AuthSession, ResolverCandidate, approveAgentConnection, createBusinessAgent, discoverAgents, getAuthSession, logoutAccount, requestAgentConnection } from "@/lib/client-api";

type WorkspaceTab = "agent" | "tasks" | "studio" | "activity" | "settings";

const tabs: Array<{ id: WorkspaceTab; label: string; icon: string }> = [
  { id: "agent", label: "My agent", icon: "home" },
  { id: "tasks", label: "Tasks", icon: "tasks" },
  { id: "studio", label: "Agent studio", icon: "business" },
  { id: "activity", label: "Activity", icon: "activity" },
  { id: "settings", label: "Settings", icon: "settings" },
];

const prompts = ["Plan a weekend in Accra", "Find a better data plan", "Book a table for Friday", "Compare laptop deals"];
const voiceBars = [18, 30, 44, 27, 58, 72, 38, 64, 88, 52, 76, 96, 62, 84, 48, 70, 40, 58, 32, 45, 22];

const tabTitles: Record<WorkspaceTab, { eyebrow: string; title: string }> = {
  agent: { eyebrow: "Personal agent", title: "What can I handle for you?" },
  tasks: { eyebrow: "Task center", title: "Everything Agen is handling" },
  studio: { eyebrow: "Agent studio", title: "Build or connect a business agent" },
  activity: { eyebrow: "Activity", title: "A clear record of every action" },
  settings: { eyebrow: "Control center", title: "Your agent, your rules" },
};

export function AgentWorkspace() {
  const router = useRouter();
  const [session, setSession] = useState<AuthSession | null>(null);
  const [checkingSession, setCheckingSession] = useState(true);
  const [activeTab, setActiveTab] = useState<WorkspaceTab>("agent");
  const [message, setMessage] = useState("");
  const [request, setRequest] = useState("");
  const [autoConnect, setAutoConnect] = useState(false);
  const [listening, setListening] = useState(false);
  const [approved, setApproved] = useState(false);
  const [candidate, setCandidate] = useState<ResolverCandidate | null>(null);
  const [connection, setConnection] = useState<AgentConnection | null>(null);
  const [resolving, setResolving] = useState(false);
  const [resolverError, setResolverError] = useState("");
  const hasTask = Boolean(request);

  useEffect(() => {
    let active = true;
    getAuthSession()
      .then((authSession) => {
        if (!active) return;
        if (!authSession.onboarding_completed) {
          router.replace("/onboarding");
          return;
        }
        setAutoConnect(authSession.approval_mode === "auto_connect");
        setSession(authSession);
      })
      .catch(() => {
        if (active) router.replace("/auth");
      })
      .finally(() => {
        if (active) setCheckingSession(false);
      });
    return () => {
      active = false;
    };
  }, [router]);

  async function signOut() {
    await logoutAccount();
    router.replace("/");
  }

  function selectTab(tab: WorkspaceTab) {
    setActiveTab(tab);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    const cleanMessage = message.trim();
    if (!cleanMessage) return;
    setRequest(cleanMessage);
    setMessage("");
    setApproved(false);
    setCandidate(null);
    setConnection(null);
    setResolverError("");
    setResolving(true);
    try {
      const task = await discoverAgents(cleanMessage);
      const topCandidate = task.candidates[0] || null;
      setCandidate(topCandidate);
      if (topCandidate) {
        const nextConnection = await requestAgentConnection(task.task_id, topCandidate.network_handle, ["task_context"]);
        setConnection(nextConnection);
        setApproved(nextConnection.status === "approved" || nextConnection.status === "active");
      }
    } catch (caught) {
      setResolverError((caught as ApiError).message);
    } finally {
      setResolving(false);
    }
  }

  async function approveConnection() {
    if (!connection) return;
    setResolverError("");
    try {
      const updated = await approveAgentConnection(connection.connection_id, connection.requested_scopes);
      setConnection(updated);
      setApproved(updated.status === "approved" || updated.status === "active");
    } catch (caught) {
      setResolverError((caught as ApiError).message);
    }
  }

  function handleComposerKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    }
  }

  const title = tabTitles[activeTab];
  const initials = session?.user.display_name.split(" ").map((part) => part[0]).join("").slice(0, 2).toUpperCase() || "AG";

  if (checkingSession || !session) {
    return <div className="auth-loading"><span><Icon name="spark" /></span><p>Opening your personal agent...</p></div>;
  }

  return (
    <div className="dashboard-shell">
      <aside className="dashboard-rail">
        <DashboardBrand />
        <WorkspaceNav activeTab={activeTab} onSelect={selectTab} />
        <div className="rail-agent">
          <span className="agent-orb" />
          <div><strong>Agen</strong><span><i /> Online</span></div>
          <button type="button" aria-label="Open agent menu">...</button>
        </div>
      </aside>

      <header className="dashboard-mobile-head">
        <DashboardBrand />
        <button type="button" className="dashboard-icon-button" aria-label="Open notifications"><Icon name="bell" /></button>
      </header>

      <main className="dashboard-main">
        <header className="dashboard-heading">
          <div><p>{title.eyebrow}</p><h1>{title.title}</h1></div>
          <div className="dashboard-heading__actions">
            <button type="button" className="dashboard-icon-button" aria-label="Notifications"><Icon name="bell" /><i /></button>
            <button type="button" className="dashboard-avatar" aria-label="Open profile" onClick={() => selectTab("settings")}>{initials}</button>
          </div>
        </header>

        {activeTab === "agent" ? (
          <AgentView
            approved={approved}
            autoConnect={autoConnect}
            hasTask={hasTask}
            listening={listening}
            message={message}
            request={request}
            candidate={candidate}
            resolving={resolving}
            resolverError={resolverError}
            onApprove={approveConnection}
            onChoosePrompt={setMessage}
            onMessageChange={setMessage}
            onSubmit={submit}
            onComposerKeyDown={handleComposerKeyDown}
            onToggleListening={() => setListening((value) => !value)}
            onViewTasks={() => selectTab("tasks")}
          />
        ) : null}
        {activeTab === "tasks" ? <TasksView approved={approved} candidate={candidate} hasTask={hasTask} request={request} resolving={resolving} onApprove={approveConnection} onAskAgent={() => selectTab("agent")} /> : null}
        {activeTab === "studio" ? <BusinessAgentsView /> : null}
        {activeTab === "activity" ? <ActivityView hasTask={hasTask} /> : null}
        {activeTab === "settings" ? <SettingsView agent={session.personal_agent} autoConnect={autoConnect} email={session.user.email} onSignOut={signOut} onToggleAutoConnect={() => setAutoConnect((value) => !value)} /> : null}
      </main>

      <nav className="dashboard-mobile-nav" aria-label="Dashboard navigation">
        {tabs.map((tab) => <TabButton key={tab.id} tab={tab} active={activeTab === tab.id} onSelect={selectTab} compact />)}
      </nav>
    </div>
  );
}

function AgentView(props: {
  approved: boolean;
  autoConnect: boolean;
  candidate: ResolverCandidate | null;
  hasTask: boolean;
  listening: boolean;
  message: string;
  request: string;
  resolving: boolean;
  resolverError: string;
  onApprove: () => void;
  onChoosePrompt: (prompt: string) => void;
  onMessageChange: (message: string) => void;
  onSubmit: (event: FormEvent) => void;
  onComposerKeyDown: (event: KeyboardEvent<HTMLTextAreaElement>) => void;
  onToggleListening: () => void;
  onViewTasks: () => void;
}) {
  return (
    <div className="agent-layout">
      <section className="agent-chat" aria-label="Conversation with Agen">
        {props.listening ? (
          <VoiceListeningView onCancel={props.onToggleListening} onFinish={props.onToggleListening} />
        ) : (
          <>
            <div className="agent-chat__bar"><span><i />Agen is online</span><span><Icon name="shield" />Private conversation</span></div>
            <div className="agent-chat__messages" aria-live="polite">
          {props.hasTask ? (
            <div className="chat-thread">
              <div className="chat-time">Just now</div>
              <div className="chat-bubble chat-bubble--user">{props.request}</div>
              <div className="chat-agent-row"><span className="chat-agent-icon"><Icon name="spark" /></span><div className="chat-bubble chat-bubble--agent">{props.resolving ? "I understand. I am checking the Agen Resolver for a verified specialist." : props.resolverError ? `I could not complete discovery: ${props.resolverError}` : props.candidate ? `I found ${props.candidate.name}. ${props.approved ? "The scoped connection is approved and ready." : "I need your approval before I connect."}` : "I could not find a verified agent with the required capabilities yet."}</div></div>
              {props.candidate ? <ConnectionCard approved={props.approved} candidate={props.candidate} onApprove={props.onApprove} /> : null}
            </div>
          ) : (
            <div className="agent-welcome">
              <span className="agent-welcome__icon"><Icon name="spark" /></span>
              <p>Good afternoon</p>
              <h2>What would you like<br />to get done?</h2>
              <span>Ask naturally. Agen will work out the steps.</span>
              <div className="prompt-grid">{prompts.map((prompt) => <button type="button" key={prompt} onClick={() => props.onChoosePrompt(prompt)}>{prompt}<Icon name="chevron" /></button>)}</div>
            </div>
          )}
            </div>
            <div className="agent-composer-wrap">
              <form className="agent-composer" onSubmit={props.onSubmit}>
                <textarea rows={1} value={props.message} onChange={(event) => props.onMessageChange(event.target.value)} onKeyDown={props.onComposerKeyDown} placeholder="Message Agen..." aria-label="Message Agen" />
                <button type="button" onClick={props.onToggleListening} aria-label="Talk to Agen"><Icon name="mic" /></button>
                <button type="submit" className="agent-composer__send" aria-label="Send message"><Icon name="send" /></button>
              </form>
              <span>Enter to send, Shift + Enter for a new line</span>
            </div>
          </>
        )}
      </section>

      <aside className="agent-context">
        <section className="context-card context-card--task">
          <div className="context-card__head"><span>Current task</span>{props.hasTask ? <b>In progress</b> : <b>None</b>}</div>
          {props.hasTask ? <><h3>{props.request}</h3><div className="mini-progress"><span className="is-done">Understood</span><span className="is-done">Agent matched</span><span className={props.approved ? "is-done" : ""}>Connected</span></div><button type="button" onClick={props.onViewTasks}>View task details <Icon name="chevron" /></button></> : <div className="context-empty"><Icon name="clock" /><p>Your current task will appear here as Agen works.</p></div>}
        </section>
        <section className="context-card"><div className="context-card__head"><span>Connection mode</span><Icon name="shield" /></div><div className="mode-row"><div><strong>{props.autoConnect ? "Automatic" : "Ask every time"}</strong><small>{props.autoConnect ? "Trusted agents can connect automatically" : "You approve each specialist connection"}</small></div><span className={props.autoConnect ? "mode-indicator mode-indicator--auto" : "mode-indicator"}>{props.autoConnect ? "Auto" : "Manual"}</span></div></section>
        <section className="context-privacy"><Icon name="shield" /><div><strong>Private by design</strong><span>Your data is only shared when a task requires it.</span></div></section>
      </aside>
    </div>
  );
}

function VoiceListeningView({ onCancel, onFinish }: { onCancel: () => void; onFinish: () => void }) {
  return (
    <div className="voice-session" role="dialog" aria-modal="true" aria-labelledby="voice-title">
      <div className="voice-session__top">
        <span><Icon name="shield" />Voice stays private</span>
        <button type="button" onClick={onCancel}>Cancel</button>
      </div>
      <div className="voice-session__body">
        <div className="voice-orb-wrap">
          <span className="voice-ring voice-ring--outer" />
          <span className="voice-ring voice-ring--inner" />
          <button type="button" className="voice-orb" onClick={onFinish} aria-label="Finish speaking"><Icon name="spark" /></button>
        </div>
        <p className="voice-session__label"><i /> Listening</p>
        <h2 id="voice-title">I am listening.</h2>
        <p className="voice-session__hint">Speak naturally. Pause when you are finished.</p>
        <div className="voice-wave" aria-hidden="true">
          {voiceBars.map((height, index) => <i key={`${height}-${index}`} style={{ "--bar-height": `${height}%`, "--bar-delay": `${index * -0.07}s` } as React.CSSProperties} />)}
        </div>
        <p className="voice-transcript">Go ahead, tell me what you need...</p>
      </div>
      <div className="voice-session__controls">
        <button type="button" className="voice-cancel" onClick={onCancel}>Cancel</button>
        <button type="button" className="voice-finish" onClick={onFinish}><Icon name="mic" /><span>Done speaking</span></button>
      </div>
    </div>
  );
}

function TasksView({ approved, candidate, hasTask, request, resolving, onApprove, onAskAgent }: { approved: boolean; candidate: ResolverCandidate | null; hasTask: boolean; request: string; resolving: boolean; onApprove: () => void; onAskAgent: () => void }) {
  return <section className="tab-view"><div className="view-summary"><article><span>Active</span><strong>{hasTask ? "1" : "0"}</strong><small>Task being handled</small></article><article><span>Completed</span><strong>12</strong><small>This month</small></article><article><span>Time saved</span><strong>8.4h</strong><small>This month</small></article></div><div className="view-panel"><div className="view-panel__head"><div><span className="view-kicker">Active work</span><h2>Tasks in progress</h2></div><button type="button" onClick={onAskAgent}>New request</button></div>{hasTask ? <div className="task-detail"><div className="task-detail__top"><span className="task-symbol"><Icon name="spark" /></span><div><h3>{request}</h3><p>Started just now</p></div><b>{resolving ? "Discovering" : approved ? "Working" : candidate ? "Needs approval" : "No match"}</b></div><div className="task-detail__progress"><span className="is-done">Request understood</span><span className={candidate ? "is-done" : ""}>Specialist found</span><span className={approved ? "is-done" : ""}>Secure connection</span><span>Result delivered</span></div>{approved ? <p className="task-note">Agen established a scoped connection. The provider can now work on the approved task context.</p> : candidate ? <ConnectionCard approved={false} candidate={candidate} onApprove={onApprove} /> : <p className="task-note">{resolving ? "The resolver is checking verified capabilities and availability." : "No verified provider currently matches this task."}</p>}</div> : <EmptyView icon="tasks" title="No active tasks" copy="Ask Agen to handle something and track every step here." action="Ask Agen" onAction={onAskAgent} />}</div></section>;
}

function ActivityView({ hasTask }: { hasTask: boolean }) {
  return <section className="tab-view"><div className="view-panel"><div className="view-panel__head"><div><span className="view-kicker">Audit trail</span><h2>Recent activity</h2></div><button type="button">Export</button></div><div className="activity-feed">{hasTask ? <ActivityItem icon="spark" title="New request received" detail="Agen understood your goal and created a task plan." time="Just now" /> : null}<ActivityItem icon="shield" title="Privacy check completed" detail="Connection permissions and sharing preferences are up to date." time="Today, 9:30" /><ActivityItem icon="tasks" title="Restaurant booking completed" detail="Agen reserved a table for two and added it to your schedule." time="Yesterday" /><ActivityItem icon="activity" title="Weekly summary prepared" detail="You saved an estimated 2.1 hours across four completed tasks." time="Mon, 8:00" /></div></div></section>;
}

function BusinessAgentsView() {
  const [mode, setMode] = useState<"managed" | "external">("managed");
  const [createdAgent, setCreatedAgent] = useState<{ name: string; company: string; id: string } | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  async function submitBusinessAgent(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    const form = new FormData(event.currentTarget);
    const name = String(form.get("name") || "Business agent");
    const company = String(form.get("company") || "Your business");
    try {
      const agent = await createBusinessAgent({
        name,
        company_name: company,
        category: String(form.get("category") || "Other"),
        hosting_type: mode,
        endpoint: mode === "external" ? String(form.get("endpoint") || "") : undefined,
        summary: mode === "managed" ? String(form.get("summary") || "") : undefined,
        capabilities: String(form.get("capabilities") || "").split(",").map((item) => item.trim()).filter(Boolean),
      });
      setCreatedAgent({ name: agent.name, company: agent.company_name, id: agent.agent_id });
    } catch (caught) {
      const apiError = caught as ApiError;
      const fieldMessage = apiError.fields
        ? Object.values(apiError.fields).flat().find((value) => typeof value === "string")
        : undefined;
      setError(fieldMessage || apiError.message);
    } finally {
      setSubmitting(false);
    }
  }

  if (createdAgent) {
    return (
      <section className="tab-view studio-success">
        <div className="studio-success__mark"><Icon name="shield" /></div>
        <span className="view-kicker">Agent identity created</span>
        <h2>{createdAgent.name} is ready for verification.</h2>
        <p>{createdAgent.company} now has a draft business agent. Its identity is permanent, but it will not appear on the network until verification is complete.</p>
        <div className="agent-id-block"><span>Unique agent ID</span><code>{createdAgent.id}</code></div>
        <div className="studio-next"><div><b>1</b><span><strong>Verify ownership</strong><small>Confirm your business identity.</small></span></div><div><b>2</b><span><strong>{mode === "external" ? "Test endpoint" : "Configure behavior"}</strong><small>{mode === "external" ? "We will run a secure handshake." : "Add instructions, tools, and limits."}</small></span></div><div><b>3</b><span><strong>Activate on the network</strong><small>Begin receiving trusted requests.</small></span></div></div>
        <div className="studio-success__actions"><button type="button" onClick={() => setCreatedAgent(null)}>Add another agent</button><button type="button" className="is-primary">Continue setup <Icon name="chevron" /></button></div>
      </section>
    );
  }

  return (
    <section className="tab-view studio-view">
      <div className="studio-intro"><span className="view-kicker">For businesses</span><h2>How do you want to bring your agent online?</h2><p>Create an agent hosted by Agen, or connect one your team already operates. Both receive a unique identity and independent trust score.</p></div>
      <div className="studio-mode" role="radiogroup" aria-label="Agent setup method">
        <button type="button" role="radio" aria-checked={mode === "managed"} className={mode === "managed" ? "is-selected" : ""} onClick={() => setMode("managed")}><span><Icon name="plus" /></span><div><strong>Create a custom agent</strong><p>Build its behavior, tools, and permissions inside Agen.</p></div><i /></button>
        <button type="button" role="radio" aria-checked={mode === "external"} className={mode === "external" ? "is-selected" : ""} onClick={() => setMode("external")}><span><Icon name="link" /></span><div><strong>Connect an existing agent</strong><p>Register your HTTPS endpoint and keep hosting it yourself.</p></div><i /></button>
      </div>
      <form className="studio-form" onSubmit={submitBusinessAgent}>
        <div className="studio-form__head"><div><span className="view-kicker">Business identity</span><h3>{mode === "managed" ? "Create your agent" : "Connect your endpoint"}</h3></div><span>Step 1 of 3</span></div>
        <div className="studio-fields">
          <label><span>Agent name</span><input name="name" required placeholder="e.g. Acme Support Agent" /></label>
          <label><span>Business name</span><input name="company" required placeholder="e.g. Acme Ltd" /></label>
          <label><span>Category</span><select name="category" required defaultValue=""><option value="" disabled>Select a category</option><option>Customer support</option><option>Commerce</option><option>Travel and hospitality</option><option>Financial services</option><option>Professional services</option><option>Other</option></select></label>
          <label><span>Capabilities</span><input name="capabilities" placeholder="Booking, support, order tracking" /></label>
          {mode === "external" ? <label className="studio-field--wide"><span>Agent endpoint</span><div className="endpoint-input"><Icon name="link" /><input name="endpoint" type="url" required pattern="https://.*" placeholder="https://api.yourbusiness.com/agent" /></div><small>HTTPS is required. We will verify ownership with a signed challenge.</small></label> : <label className="studio-field--wide"><span>What should this agent do?</span><textarea name="summary" required rows={3} placeholder="Describe the requests it handles and the outcomes it can deliver." /></label>}
        </div>
        <div className="studio-notice"><Icon name="shield" /><p><strong>Trust starts with verification</strong><span>This agent begins at a baseline score of 40. Identity, successful work, attestations, and disputes change its score over time.</span></p></div>
        {error ? <div className="auth-error studio-error" role="alert">{error}</div> : null}
        <div className="studio-form__footer"><span>You can finish configuration later.</span><button type="submit" disabled={submitting}>{submitting ? "Creating identity..." : "Create agent identity"} <Icon name="chevron" /></button></div>
      </form>
    </section>
  );
}

function WorkspaceNav({ activeTab, onSelect }: { activeTab: WorkspaceTab; onSelect: (tab: WorkspaceTab) => void }) {
  return <nav className="dashboard-nav" aria-label="Dashboard navigation">{tabs.map((tab) => <TabButton key={tab.id} tab={tab} active={activeTab === tab.id} onSelect={onSelect} />)}</nav>;
}

function TabButton({ tab, active, onSelect, compact = false }: { tab: (typeof tabs)[number]; active: boolean; onSelect: (tab: WorkspaceTab) => void; compact?: boolean }) {
  const compactLabel = tab.id === "agent" ? "Agent" : tab.id === "studio" ? "Studio" : tab.label;
  return <button type="button" className={`${compact ? "mobile-tab" : "dashboard-nav__item"}${active ? " is-active" : ""}`} onClick={() => onSelect(tab.id)} aria-current={active ? "page" : undefined}><Icon name={tab.icon} /><span>{compact ? compactLabel : tab.label}</span></button>;
}

function ConnectionCard({ approved, candidate, onApprove }: { approved: boolean; candidate: ResolverCandidate; onApprove: () => void }) {
  return <div className="connect-card"><div><span className="connect-logo">A+</span><p><strong>{candidate.name}</strong><small><Icon name="shield" />{candidate.trust_score}% network trust · @{candidate.network_handle}</small></p><b>Rank #{candidate.rank}</b></div><p>{candidate.reasons[0]}. Only approved task context will be shared.</p><button type="button" onClick={onApprove} disabled={approved}>{approved ? "Connected securely" : "Approve scoped connection"}<Icon name={approved ? "shield" : "chevron"} /></button></div>;
}

function ActivityItem({ icon, title, detail, time }: { icon: string; title: string; detail: string; time: string }) {
  return <article className="activity-item"><span><Icon name={icon} /></span><div><strong>{title}</strong><p>{detail}</p></div><time>{time}</time></article>;
}

function EmptyView({ icon, title, copy, action, onAction }: { icon: string; title: string; copy: string; action: string; onAction: () => void }) {
  return <div className="view-empty"><span><Icon name={icon} /></span><h3>{title}</h3><p>{copy}</p><button type="button" onClick={onAction}>{action}</button></div>;
}

function DashboardBrand() {
  return <Link className="dashboard-brand" href="/" aria-label="Agen homepage"><span><Icon name="spark" /></span><strong>agen</strong></Link>;
}
