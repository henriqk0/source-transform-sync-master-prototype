"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { api, ApiError, ProfessorList, ProfessorListItem } from "@/lib/api";

export default function DirectoryPage() {
  const [query, setQuery] = useState("");
  const [debounced, setDebounced] = useState("");
  const [data, setData] = useState<ProfessorList | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const resultsRef = useRef<HTMLUListElement>(null);

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(query), 300);
    return () => clearTimeout(timer);
  }, [query]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    api
      .get<ProfessorList>(`/api/professors?q=${encodeURIComponent(debounced)}&page=1&page_size=50`)
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((err: ApiError) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [debounced]);

  function handleKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    const links = resultsRef.current
      ? Array.from(resultsRef.current.querySelectorAll<HTMLAnchorElement>("a"))
      : [];
    if (links.length === 0) return;
    const currentIndex = links.indexOf(document.activeElement as HTMLAnchorElement);
    if (event.key === "ArrowDown") {
      event.preventDefault();
      links[(currentIndex + 1) % links.length].focus();
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      links[(currentIndex - 1 + links.length) % links.length].focus();
    } else if (event.key === "Escape") {
      setQuery("");
    }
  }

  return (
    <section aria-labelledby="directory-title">
      <h1 id="directory-title" className="text-2xl font-semibold">
        Professor directory
      </h1>
      <label htmlFor="professor-search" className="mt-4 block text-sm font-medium">
        Search professors by name
      </label>
      <input
        id="professor-search"
        type="search"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="e.g. Maria"
        className="mt-1 w-full max-w-md rounded border border-gray-300 px-3 py-2"
        aria-describedby="search-hint"
      />
      <p id="search-hint" className="mt-1 text-sm text-gray-600">
        Type at least one letter to filter results. Use the arrow keys to move
        through results and Enter to open a profile.
      </p>

      {loading && (
        <p role="status" className="mt-4">
          Loading professors…
        </p>
      )}
      {!loading && error && (
        <p role="alert" className="mt-4 text-red-700">
          {error}
        </p>
      )}
      {!loading && !error && data && (
        <>
          {data.items.length === 0 ? (
            <p className="mt-4 text-gray-600">No professors found.</p>
          ) : (
            <>
              <p className="mt-4 text-sm text-gray-600" aria-live="polite">
                {data.total} professor{data.total === 1 ? "" : "s"} found
              </p>
              <ul
                ref={resultsRef}
                className="mt-2 divide-y divide-gray-200"
                aria-label="Professor results"
              >
                {data.items.map((professor: ProfessorListItem) => (
                  <li key={professor.id} className="py-3">
                    <Link
                      href={`/professors/${professor.id}`}
                      className="font-medium no-underline hover:underline"
                    >
                      {professor.name}
                    </Link>
                    {professor.affiliation && (
                      <span className="ml-2 text-sm text-gray-600">
                        {professor.affiliation}
                      </span>
                    )}
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