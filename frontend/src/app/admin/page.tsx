"use client";

import { FormEvent, useEffect, useState } from "react";

import { ApiError, api } from "@/lib/api";
import { clearSession, getSession, Session, setSession } from "@/lib/auth";

type SyncStatus = {
  status: "IDLE" | "RUNNING" | "SUCCEEDED" | "FAILED";
  started_at: string | null;
  finished_at: string | null;
  counts: Record<string, number> | null;
  errors: { file: string | null; record: string | null; detail: string }[] | null;
};

const COUNT_LABELS: Record<string, string> = {
  researchers: "Professors",
  articles: "Articles",
  initiatives: "Initiatives",
  research_groups: "Research groups",
  campuses: "Campuses",
  organizations: "Organizations",
  knowledge_areas: "Knowledge areas",
  research_productions: "Research productions",
  advisorships: "Advisorships",
  fellowships: "Fellowships",
};

function formatTimestamp(value: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

type RegisteredProfessor = {
  id: number;
  username: string;
  role: "PROFESSOR";
  researcher_id: number;
};

function RegistrationForm() {
  const [name, setName] = useState("");
  const [emails, setEmails] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setMessage(null);
    setBusy(true);
    try {
      const created = await api.post<RegisteredProfessor>("/api/admin/professors", {
        name,
        emails: emails
          .split(",")
          .map((email) => email.trim())
          .filter(Boolean),
        username,
        password,
      });
      setMessage(
        `Professor registered: ${created.username} (researcher id ${created.researcher_id}).`,
      );
      setName("");
      setEmails("");
      setUsername("");
      setPassword("");
    } catch (err) {
      if (err instanceof ApiError) {
        const detail = typeof err.detail === "string" ? err.detail : err.message;
        setError(`${err.status}: ${detail}`);
      } else {
        setError("Could not reach the server. Please try again.");
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="mt-3 max-w-md space-y-3">
      <div>
        <label htmlFor="reg-name" className="block text-sm font-medium">
          Full name
        </label>
        <input
          id="reg-name"
          value={name}
          onChange={(event) => setName(event.target.value)}
          required
          className="mt-1 w-full rounded border border-gray-300 px-3 py-2"
        />
      </div>
      <div>
        <label htmlFor="reg-emails" className="block text-sm font-medium">
          Emails (comma-separated)
        </label>
        <input
          id="reg-emails"
          value={emails}
          onChange={(event) => setEmails(event.target.value)}
          placeholder="joao@ifes.edu.br, joao@example.com"
          className="mt-1 w-full rounded border border-gray-300 px-3 py-2"
        />
      </div>
      <div>
        <label htmlFor="reg-username" className="block text-sm font-medium">
          Username
        </label>
        <input
          id="reg-username"
          value={username}
          onChange={(event) => setUsername(event.target.value)}
          required
          autoComplete="off"
          className="mt-1 w-full rounded border border-gray-300 px-3 py-2"
        />
      </div>
      <div>
        <label htmlFor="reg-password" className="block text-sm font-medium">
          Password (min 8 characters)
        </label>
        <input
          id="reg-password"
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          required
          minLength={8}
          autoComplete="new-password"
          className="mt-1 w-full rounded border border-gray-300 px-3 py-2"
        />
      </div>
      {error && (
        <p role="alert" className="text-sm text-red-700">
          {error}
        </p>
      )}
      {message && (
        <p role="status" className="text-sm text-green-700">
          {message}
        </p>
      )}
      <button
        type="submit"
        disabled={busy}
        className="rounded bg-gray-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
      >
        {busy ? "Registering…" : "Register professor"}
      </button>
    </form>
  );
}

export default function AdminPage() {
  const [session, setSessionState] = useState<Session | null>(null);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loginError, setLoginError] = useState<string | null>(null);
  const [status, setStatus] = useState<SyncStatus | null>(null);
  const [seedError, setSeedError] = useState<string | null>(null);
  const [seedRequested, setSeedRequested] = useState(false);

  useEffect(() => {
    setSessionState(getSession());
  }, []);

  useEffect(() => {
    if (!session || session.role !== "ADMIN") return;
    let cancelled = false;
    const poll = async () => {
      try {
        const current = await api.get<SyncStatus>("/api/admin/sync-status");
        if (!cancelled) setStatus(current);
      } catch (err) {
        if (!cancelled && err instanceof ApiError && err.status === 401) {
          clearSession();
          setSessionState(null);
        }
      }
    };
    poll();
    const timer = setInterval(poll, 2000);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [session, seedRequested]);

  async function handleLogin(event: FormEvent) {
    event.preventDefault();
    setLoginError(null);
    try {
      const body = new URLSearchParams({ username, password });
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body,
      });
      if (!response.ok) {
        throw new ApiError(response.status, "Invalid username or password");
      }
      const payload = await response.json();
      const nextSession: Session = {
        token: payload.access_token,
        role: payload.role,
        researcher_id: payload.researcher_id,
        username: payload.username ?? username,
      };
      setSession(nextSession);
      setSessionState(nextSession);
      setPassword("");
    } catch (err) {
      setLoginError(err instanceof ApiError ? err.message : "Login failed. Please try again.");
    }
  }

  function handleLogout() {
    clearSession();
    setSessionState(null);
    setStatus(null);
    setSeedError(null);
  }

  async function handleSeed() {
    setSeedError(null);
    setSeedRequested(false);
    try {
      await api.post("/api/admin/seed");
      setSeedRequested(true);
    } catch (err) {
      if (err instanceof ApiError) {
        const detail = typeof err.detail === "string" ? err.detail : err.message;
        setSeedError(`${err.status}: ${detail}`);
      } else {
        setSeedError("Could not reach the server. Please try again.");
      }
    }
  }

  if (!session) {
    return (
      <section aria-labelledby="admin-login-title">
        <h1 id="admin-login-title" className="text-2xl font-semibold">
          Admin sign in
        </h1>
        <form onSubmit={handleLogin} className="mt-4 max-w-sm space-y-3">
          <div>
            <label htmlFor="admin-username" className="block text-sm font-medium">
              Username
            </label>
            <input
              id="admin-username"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              autoComplete="username"
              className="mt-1 w-full rounded border border-gray-300 px-3 py-2"
            />
          </div>
          <div>
            <label htmlFor="admin-password" className="block text-sm font-medium">
              Password
            </label>
            <input
              id="admin-password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
              className="mt-1 w-full rounded border border-gray-300 px-3 py-2"
            />
          </div>
          {loginError && (
            <p role="alert" className="text-sm text-red-700">
              {loginError}
            </p>
          )}
          <button
            type="submit"
            className="rounded bg-gray-900 px-4 py-2 text-sm font-medium text-white"
          >
            Sign in
          </button>
        </form>
      </section>
    );
  }

  if (session.role !== "ADMIN") {
    return (
      <section aria-labelledby="admin-denied-title">
        <h1 id="admin-denied-title" className="text-2xl font-semibold">
          Admin only
        </h1>
        <p className="mt-2 text-gray-600">
          Your account does not have administrator privileges.
        </p>
        <button onClick={handleLogout} className="mt-4 text-sm underline">
          Sign out
        </button>
      </section>
    );
  }

  const running = status?.status === "RUNNING";
  const counts = status?.counts ?? {};
  const errors = status?.errors ?? [];
  const totalRecords = Object.values(counts).reduce((sum, value) => sum + value, 0);
  const lastSync = status?.finished_at ?? null;

  return (
    <section aria-labelledby="admin-title">
      <div className="flex items-center justify-between">
        <h1 id="admin-title" className="text-2xl font-semibold">
          Admin
        </h1>
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-600">{session.username}</span>
          <button onClick={handleLogout} className="text-sm underline">
            Sign out
          </button>
        </div>
      </div>

      {status?.status === "SUCCEEDED" && lastSync && (
        <p
          role="status"
          aria-live="polite"
          className="mt-4 rounded border border-green-300 bg-green-50 px-4 py-3 text-sm text-green-900"
        >
          Data synced on {formatTimestamp(lastSync)} — {totalRecords.toLocaleString()} records.
        </p>
      )}
      {status?.status === "FAILED" && (
        <p
          role="alert"
          className="mt-4 rounded border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-900"
        >
          Last synchronization failed. Check the sync status below.
        </p>
      )}

      <h2 className="mt-6 text-lg font-medium">Register professor</h2>
      <RegistrationForm />

      <h2 className="mt-8 text-lg font-medium">Data synchronization</h2>
      <dl className="mt-2 grid max-w-md grid-cols-2 gap-x-6 gap-y-1 text-sm">
        <dt className="text-gray-600">Status</dt>
        <dd role="status">
          {status ? status.status : "…"}
          {running && " — updating"}
        </dd>
        <dt className="text-gray-600">Started</dt>
        <dd>{formatTimestamp(status?.started_at ?? null)}</dd>
        <dt className="text-gray-600">Finished</dt>
        <dd>{formatTimestamp(status?.finished_at ?? null)}</dd>
      </dl>

      <button
        onClick={handleSeed}
        disabled={running}
        className="mt-4 rounded bg-gray-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
      >
        {running ? "Seed in progress…" : "Seed from source data"}
      </button>
      {running && (
        <p role="status" className="mt-2 text-sm text-gray-600">
          The seed runs in the background. This page refreshes automatically.
        </p>
      )}
      {seedError && (
        <p role="alert" className="mt-2 text-sm text-red-700">
          {seedError}
        </p>
      )}

      {status && (status.status === "SUCCEEDED" || status.status === "FAILED") && (
        <>
          <h3 className="mt-6 text-base font-medium">
            Record counts{status.status === "FAILED" ? " (partial — seed failed)" : ""}
          </h3>
          {counts && Object.keys(counts).length > 0 ? (
            <ul className="mt-2 max-w-md divide-y divide-gray-200 text-sm">
              {Object.entries(counts).map(([key, value]) => (
                <li key={key} className="flex justify-between py-1.5">
                  <span>{COUNT_LABELS[key] ?? key}</span>
                  <span>{value}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-2 text-sm text-gray-600">No counts recorded.</p>
          )}
          {status.status === "FAILED" && errors.length > 0 && (
            <>
              <h3 className="mt-4 text-base font-medium">Errors</h3>
              <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-red-800">
                {errors.map((error, index) => (
                  <li key={index}>
                    {error.file}
                    {error.record ? ` (record ${error.record})` : ""}: {error.detail}
                  </li>
                ))}
              </ul>
            </>
          )}
        </>
      )}
    </section>
  );
}