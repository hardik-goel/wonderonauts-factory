/**
 * List — and optionally delete — the sandbox snapshots this project has piled up.
 *
 * The same logic runs unattended every day at app/api/cron/prune-snapshots;
 * this is the manual door into it, for when you want to see the inventory or
 * sweep with a different age cutoff. Both share lib/snapshots.ts, which is
 * where the rules about what is safe to delete actually live.
 *
 *   cd web
 *   vercel env pull                                  # gets VERCEL_OIDC_TOKEN
 *   pnpm dlx tsx scripts/prune-snapshots.ts          # dry run: just lists
 *   pnpm dlx tsx scripts/prune-snapshots.ts --delete # actually prunes
 *
 * By default a snapshot has to be older than 24h to be a candidate, so a render
 * that is still running is not pruned out from under itself. Override with
 * --older-than=<hours>, or pass --older-than=0 to sweep everything.
 */
import { prune, gb, DEFAULT_MIN_AGE_MS } from "../lib/snapshots";

const args = process.argv.slice(2);
const apply = args.includes("--delete");
const olderThanArg = args.find((a) => a.startsWith("--older-than="));
const hours = olderThanArg ? Number(olderThanArg.split("=")[1]) : DEFAULT_MIN_AGE_MS / 3600_000;

if (!Number.isFinite(hours) || hours < 0) {
  console.error("--older-than expects a number of hours, e.g. --older-than=6");
  process.exit(1);
}

const age = (ms: number, now: number) => {
  const h = (now - ms) / 3600_000;
  return h < 48 ? `${h.toFixed(1)}h` : `${(h / 24).toFixed(1)}d`;
};

async function main() {
  const now = Date.now();
  const report = await prune({ now, minAgeMs: hours * 3600_000, apply });

  if (report.verdicts.length === 0) {
    console.log("no snapshots found for this project.");
    return;
  }

  for (const v of report.verdicts) {
    const why = v.base
      ? "KEEP (base)"
      : v.gone
        ? "already deleted"
        : !v.stale
          ? "KEEP (too new)"
          : "prune";
    console.log(
      `${v.id}  ${gb(v.sizeBytes ?? 0).padStart(9)}  ${age(v.createdAt, now).padStart(6)} old  ` +
        `${(v.creationMethod ?? "-").padEnd(9)}  parent=${(v.parentId ?? "-").padEnd(30)}  ` +
        `${v.status.padEnd(8)}  ${why}`,
    );
  }

  console.log(`\n${report.live} live snapshots, ${gb(report.liveBytes)} total.`);
  console.log(`${report.doomed.length} prunable, ${gb(report.reclaimableBytes)} reclaimable.`);

  if (!process.env.FACTORY_SNAPSHOT_ID) {
    console.warn(
      "\nnote: FACTORY_SNAPSHOT_ID is not set here (it is a Sensitive env var and\n" +
        "cannot be pulled), so the base is being identified by creationMethod and\n" +
        "parentage instead. Check the KEEP (base) rows above before deleting.",
    );
  }

  if (!apply) {
    console.log("\ndry run — nothing deleted. Re-run with --delete to prune.");
    return;
  }

  for (const id of report.deleted ?? []) console.log(`deleted ${id}`);
  for (const e of report.errors ?? []) console.error(`FAILED ${e.id}: ${e.message}`);
  console.log(`\nreclaimed ${gb(report.deletedBytes ?? 0)}.`);
  if (report.errors?.length) process.exit(1);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
