import { Readable } from "node:stream";
import { Sandbox } from "@vercel/sandbox";
import type { Draft, Job, JobStatus } from "./types";
import { ARTIFACTS } from "./types";

/**
 * Render orchestration.
 *
 * The sandbox IS the job store. A job id is a sandbox name, and everything a
 * poll needs — the log, the exit code, the metadata, the artifacts — lives in
 * that sandbox's filesystem. Sandboxes are persistent by default (auto-snapshot
 * on stop, restored on resume), so there is no database to provision and
 * nothing to keep in sync with the render.
 *
 * The build is started DETACHED: a render takes minutes and a serverless
 * function does not. The POST that starts it returns as soon as the process is
 * running; polling reads state back out of the sandbox afterwards.
 */

const REPO = process.env.FACTORY_REPO_URL ?? "https://github.com/hardik-goel/wonderonauts-factory";
const SNAPSHOT = process.env.FACTORY_SNAPSHOT_ID;
const ROOT = "/vercel/sandbox";
const BUILD_TIMEOUT_MS = 25 * 60 * 1000;

/** apt + pip bootstrap. Skipped entirely when a prepared snapshot is available. */
export const BOOTSTRAP = [
  "set -eux",
  "export DEBIAN_FRONTEND=noninteractive",
  "sudo apt-get update -qq",
  "sudo apt-get install -y -qq ffmpeg fonts-dejavu-core",
  "python3 -m pip install --quiet --break-system-packages -r requirements.txt",
].join("\n");

function credentials() {
  const { VERCEL_TOKEN, VERCEL_TEAM_ID, VERCEL_PROJECT_ID } = process.env;
  return VERCEL_TOKEN && VERCEL_TEAM_ID && VERCEL_PROJECT_ID
    ? { token: VERCEL_TOKEN, teamId: VERCEL_TEAM_ID, projectId: VERCEL_PROJECT_ID }
    : {};
}

function gitSource() {
  const token = process.env.FACTORY_REPO_TOKEN;
  return token
    ? { type: "git" as const, url: REPO, depth: 1, username: "x-access-token", password: token }
    : { type: "git" as const, url: REPO, depth: 1 };
}

export function newJobId(slug: string): string {
  const rand = Math.random().toString(36).slice(2, 8);
  // sandbox names are per-project unique; keep them short and readable
  return `ep-${slug}-${rand}`.slice(0, 60);
}

/**
 * Create a sandbox, install the draft, and kick off the build.
 * Returns as soon as the build process is running.
 *
 * A `draft` with no `videoJson` is a bundled episode: its script and scene art
 * are already committed in the repo the sandbox cloned, so nothing is written
 * and the factory just builds what is there.
 */
export async function startRender(draft: Draft | BundledEpisode): Promise<Job> {
  const id = newJobId(draft.slug);
  const projectDir = `projects/${draft.slug}`;
  const bundled = !("videoJson" in draft) || !draft.videoJson;

  // A prepared snapshot (ffmpeg + python deps already installed) and a cold
  // git clone are separate parameter shapes in the SDK, not one field.
  const common = {
    ...credentials(),
    name: id,
    resources: { vcpus: 4 },
    timeout: BUILD_TIMEOUT_MS,
    // the filesystem is the job record; it must survive the session
    persistent: true,
    tags: { app: "wonderonauts", slug: draft.slug.slice(0, 60) },
  };
  const sandbox = SNAPSHOT
    ? await Sandbox.create({ ...common, source: { type: "snapshot", snapshotId: SNAPSHOT } })
    : await Sandbox.create({ ...common, source: gitSource() });

  const job: Job = {
    id,
    slug: draft.slug,
    title: draft.title ?? ("videoJson" in draft ? draft.videoJson?.title : "") ?? draft.slug,
    status: "starting",
    createdAt: new Date().toISOString(),
    artifacts: [],
  };

  const files: { path: string; content: Buffer; mode?: number }[] = [
    { path: "job.json", content: Buffer.from(JSON.stringify(job, null, 2)) },
    { path: "build.sh", content: Buffer.from(buildScript(projectDir)), mode: 0o755 },
  ];

  if (!bundled) {
    const d = draft as Draft;
    await sandbox.mkDir(`${projectDir}/frames`);
    files.push(
      {
        path: `${projectDir}/video.json`,
        content: Buffer.from(JSON.stringify(d.videoJson, null, 2) + "\n"),
      },
      { path: `${projectDir}/render_scenes.py`, content: Buffer.from(d.renderScenes) },
    );
  }

  await sandbox.writeFiles(files);

  // Detached: the build outlives this request. Everything it prints lands in
  // job.log; job.exit appearing is the completion signal.
  await sandbox.runCommand({
    cmd: "bash",
    args: ["-lc", `cd ${ROOT} && nohup ./build.sh > /dev/null 2>&1 &`],
    detached: true,
  });

  return { ...job, status: "running" };
}

