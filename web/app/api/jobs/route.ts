import { NextResponse } from "next/server";
import { listJobs, historyEnabled } from "@/lib/db";

/**
 * Render history, newest first.
 *
 * Before this existed a job lived only in React state, so reloading the tab
 * lost it. The rows here are permanent; their artifacts are not — check
 * `downloadable` before offering links, because the sandbox holding the video
 * is pruned after a day.
 */
export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  if (!historyEnabled()) {
    // Not an error: the app is fully usable without Supabase configured, it
    // just cannot remember anything.
    return NextResponse.json({ jobs: [], history: false });
  }

  const limit = Number(new URL(req.url).searchParams.get("limit") ?? 50);
  const jobs = await listJobs(Number.isFinite(limit) ? Math.min(limit, 200) : 50);
  return NextResponse.json({ jobs, history: true });
}
