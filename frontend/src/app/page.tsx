/* FlatWatch - Society Cash Tracker */
/* DRAMS Design: "Less, but better" - Dieter Rams principles */

'use client';

import Link from 'next/link';

export default function Home() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-white font-sans">
      <main className="flex w-full max-w-2xl flex-col items-center gap-12 px-6 py-20 text-center">
        {/* Title */}
        <div className="flex flex-col items-center gap-4">
          <h1 className="text-4xl font-semibold tracking-tight text-[#333] sm:text-5xl">
            FlatWatch
          </h1>
          <p className="text-lg text-[#999]">
            Society Cash Tracker
          </p>
        </div>

        {/* DRAMS Card Component */}
        <div className="w-full max-w-md rounded-3xl bg-white p-8 shadow-[0_4px_16px_rgba(0,0,0,0.06)] transition-all hover:shadow-[0_8px_24px_rgba(0,0,0,0.1)] hover:-translate-y-1">
          <p className="mb-6 text-[#333]">
            Financial transparency for housing societies
          </p>

          {/* DRAMS Action Button */}
          <Link href="/dashboard">
            <button className="h-12 w-full rounded-full bg-[rgb(255,97,26)] px-6 text font-medium text-white shadow-[0_2px_8px_rgba(255,97,26,0.3)] transition-all hover:shadow-[0_4px_12px_rgba(255,97,26,0.4)] active:scale-95">
              Get Started
            </button>
          </Link>
        </div>

        {/* Status indicator */}
        <div className="flex items-center gap-2 rounded-full bg-[rgb(238,238,238)] px-4 py-2">
          <span className="h-2 w-2 rounded-full bg-[rgb(255,97,26)]" />
          <span className="text-sm text-[#999]">
            System initializing...
          </span>
        </div>
      </main>
    </div>
  );
}
