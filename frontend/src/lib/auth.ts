export type Session = {
  token: string;
  role: "ADMIN" | "PROFESSOR";
  researcher_id: number | null;
  username: string;
};

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem("portal_token");
}

export function getSession(): Session | null {
  if (typeof window === "undefined") return null;
  const token = window.localStorage.getItem("portal_token");
  const role = window.localStorage.getItem("portal_role");
  const researcherId = window.localStorage.getItem("portal_researcher_id");
  const username = window.localStorage.getItem("portal_username");
  if (!token || !role) return null;
  return {
    token,
    role: role as Session["role"],
    researcher_id: researcherId ? Number(researcherId) : null,
    username: username ?? "",
  };
}

export function setSession(session: Session): void {
  window.localStorage.setItem("portal_token", session.token);
  window.localStorage.setItem("portal_role", session.role);
  window.localStorage.setItem(
    "portal_researcher_id",
    session.researcher_id === null ? "" : String(session.researcher_id),
  );
  window.localStorage.setItem("portal_username", session.username);
}

export function clearSession(): void {
  ["portal_token", "portal_role", "portal_researcher_id", "portal_username"].forEach(
    (key) => window.localStorage.removeItem(key),
  );
}

export function isLoggedIn(): boolean {
  return getSession() !== null;
}