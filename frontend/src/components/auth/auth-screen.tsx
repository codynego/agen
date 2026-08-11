"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { Icon } from "@/components/workspace/icons";
import { ApiError, requestLoginCode, verifyLoginCode } from "@/lib/client-api";

type AuthStep = "email" | "code";

function errorMessage(caught: unknown) {
  const apiError = caught as ApiError;
  const fieldMessage = apiError.fields
    ? Object.values(apiError.fields).flat().find((value) => typeof value === "string")
    : undefined;
  return fieldMessage || apiError.message;
}

export function AuthScreen() {
  const router = useRouter();
  const [step, setStep] = useState<AuthStep>("email");
  const [email, setEmail] = useState("");
  const [challengeId, setChallengeId] = useState("");
  const [code, setCode] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  async function requestCode() {
    const challenge = await requestLoginCode({ email });
    setChallengeId(challenge.challenge_id);
    setNotice("We sent a six-digit code. It expires in 10 minutes.");
    setStep("code");
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      if (step === "email") {
        await requestCode();
      } else {
        const session = await verifyLoginCode({ challenge_id: challengeId, code });
        router.replace(session.onboarding_completed ? "/app" : "/onboarding");
      }
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setSubmitting(false);
    }
  }

  async function resendCode() {
    setSubmitting(true);
    setError("");
    setCode("");
    try {
      await requestCode();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setSubmitting(false);
    }
  }

  function changeEmail() {
    setStep("email");
    setChallengeId("");
    setCode("");
    setNotice("");
    setError("");
  }

  return (
    <main className="auth-page">
      <section className="auth-story">
        <Link className="dashboard-brand auth-brand" href="/"><span><Icon name="spark" /></span><strong>agen</strong></Link>
        <div className="auth-story__copy"><span>Your personal agent</span><h1>Ask once.<br /><em>Move on.</em></h1><p>Agen finds the right services, coordinates the work, and brings the result back to you.</p></div>
        <div className="auth-story__signal"><span className="agent-orb" /><div><strong>Agen is ready</strong><small>Private by default. Always under your control.</small></div></div>
      </section>
      <section className="auth-panel">
        <div className="auth-card">
          <div className="auth-mobile-brand"><Link className="dashboard-brand" href="/"><span><Icon name="spark" /></span><strong>agen</strong></Link></div>
          <span className="view-kicker">{step === "email" ? "Welcome to Agen" : "Check your email"}</span>
          <h2>{step === "email" ? "Meet your agent." : "Enter your code."}</h2>
          <p>{step === "email" ? "Enter your email to continue. New accounts get a personal agent automatically." : <>We sent a code to <strong>{email}</strong>.</>}</p>
          <form className="auth-form" onSubmit={submit}>
            {step === "email" ? (
              <label><span>Email address</span><input name="email" type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} required autoFocus placeholder="you@example.com" /></label>
            ) : (
              <label><span>Six-digit code</span><input className="auth-code-input" name="code" type="text" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} value={code} onChange={(event) => setCode(event.target.value.replace(/\D/g, ""))} required autoFocus placeholder="000000" /></label>
            )}
            {notice && !error ? <div className="auth-notice" role="status">{notice}</div> : null}
            {error ? <div className="auth-error" role="alert">{error}</div> : null}
            <button type="submit" disabled={submitting || (step === "code" && code.length !== 6)}>{submitting ? "Please wait..." : step === "email" ? "Continue" : "Verify and continue"}<Icon name="chevron" /></button>
          </form>
          {step === "code" ? <div className="auth-code-actions"><button type="button" onClick={changeEmail}>Use another email</button><button type="button" onClick={resendCode} disabled={submitting}>Send a new code</button></div> : null}
          <div className="auth-security"><Icon name="shield" /><span>No password to remember. Your session is protected with a secure HttpOnly cookie.</span></div>
        </div>
      </section>
    </main>
  );
}