function buildScript(projectDir: string): string {
  return `#!/usr/bin/env bash
# Render one episode, then record the outcome for the poller.
cd "${ROOT}"
{
  echo "== preparing environment =="
  ${SNAPSHOT ? 'echo "using prepared snapshot"' : `(
${BOOTSTRAP
  .split("\n")
  .map((l) => "    " + l)
  .join("\n")}
  )`}

  echo "== validating video.json =="
  python3 factory.py "${projectDir}" --validate || echo "(lint reported issues; continuing)"

  echo "== building =="
  python3 factory.py "${projectDir}" --shorts
} > job.log 2>&1
echo $? > job.exit
`;
}

async function attach(id: string) {
  return Sandbox.get({ ...credentials(), name: id });
}

async function readText(
  sandbox: Awaited<ReturnType<typeof attach>>,
  path: string,
): Promise<string | null> {
  const buf = await sandbox.readFileToBuffer({ path, cwd: ROOT });
  return buf ? buf.toString("utf8") : null;
}

/** A bundled episode: everything it needs is already committed in the repo. */
export type BundledEpisode = { slug: string; title: string; videoJson?: undefined };

export type JobView = Job & { log: string };

export async function getJob(id: string): Promise<JobView> {
  const sandbox = await attach(id);

  const [metaRaw, logRaw, exitRaw] = await Promise.all([
    readText(sandbox, "job.json"),
    readText(sandbox, "job.log"),
    readText(sandbox, "job.exit"),
  ]);

  if (!metaRaw) throw new Error(`job ${id} not found`);
  const job = JSON.parse(metaRaw) as Job;
  const log = logRaw ?? "";

  let status: JobStatus = "running";
  let exitCode: number | undefined;
  let artifacts: string[] = [];
  let qc: string | undefined;

  if (exitRaw !== null) {
    exitCode = Number(exitRaw.trim());
    status = exitCode === 0 ? "done" : "failed";
    if (status === "done") {
      artifacts = await listArtifacts(sandbox, job.slug);
      qc = (await readText(sandbox, `projects/${job.slug}/output/qc_report.txt`)) ?? undefined;
    }
  }

  return { ...job, status, exitCode, artifacts, qc, log };
}

async function listArtifacts(
  sandbox: Awaited<ReturnType<typeof attach>>,
  slug: string,
): Promise<string[]> {
  const res = await sandbox.runCommand({
    cmd: "bash",
    args: ["-lc", `ls -1 ${ROOT}/projects/${slug}/output 2>/dev/null || true`],
  });
  const present = new Set((await res.stdout()).split("\n").map((s) => s.trim()));
  return ARTIFACTS.filter((a) => present.has(a));
}

const MIME: Record<string, string> = {
  ".mp4": "video/mp4",
  ".jpg": "image/jpeg",
  ".srt": "application/x-subrip",
  ".txt": "text/plain; charset=utf-8",
  ".json": "application/json",
};

export async function readArtifact(
  id: string,
  name: string,
): Promise<{ body: ReadableStream; contentType: string } | null> {
  if (!(ARTIFACTS as readonly string[]).includes(name)) return null;

  const sandbox = await attach(id);
  const meta = await readText(sandbox, "job.json");
  if (!meta) return null;
  const { slug } = JSON.parse(meta) as Job;

  const node = await sandbox.readFile({
    path: `projects/${slug}/output/${name}`,
    cwd: ROOT,
  });
  if (!node) return null;

  // The SDK hands back a Node stream; a Response body needs a web stream.
  const body = Readable.toWeb(
    node as unknown as Readable,
  ) as unknown as ReadableStream;

  const ext = name.slice(name.lastIndexOf("."));
  return { body, contentType: MIME[ext] ?? "application/octet-stream" };
}

/** Free the microVM once the user has what they need. */
export async function stopJob(id: string): Promise<void> {
  const sandbox = await attach(id);
  await sandbox.stop();
}
