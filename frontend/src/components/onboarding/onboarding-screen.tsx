"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Icon } from "@/components/workspace/icons";
import { ApiError, ApprovalMode, AuthSession, completeOnboarding, getAuthSession } from "@/lib/client-api";

const goals = [
  { id: "work", label: "Work", detail: "Planning and daily execution", icon: "tasks" },
  { id: "research", label: "Research", detail: "Find, compare, and explain", icon: "activity" },
  { id: "travel", label: "Travel", detail: "Plan trips and coordinate bookings", icon: "business" },
  { id: "shopping", label: "Shopping", detail: "Compare options and find value", icon: "link" },
  { id: "personal_admin", label: "Personal admin", detail: "Schedules, reminders, and errands", icon: "clock" },
  { id: "business", label: "Business", detail: "Operations and customer workflows", icon: "spark" },
];

const approvalModes: Array<{ id: ApprovalMode; label: string; detail: string; badge?: string }> = [
  { id: "balanced", label: "Balanced", detail: "Agen handles low-risk steps and asks before sharing data, connecting agents, or spending.", badge: "Recommended" },
  { id: "always_ask", label: "Always ask", detail: "Agen requests your approval before every external connection or action." },
  { id: "auto_connect", label: "Auto-connect", detail: "Agen may connect to verified agents automatically, but still asks before sensitive actions." },
];

const integrations = [
  { id: "email_calendar", label: "Email & calendar", detail: "Coordinate messages and schedules", icon: "activity" },
  { id: "files", label: "Files & documents", detail: "Work with files you approve", icon: "tasks" },
  { id: "payments", label: "Payments", detail: "Prepare purchases with approval", icon: "business" },
  { id: "business_tools", label: "Business tools", detail: "Connect your existing workspace", icon: "link" },
];

const stepCopy = [
  { eyebrow: "Your personal agent", title: "First, make it yours.", detail: "Your agent already has a permanent network identity. Give it the name you want to use every day." },
  { eyebrow: "Your priorities", title: "What should it help with?", detail: "Choose the areas that matter now. You can teach your agent more over time." },
  { eyebrow: "Your control", title: "How should it ask?", detail: "Set the approval style for actions and agent connections. You can change this later." },
  { eyebrow: "Your tools", title: "What might you connect?", detail: "This only prepares your workspace. Nothing is connected until you approve it inside Settings." },
];

