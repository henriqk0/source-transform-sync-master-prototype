"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { FormEvent, useCallback, useEffect, useState } from "react";

import { api, ApiError, Profile } from "@/lib/api";
import { getSession } from "@/lib/auth";

const PAGE_SIZE = 50;

export default function ProfessorProfilePage() {
  const { id } = useParams<{ id: string }>();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [articlePage, setArticlePage] = useState(1);

  const loadProfile = useCallback(
    (page: number) => {
      api
        .get<Profile>(
          `/api/professors/${id}?page=${page}&page_size=${PAGE_SIZE}`,
        )
        .then(setProfile)
        .catch((err: ApiError) => {
          setError(err.status === 404 ? "Professor not found." : err.message);
        })
        .finally(() => setLoading(false));
    },
    [id],
  );

  useEffect(() => {
    loadProfile(1);
  }, [loadProfile]);

  if (loading) {
    return <p role="status">Loading professor…</p>;
  }

  if (error || !profile) {
    return (
      <section aria-labelledby="profile-error">
        <h1 id="profile-error" className="text-xl font-semibold">
          {error ?? "Professor unavailable."}
        </h1>
        <Link href="/" className="mt-2 inline-block">
          Back to directory
        </Link>
      </section>
    );
  }

  const loadMoreArticles = () => {
    const next = articlePage + 1;
    setArticlePage(next);
    api
      .get<Profile>(`/api/professors/${id}?page=${next}&page_size=${PAGE_SIZE}`)
      .then((result) => setProfile(result))
      .catch((err: ApiError) => setError(err.message));
  };

  const session = getSession();
  const isOwner =
    session !== null && session.researcher_id === Number(id);

  return (
    <article aria-labelledby="profile-name">
      <Link href="/" className="text-sm">
        ← Back to directory
      </Link>

      <header className="mt-2">
        <h1 id="profile-name" className="text-3xl font-semibold">
          {profile.name}
        </h1>
        {profile.affiliation && (
          <p className="mt-1 text-gray-700">{profile.affiliation}</p>
        )}
        {profile.resume && <p className="mt-2 text-gray-700">{profile.resume}</p>}
      </header>

      {isOwner && <EditOwnData profile={profile} />}

      <section aria-labelledby="current-projects-title" className="mt-6">
        <h2 id="current-projects-title" className="text-xl font-semibold">
          Current projects
        </h2>
        {profile.current_projects.length === 0 ? (
          <p className="mt-1 text-gray-600">No current projects.</p>
        ) : (
          <ul className="mt-1 list-disc pl-6">
            {profile.current_projects.map((project) => (
              <li key={project.id}>
                {project.name}
                <span className="ml-2 text-sm text-gray-600">{project.status}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section aria-labelledby="article-counts-title" className="mt-6">
        <h2 id="article-counts-title" className="text-xl font-semibold">
          Article counts by year
        </h2>
        {profile.article_counts_by_year.length === 0 ? (
          <p className="mt-1 text-gray-600">No articles recorded.</p>
        ) : (
          <table className="mt-1">
            <thead>
              <tr>
                <th scope="col" className="pr-6 text-left">Year</th>
                <th scope="col" className="text-left">Articles</th>
              </tr>
            </thead>
            <tbody>
              {profile.article_counts_by_year.map((row) => (
                <tr key={row.year}>
                  <td className="py-1 pr-6">{row.year}</td>
                  <td className="py-1">{row.count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section aria-labelledby="locations-title" className="mt-6">
        <h2 id="locations-title" className="text-xl font-semibold">
          Research locations
        </h2>
        {profile.locations.length === 0 ? (
          <p className="mt-1 text-gray-600">No locations recorded.</p>
        ) : (
          <ul className="mt-1 list-disc pl-6">
            {profile.locations.map((location) => (
              <li key={`${location.type}-${location.id}`}>{location.name}</li>
            ))}
          </ul>
        )}
      </section>

      <section aria-labelledby="articles-title" className="mt-6">
        <h2 id="articles-title" className="text-xl font-semibold">
          Articles
        </h2>
        {profile.articles.length === 0 ? (
          <p className="mt-1 text-gray-600">No articles recorded.</p>
        ) : (
          <>
            <ul className="mt-1 list-disc pl-6">
              {profile.articles.map((article) => (
                <li key={article.id} className="py-1">
                  {article.title}
                  <span className="ml-2 text-sm text-gray-600">
                    {article.year}
                    {article.type ? ` · ${article.type}` : ""}
                  </span>
                </li>
              ))}
            </ul>
            {profile.article_page * PAGE_SIZE < profile.articles_total && (
              <button
                type="button"
                onClick={loadMoreArticles}
                className="mt-3 rounded border border-brand px-4 py-2 font-medium"
              >
                Load more articles
              </button>
            )}
          </>
        )}
      </section>
    </article>
  );
}

type EditResponse = {
  id: number;
  name: string;
  emails: string[];
  resume: string | null;
};

function EditOwnData({ profile }: { profile: Profile }) {
  const [name, setName] = useState(profile.name);
  const [emails, setEmails] = useState("");
  const [resume, setResume] = useState(profile.resume ?? "");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setMessage(null);
    setError(null);
    setBusy(true);
    try {
      const updated = await api.patch<EditResponse>(`/api/professors/${profile.id}`, {
        name,
        emails: emails
          .split(",")
          .map((email) => email.trim())
          .filter(Boolean),
        resume: resume || null,
      });
      setMessage("Your data was updated.");
      setName(updated.name);
      setEmails(updated.emails.join(", "));
      setResume(updated.resume ?? "");
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
    <section aria-labelledby="edit-own-title" className="mt-6 max-w-md">
      <h2 id="edit-own-title" className="text-xl font-semibold">
        Edit your data
      </h2>
      <form onSubmit={handleSubmit} className="mt-2 space-y-3">
        <div>
          <label htmlFor="edit-name" className="block text-sm font-medium">
            Name
          </label>
          <input
            id="edit-name"
            value={name}
            onChange={(event) => setName(event.target.value)}
            required
            className="mt-1 w-full rounded border border-gray-300 px-3 py-2"
          />
        </div>
        <div>
          <label htmlFor="edit-emails" className="block text-sm font-medium">
            Emails (comma-separated)
          </label>
          <input
            id="edit-emails"
            value={emails}
            onChange={(event) => setEmails(event.target.value)}
            placeholder="me@ifes.edu.br"
            className="mt-1 w-full rounded border border-gray-300 px-3 py-2"
          />
        </div>
        <div>
          <label htmlFor="edit-resume" className="block text-sm font-medium">
            Resume
          </label>
          <textarea
            id="edit-resume"
            value={resume}
            onChange={(event) => setResume(event.target.value)}
            rows={3}
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
          {busy ? "Saving…" : "Save changes"}
        </button>
      </form>
    </section>
  );
}