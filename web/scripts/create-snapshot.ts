/**
 * One-time bootstrap: bake ffmpeg + the Python dependencies into a sandbox
 * snapshot so every render starts warm.
 *
 * Without this, each build spends 60-120s on `apt-get install ffmpeg` and pip
 * before it draws a single frame. With it, the sandbox boots with everything
 * already present.
 *
 *   cd web
 *   vercel link && vercel env pull      # gets VERCEL_OIDC_TOKEN
 *   pnpm dlx tsx scripts/create-snapshot.ts
 *
 * Then set the printed id as FACTORY_SNAPSHOT_ID in the Vercel project.
 * Re-run it whenever requirements.txt changes.
 */
import { Sandbox } from "@vercel/sandbox";
import { BOOTSTRAP } from "../lib/sandbox";

const REPO =
  process.env.FACTORY_REPO_URL ?? "https://github.com/hardik-goel/wonderonauts-factory";

async function main() {
  console.log(`cloning ${REPO} and installing dependencies…`);

  const sandbox = await Sandbox.create({
    source: { type: "git", url: REPO, depth: 1 },
    resources: { vcpus: 4 },
    timeout: 15 * 60 * 1000,
  });

  const res = await sandbox.runCommand({
    cmd: "bash",
    args: ["-lc", BOOTSTRAP],
    stdout: process.stdout,
    stderr: process.stderr,
  });
  if (res.exitCode !== 0) throw new Error(`bootstrap failed (exit ${res.exitCode})`);

  // Prove the toolchain works before freezing it — a snapshot that is missing
  // an encoder is worse than no snapshot, because every later build inherits it.
  const check = await sandbox.runCommand({
    cmd: "bash",
    args: ["-lc", "python3 factory.py --check"],
    stdout: process.stdout,
    stderr: process.stderr,
  });
  if (check.exitCode !== 0) throw new Error("preflight failed inside the sandbox");

  const snapshot = await sandbox.snapshot();
  await sandbox.stop();

  console.log(`\nFACTORY_SNAPSHOT_ID=${snapshot.snapshotId}\n`);
  console.log("Set that in the Vercel project's environment variables.");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
