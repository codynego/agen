"use client";

import { useState } from "react";

import { Icon } from "@/components/workspace/icons";
import type { AuthSession } from "@/lib/client-api";

type SettingsTab = "agent" | "integrations" | "preferences" | "security";

type SettingsViewProps = {
  agent: AuthSession["personal_agent"];
  autoConnect: boolean;
  email: string;
  onSignOut: () => void;
  onToggleAutoConnect: () => void;
};

const settingsTabs: Array<{ id: SettingsTab; label: string; detail: string; icon: string }> = [
  { id: "agent", label: "Agent info", detail: "Identity and trust", icon: "spark" },
  { id: "integrations", label: "Integrations", detail: "Tools your agent can use", icon: "link" },
  { id: "preferences", label: "Preferences", detail: "Connections and approvals", icon: "settings" },
  { id: "security", label: "Security", detail: "Account and sessions", icon: "shield" },
];

const integrations = [
  { name: "Agent Network", description: "Find and collaborate with verified specialist agents.", icon: "spark", status: "Core connection" },
  { name: "Email & calendar", description: "Draft email, coordinate meetings, and manage your schedule.", icon: "activity", status: "Available soon" },
  { name: "Files & documents", description: "Work with approved files and deliver finished documents.", icon: "tasks", status: "Available soon" },
  { name: "Payments", description: "Request approval before completing purchases or paid tasks.", icon: "business", status: "Available soon" },
];

export function SettingsView({ agent, autoConnect, email, onSignOut, onToggleAutoConnect }: SettingsViewProps) {
  const [activeTab, setActiveTab] = useState<SettingsTab>("agent");

  return (
    <section className="tab-view settings-center">
      <aside className="settings-subnav" aria-label="Settings sections">
        <div className="settings-subnav__intro">
          <span>Settings</span>
          <p>Manage your personal agent and the tools it can access.</p>
        </div>
        <div className="settings-subnav__items" role="tablist" aria-label="Agent settings">
          {settingsTabs.map((tab) => (
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === tab.id}
              aria-controls={`settings-panel-${tab.id}`}
              className={activeTab === tab.id ? "is-active" : ""}
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
            >
              <span className="settings-subnav__icon"><Icon name={tab.icon} /></span>
              <span><strong>{tab.label}</strong><small>{tab.detail}</small></span>
              <Icon name="chevron" />
            </button>
          ))}
        </div>
      </aside>

      <div className="settings-content">
        {activeTab === "agent" ? <AgentInfoPanel agent={agent} /> : null}
        {activeTab === "integrations" ? <IntegrationsPanel /> : null}
        {activeTab === "preferences" ? (
          <PreferencesPanel autoConnect={autoConnect} onToggleAutoConnect={onToggleAutoConnect} />
        ) : null}
        {activeTab === "security" ? <SecurityPanel email={email} onSignOut={onSignOut} /> : null}
      </div>
    </section>
  );
}

function PanelHeader({ eyebrow, title, description }: { eyebrow: string; title: string; description: string }) {
  return (
    <header className="settings-panel__header">
      <span>{eyebrow}</span>
      <h2>{title}</h2>
      <p>{description}</p>
    </header>
  );
}

function AgentInfoPanel({ agent }: { agent: AuthSession["personal_agent"] }) {
  return (
    <div id="settings-panel-agent" role="tabpanel" className="settings-panel">
      <PanelHeader eyebrow="Personal agent" title="Identity and trust" description="The permanent identity other agents use to discover, verify, and safely work with your agent." />

      <article className="agent-identity-card">
        <div className="agent-identity-card__top">
          <span className="agent-identity-card__mark"><Icon name="spark" /></span>
          <div><span>Active personal agent</span><h3>{agent.name}</h3></div>
          <span className="agent-identity-card__status"><i /> Online</span>
        </div>
        <div className="agent-identity-card__id">
          <span>Network handle</span>
          <code>@{agent.network_handle}</code>
          <small>Unique across the entire Agen network</small>
        </div>
        <div className="agent-identity-card__id">
          <span>Agent ID</span>
          <code>{agent.agent_id}</code>
          <small>Permanent and independently verifiable</small>
        </div>
        <div className="agent-identity-card__trust">
          <div><span>Network trust score</span><strong>{agent.trust_score}%</strong></div>
          <div className="agent-trust-meter"><i style={{ width: `${Math.min(Number(agent.trust_score), 100)}%` }} /></div>
          <p><Icon name="shield" /> {agent.trust_level} standing across the agent network</p>
        </div>
      </article>

      <div className="settings-detail-grid">
        <article>
          <span className="settings-detail-grid__icon"><Icon name="shield" /></span>
          <div><strong>Verified identity</strong><p>Your agent signs network requests with its unique identity.</p></div>
          <span className="settings-pill">Protected</span>
        </article>
        <article>
          <span className="settings-detail-grid__icon"><Icon name="activity" /></span>
          <div><strong>Core capabilities</strong><p>Planning, research, coordination, and agent discovery.</p></div>
          <span className="settings-pill settings-pill--neutral">4 enabled</span>
        </article>
      </div>
    </div>
  );
}

