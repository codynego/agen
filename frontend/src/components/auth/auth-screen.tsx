"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { Icon } from "@/components/workspace/icons";
import { ApiError, loginAccount, registerAccount } from "@/lib/client-api";

type AuthMode = "register" | "login";

export function AuthScreen() {
  const router = useRouter();
  const [mode, setMode] = useState<AuthMode>("register");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    const form = new FormData(event.currentTarget);
    try {
      if (mode === "register") {
        await registerAccount({
          name: String(form.get("name") || ""),
          email: String(form.get("email") || ""),
          password: String(form.get("password") || ""),
        });
      } else {
        await loginAccount({
          email: String(form.get("email") || ""),
          password: String(form.get("password") || ""),
        });
      }
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

  function changeMode(nextMode: AuthMode) {
    setMode(nextMode);
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
          <span className="view-kicker">{mode === "register" ? "Create your account" : "Welcome back"}</span>
          <h2>{mode === "register" ? "Meet your Agen." : "Continue with Agen."}</h2>
          <p>{mode === "register" ? "Your private personal agent is created automatically." : "Sign in to your personal agent and active tasks."}</p>
          <div className="auth-switch" role="tablist" aria-label="Authentication method"><button type="button" role="tab" aria-selected={mode === "register"} className={mode === "register" ? "is-active" : ""} onClick={() => changeMode("register")}>Create account</button><button type="button" role="tab" aria-selected={mode === "login"} className={mode === "login" ? "is-active" : ""} onClick={() => changeMode("login")}>Sign in</button></div>
          <form className="auth-form" onSubmit={submit}>
            {mode === "register" ? <label><span>Full name</span><input name="name" autoComplete="name" required placeholder="Your name" /></label> : null}
            <label><span>Email address</span><input name="email" type="email" autoComplete="email" required placeholder="you@company.com" /></label>
            <label><span>Password</span><input name="password" type="password" autoComplete={mode === "register" ? "new-password" : "current-password"} minLength={8} required placeholder="At least 8 characters" /></label>
            {error ? <div className="auth-error" role="alert">{error}</div> : null}
            <button type="submit" disabled={submitting}>{submitting ? "Please wait..." : mode === "register" ? "Create my personal agent" : "Sign in"}<Icon name="chevron" /></button>
          </form>
          <div className="auth-security"><Icon name="shield" /><span>Your session is protected with secure cookies. We never store your password in the browser.</span></div>
        </div>
      </section>
    </main>
  );
}
