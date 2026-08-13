import { Snapshot } from "@vercel/sandbox";
import { credentials } from "./sandbox";

/**
 * Sandbox snapshot housekeeping.
 *
 * Render sandboxes are `persistent: true` — the filesystem IS the job record —
 * so Vercel snapshots each one when its session stops. That is roughly a
 * gigabyte per render, and left alone they accumulate until the plan's storage
 * quota trips every subsequent render:
 *
 *   Status code 402 is not ok - Hobby plan usage limit exceeded for Snapshots
 *   Storage.
 *
 * New renders now set `snapshotExpiration` so the platform reclaims them on its
 * own (see startRender). This module is the belt to that pair of braces: it
 * sweeps anything already on disk without one, and catches whatever slips
 * through. Driven by scripts/prune-snapshots.ts by hand and by the daily cron
 * at app/api/cron/prune-snapshots.
 */

export type SnapshotRow = {
  id: string;
  status: "failed" | "created" | "deleted";
  sizeBytes: number;
  createdAt: number;
  parentId?: string;
  creationMethod?: string;
};

export type PruneVerdict = SnapshotRow & {
  /** Kept because it is the prepared base every render boots from. */
  base: boolean;
  /** Already gone; listed by the API but costing nothing. */
  gone: boolean;
  /** Old enough to be a candidate. */
  stale: boolean;
  prune: boolean;
};

export type PruneReport = {
  verdicts: PruneVerdict[];
  /** Snapshots that still occupy storage. */
  live: number;
  liveBytes: number;
  doomed: PruneVerdict[];
  reclaimableBytes: number;
  /** Set once deletions actually run. */
  deleted?: string[];
  deletedBytes?: number;
  errors?: { id: string; message: string }[];
};

/** A day. Long enough that a running render is never pruned out from under itself. */
export const DEFAULT_MIN_AGE_MS = 24 * 60 * 60 * 1000;

/**
 * Decide what is safe to delete.
 *
 * `now` is a parameter rather than a `Date.now()` call so the caller controls
 * the clock and every row in one report is judged against the same instant.
 */
export function planPrune(
  all: SnapshotRow[],
  { now, minAgeMs = DEFAULT_MIN_AGE_MS }: { now: number; minAgeMs?: number },
): PruneReport {
  // FACTORY_SNAPSHOT_ID is a Sensitive env var — readable by the deployed
  // function but never by `vercel env pull` — so the base has to be
  // identifiable without it or a local run would delete the one snapshot worth
  // keeping. Two signals give it away: scripts/create-snapshot.ts calls
  // sandbox.snapshot() by hand, which the API records as "manual" (every render
  // snapshot is "automatic"), and every render started from the base names it
  // as their parent.
  const keep = process.env.FACTORY_SNAPSHOT_ID;
  const parents = new Set(all.map((s) => s.parentId).filter(Boolean));

  const verdicts: PruneVerdict[] = all
    .slice()
    .sort((a, b) => b.createdAt - a.createdAt)
    .map((s) => {
      const base = s.id === keep || s.creationMethod === "manual" || parents.has(s.id);
      const gone = s.status === "deleted";
      const stale = now - s.createdAt >= minAgeMs;
      return { ...s, base, gone, stale, prune: !base && !gone && stale };
    });

  const liveRows = verdicts.filter((v) => !v.gone);
  const doomed = verdicts.filter((v) => v.prune);

  return {
    verdicts,
    live: liveRows.length,
    liveBytes: liveRows.reduce((n, v) => n + (v.sizeBytes ?? 0), 0),
    doomed,
    reclaimableBytes: doomed.reduce((n, v) => n + (v.sizeBytes ?? 0), 0),
  };
}

/** Fetch every snapshot the credentials can see, following pagination. */
export async function listSnapshots(): Promise<SnapshotRow[]> {
  const page = await Snapshot.list({ ...credentials() });
  return page.toArray();
}

/**
 * Plan a prune and, when `apply` is set, carry it out.
 *
 * One failed delete does not abort the sweep — a snapshot that is wedged or
 * concurrently removed should not strand the rest of the quota.
 */
export async function prune({
  now,
  minAgeMs = DEFAULT_MIN_AGE_MS,
  apply = false,
}: {
  now: number;
  minAgeMs?: number;
  apply?: boolean;
}): Promise<PruneReport> {
  const report = planPrune(await listSnapshots(), { now, minAgeMs });
  if (!apply) return report;

  const creds = credentials();
  const deleted: string[] = [];
  const errors: { id: string; message: string }[] = [];
  let deletedBytes = 0;

  for (const s of report.doomed) {
    try {
      const snap = await Snapshot.get({ ...creds, snapshotId: s.id });
      await snap.delete();
      deleted.push(s.id);
      deletedBytes += s.sizeBytes ?? 0;
    } catch (err) {
      errors.push({ id: s.id, message: err instanceof Error ? err.message : String(err) });
    }
  }

  // Nothing here marks job rows as expired: a snapshot record carries a
  // sourceSessionId, not the sandbox name a job is keyed by, so there is no
  // reliable mapping back. lib/db.ts derives `downloadable` from the job's age
  // against the same TTL instead.
  return { ...report, deleted, deletedBytes, errors };
}

export const gb = (bytes: number) => (bytes / 1024 ** 3).toFixed(2) + " GB";
