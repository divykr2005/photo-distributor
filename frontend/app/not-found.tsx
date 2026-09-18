import Link from "next/link";

export default function NotFound() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-zinc-950 px-6 text-zinc-100">
      <div className="max-w-lg text-center">
        <p className="text-sm font-semibold uppercase tracking-[0.24em] text-indigo-400">404</p>
        <h1 className="mt-4 text-4xl font-bold tracking-tight">This page is out of frame</h1>
        <p className="mt-4 leading-relaxed text-zinc-400">
          The link may be old, incomplete, or no longer available.
        </p>
        <Link
          href="/"
          className="mt-8 inline-flex rounded-xl bg-indigo-500 px-5 py-3 font-semibold text-white transition-colors hover:bg-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-300 focus:ring-offset-2 focus:ring-offset-zinc-950"
        >
          Go to SnapTracer
        </Link>
      </div>
    </main>
  );
}
