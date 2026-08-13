import { NextResponse } from "next/server";
import { prune, gb, DEFAULT_MIN_AGE_MS } from "@/lib/snapshots";

/**
 * Daily snapshot sweep. Scheduled by the `crons` entry in vercel.json.
 *
 * Every render leaves a ~1 GB filesystem snapshot behind (the sandbox is the
 * job store, so it has to be persistent). New ones expire on their own now,
 * but this keeps the quota honest anyway — expiries can be missing on anything
 * created before that change, and running out of snapshot storage breaks every
 * render at once with a 402.
 *
 * To run it by hand against production:
 *
 *   curl -H "Authorization: Bearer $CRON_SECRET" \
 *     https://wonderonauts-studio.vercel.app/api/cron/prune-snapshots
 *
 * A 404 there means the current production deployment predates this route —
 * the project is not connected to git, so pushing does not deploy it. Ship it
 * with `cd web && vercel --prod`.
 */

// Deletes are individual API calls; a backlog of them should not be cut off
// mid-sweep. Hobby caps this at 60s, which is the effective ceiling here.
export const maxDuration = 60;
// Nothing here is cacheable — it must actually run each time it fires.
export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  // Vercel Cron sends `Authorization: Bearer $CRON_SECRET` when that variable
  // is set. Without the check the route is a public endpoint that deletes
  // things, so refuse to run at all rather than run unauthenticated.
  const secret = process.env.CRON_SECRET;
  if (!secret) {
    return NextResponse.json(
      { error: "CRON_SECRET is not set; refusing to run an unauthenticated prune." },
      { status: 500 },
    );
  }
  if (req.headers.get("authorization") !== `Bearer ${secret}`) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  try {
    const report = await prune({ now: Date.now(), apply: true });

    const summary = {
      live: report.live,
      liveSize: gb(report.liveBytes),
      deleted: report.deleted?.length ?? 0,
      reclaimed: gb(report.deletedBytes ?? 0),
      minAgeHours: DEFAULT_MIN_AGE_MS / 3600_000,
      errors: report.errors?.length ? report.errors : undefined,
    };

    // Cron output is only ever read in the function log, so print it there too.
    console.log("[prune-snapshots]", JSON.stringify(summary));

    return NextResponse.json(summary);
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    console.error("[prune-snapshots] failed:", message);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
