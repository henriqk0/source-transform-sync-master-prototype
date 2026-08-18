import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Professor Data Portal",
  description:
    "Research data portal: professor profiles, projects, articles, and research locations.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt-BR">
      <body>
        <header className="border-b border-gray-200">
          <nav className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3" aria-label="Main">
            <Link
              href="/"
              className="text-lg font-semibold no-underline hover:underline text-brand"
            >
              Professor Data Portal
            </Link>
            <div className="flex gap-4 text-sm">
              <Link href="/" className="no-underline hover:underline">
                Professors
              </Link>
              <Link href="/login" className="no-underline hover:underline">
                Sign in
              </Link>
            </div>
          </nav>
        </header>
        <main className="mx-auto max-w-5xl px-4 py-6">{children}</main>
      </body>
    </html>
  );
}