export function OnboardingScreen() {
  const router = useRouter();
  const [session, setSession] = useState<AuthSession | null>(null);
  const [step, setStep] = useState(0);
  const [agentName, setAgentName] = useState("");
  const [selectedGoals, setSelectedGoals] = useState<string[]>([]);
  const [approvalMode, setApprovalMode] = useState<ApprovalMode>("balanced");
  const [selectedIntegrations, setSelectedIntegrations] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    getAuthSession()
      .then((authSession) => {
        if (!active) return;
        if (authSession.onboarding_completed) {
          router.replace("/app");
          return;
        }
        setSession(authSession);
        setAgentName(authSession.personal_agent.name);
      })
      .catch(() => {
        if (active) router.replace("/auth");
      });
    return () => { active = false; };
  }, [router]);

  function toggleSelection(value: string, selected: string[], update: (values: string[]) => void) {
    update(selected.includes(value) ? selected.filter((item) => item !== value) : [...selected, value]);
  }

  function canContinue() {
    if (step === 0) return Boolean(agentName.trim());
    if (step === 1) return selectedGoals.length > 0;
    return true;
  }

  async function continueFlow() {
    if (!canContinue()) return;
    setError("");
    if (step < 3) {
      setStep((current) => current + 1);
      return;
    }
    setSubmitting(true);
    try {
      await completeOnboarding({
        agent_name: agentName.trim(),
        goals: selectedGoals,
        approval_mode: approvalMode,
        integrations: selectedIntegrations,
      });
      router.replace("/app");
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

  if (!session) {
    return <main className="auth-loading"><span><Icon name="spark" /></span><p>Preparing your agent...</p></main>;
  }

  const copy = stepCopy[step];
  return (
    <main className="onboarding-page">
      <aside className="onboarding-story">
        <div className="onboarding-brand"><span><Icon name="spark" /></span><strong>agen</strong></div>
        <div className="onboarding-story__center">
          <span className="onboarding-orbit"><i /><i /><i /><b><Icon name="spark" /></b></span>
          <p>Your agent identity is ready</p>
          <code>@{session.personal_agent.network_handle}</code>
        </div>
        <div className="onboarding-trust-note"><Icon name="shield" /><div><strong>Trust is earned, never selected.</strong><span>Your agent’s score is calculated from identity verification and proven network activity.</span></div></div>
      </aside>

      <section className="onboarding-workspace">
        <header className="onboarding-head">
          <span>Set up your agent</span>
          <div className="onboarding-progress" aria-label={`Step ${step + 1} of 4`}>
            {[0, 1, 2, 3].map((item) => <i key={item} className={item <= step ? "is-active" : ""} />)}
          </div>
          <small>{step + 1} / 4</small>
        </header>

        <div className="onboarding-content">
          <div className="onboarding-copy"><span>{copy.eyebrow}</span><h1>{copy.title}</h1><p>{copy.detail}</p></div>

          {step === 0 ? (
            <div className="onboarding-name-step">
              <span className="onboarding-agent-mark"><Icon name="spark" /></span>
              <label><span>Agent name</span><input value={agentName} onChange={(event) => setAgentName(event.target.value)} maxLength={120} autoFocus /></label>
              <p>You can rename your agent later. Its permanent Agent ID will not change.</p>
            </div>
          ) : null}

          {step === 1 ? (
            <div className="onboarding-option-grid">
              {goals.map((goal) => <ChoiceCard key={goal.id} {...goal} selected={selectedGoals.includes(goal.id)} onClick={() => toggleSelection(goal.id, selectedGoals, setSelectedGoals)} />)}
            </div>
          ) : null}

          {step === 2 ? (
            <div className="onboarding-mode-list">
              {approvalModes.map((mode) => (
                <button type="button" key={mode.id} className={approvalMode === mode.id ? "is-selected" : ""} onClick={() => setApprovalMode(mode.id)}>
                  <i /><div><span>{mode.label}{mode.badge ? <b>{mode.badge}</b> : null}</span><p>{mode.detail}</p></div><Icon name="chevron" />
                </button>
              ))}
              <div className="onboarding-policy"><Icon name="shield" /><span><strong>Always protected</strong> Payments, sensitive data, and irreversible actions still require explicit approval.</span></div>
            </div>
          ) : null}

          {step === 3 ? (
            <div className="onboarding-option-grid onboarding-option-grid--tools">
              {integrations.map((integration) => <ChoiceCard key={integration.id} {...integration} selected={selectedIntegrations.includes(integration.id)} onClick={() => toggleSelection(integration.id, selectedIntegrations, setSelectedIntegrations)} />)}
              <p className="onboarding-skip-note">Optional. You can skip this and connect tools from Settings later.</p>
            </div>
          ) : null}

          {error ? <div className="auth-error" role="alert">{error}</div> : null}
        </div>

        <footer className="onboarding-actions">
          <button type="button" className="onboarding-back" onClick={() => setStep((current) => Math.max(0, current - 1))} disabled={step === 0}>Back</button>
          <button type="button" className="onboarding-next" onClick={continueFlow} disabled={!canContinue() || submitting}>{submitting ? "Creating your workspace..." : step === 3 ? "Enter my dashboard" : "Continue"}<Icon name="chevron" /></button>
        </footer>
      </section>
    </main>
  );
}

function ChoiceCard({ label, detail, icon, selected, onClick }: { label: string; detail: string; icon: string; selected: boolean; onClick: () => void }) {
  return (
    <button type="button" className={selected ? "onboarding-choice is-selected" : "onboarding-choice"} aria-pressed={selected} onClick={onClick}>
      <span><Icon name={icon} /></span><div><strong>{label}</strong><small>{detail}</small></div><i />
    </button>
  );
}
