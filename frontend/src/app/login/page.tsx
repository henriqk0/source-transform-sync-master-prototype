"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { setSession, Session } from "@/lib/auth";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const response = await fetch(`${API_BASE}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({ username, password }),
      });
      if (!response.ok) {
        setError("Invalid username or password");
        return;
      }
      const payload = await response.json();
      const session: Session = {
        token: payload.access_token,
        role: payload.role,
        researcher_id: payload.researcher_id,
        username: payload.username ?? username,
      };
      setSession(session);
      router.push(payload.role === "ADMIN" ? "/admin" : "/");
    } catch {
      setError("Could not reach the server. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-labelledby="login-title">
      <h1 id="login-title" className="text-2xl font-semibold">
        Sign in
      </h1>
      <form onSubmit={handleSubmit} className="mt-4 max-w-sm space-y-3">
        <div>
          <label htmlFor="login-username" className="block text-sm font-medium">
            Username
          </label>
          <input
            id="login-username"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            autoComplete="username"
            className="mt-1 w-full rounded border border-gray-300 px-3 py-2"
          />
        </div>
        <div>
          <label htmlFor="login-password" className="block text-sm font-medium">
            Password
          </label>
          <input
            id="login-password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="current-password"
            className="mt-1 w-full rounded border border-gray-300 px-3 py-2"
          />
        </div>
        {error && (
          <p role="alert" className="text-sm text-red-700">
            {error}
          </p>
        )}
        <button
          type="submit"
          disabled={busy}
          className="rounded bg-gray-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {busy ? "Signing in…" : "Sign in"}
        </button>
      </form>
      <p className="mt-4 text-sm text-gray-600">
        Browse the <Link href="/" className="underline">professor directory</Link> without an account.
      </p>
    </section>
  );
}