function IntegrationsPanel() {
  return (
    <div id="settings-panel-integrations" role="tabpanel" className="settings-panel">
      <PanelHeader eyebrow="Internal integrations" title="Tools your agent can use" description="Review every system Agen can access. New connections will always require your approval before they are activated." />
      <div className="integration-summary">
        <div><Icon name="link" /><span><strong>1 active connection</strong><small>Your network connection is healthy</small></span></div>
        <span><i /> Systems operational</span>
      </div>
      <div className="integration-list">
        {integrations.map((integration, index) => (
          <article key={integration.name}>
            <span className="integration-list__icon"><Icon name={integration.icon} /></span>
            <div><strong>{integration.name}</strong><p>{integration.description}</p></div>
            {index === 0 ? <span className="settings-pill">Connected</span> : <button type="button" disabled>{integration.status}</button>}
          </article>
        ))}
      </div>
      <div className="settings-note"><Icon name="shield" /><p><strong>You remain in control.</strong> Integration credentials will be encrypted and access can be revoked from this page.</p></div>
    </div>
  );
}

function PreferencesPanel({ autoConnect, onToggleAutoConnect }: { autoConnect: boolean; onToggleAutoConnect: () => void }) {
  return (
    <div id="settings-panel-preferences" role="tabpanel" className="settings-panel">
      <PanelHeader eyebrow="Agent behaviour" title="Connections and approvals" description="Choose how independently your agent can act when it finds another agent or needs access to a tool." />
      <div className="settings-list">
        <div className="setting-row">
          <div><strong>Auto-connect to trusted agents</strong><p>Allow Agen to connect automatically when an agent meets your trust rules.</p></div>
          <button type="button" className="toggle" aria-label="Toggle auto-connect" aria-pressed={autoConnect} onClick={onToggleAutoConnect} />
        </div>
        <div className="setting-row">
          <div><strong>Network verification policy</strong><p>Only consider agents the network currently classifies as high trust.</p></div>
          <span className="setting-value">High trust only</span>
        </div>
        <div className="setting-row">
          <div><strong>Task-only data sharing</strong><p>Share only the minimum information another agent needs to complete a task.</p></div>
          <span className="setting-status">On</span>
        </div>
      </div>
    </div>
  );
}

function SecurityPanel({ email, onSignOut }: { email: string; onSignOut: () => void }) {
  return (
    <div id="settings-panel-security" role="tabpanel" className="settings-panel">
      <PanelHeader eyebrow="Account security" title="Access and active session" description="Your dashboard uses a short-lived email code, so there is no password to remember or expose." />
      <div className="security-account-card">
        <span className="security-account-card__avatar">{email.slice(0, 1).toUpperCase()}</span>
        <div><span>Signed in as</span><strong>{email}</strong></div>
        <span className="settings-pill"><i /> Current session</span>
      </div>
      <div className="settings-list">
        <div className="setting-row">
          <div><strong>Passwordless access</strong><p>A new verification code is required when your session ends.</p></div>
          <span className="setting-status">Enabled</span>
        </div>
        <div className="setting-row">
          <div><strong>End this session</strong><p>Sign out of Agen on this device. Your agent and task history remain safe.</p></div>
          <button type="button" className="settings-signout" onClick={onSignOut}>Sign out <Icon name="chevron" /></button>
        </div>
      </div>
    </div>
  );
}
