import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex h-screen flex-col items-center justify-center gap-3 bg-background px-4 text-center">
      <p className="font-mono text-xs text-ink-subtle">404</p>
      <h1 className="text-lg font-semibold text-ink">Body system not found</h1>
      <p className="max-w-sm text-sm text-ink-muted">
        That anatomy topic doesn&apos;t exist yet. Try one of the systems in the sidebar instead.
      </p>
      <Link
        href="/"
        className="mt-2 rounded-control border border-line px-3 py-1.5 text-sm text-ink-muted transition-colors hover:border-line-strong hover:text-ink"
      >
        Back to Anatomy Explorer
      </Link>
    </div>
  );
}
