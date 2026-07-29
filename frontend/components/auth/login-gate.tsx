"use client";

import { FormEvent, useEffect, useState } from "react";
import { ChatWorkspace } from "@/components/chat/workspace";

const AUTHORIZED_EMAIL = "eya.mkaouar@ept.ucar.tn";
const AUTHORIZED_PASSWORD = "vistasy2026";
const SESSION_KEY = "RICHOUT-authenticated";
const DEFAULT_USER_ID = process.env.NEXT_PUBLIC_DEMO_USER_ID ?? "988367fd-3496-401a-8c7c-3336a3523079";

export function LoginGate() {
  const [checkingSession, setCheckingSession] = useState(true);
  const [authenticated, setAuthenticated] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setAuthenticated(window.localStorage.getItem(SESSION_KEY) === "true");
      setCheckingSession(false);
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);

  const signIn = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (email.trim().toLowerCase() !== AUTHORIZED_EMAIL || password !== AUTHORIZED_PASSWORD) {
      setError("The email or password is incorrect.");
      return;
    }
    window.localStorage.setItem(SESSION_KEY, "true");
    setError("");
    setAuthenticated(true);
  };

  if (checkingSession) return <main className="auth-loading"><span className="auth-loading__mark" /></main>;
  const handleLogout = () => {
    window.localStorage.removeItem(SESSION_KEY);
    setAuthenticated(false);
  };

  if (authenticated) return <ChatWorkspace userId={DEFAULT_USER_ID} username="eya.mkaouar" onLogout={handleLogout} />;

  return <main className="auth-page">
    <section className="auth-intro">
      <div className="auth-brand"><span className="brand__mark"><i /><i /><i /></span><strong>RICHOUT</strong></div>
      <div className="auth-intro__content">
        <p className="eyebrow">Private workspace</p>
        <h1>A calmer place to think clearly.</h1>
        <p>One focused workspace for your conversations, ideas, and momentum.</p>
      </div>
      <div className="auth-orbit auth-orbit--one" /><div className="auth-orbit auth-orbit--two" />
      <p className="auth-intro__footer">RICHOUT intelligence workspace <span /> Private access</p>
    </section>
    <section className="auth-panel">
      <form className="login-card" onSubmit={signIn}>
        <div className="login-card__heading"><p className="eyebrow">Welcome back</p><h2>Sign in to your workspace</h2><span>Use your authorized account to continue.</span></div>
        <label>Email address<input autoComplete="email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@example.com" required /></label>
        <label>Password<input autoComplete="current-password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Enter your password" required /></label>
        {error && <p className="login-error" role="alert"><span>!</span>{error}</p>}
        <button className="login-button" type="submit">Enter Nexus <span>&rarr;</span></button>
        <p className="login-card__help">This workspace is restricted to authorized access.</p>
      </form>
    </section>
  </main>;
}
