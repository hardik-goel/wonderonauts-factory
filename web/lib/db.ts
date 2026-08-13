import { createClient, type SupabaseClient } from "@supabase/supabase-js";
import type { Draft, Job, JobStatus, VideoConfig } from "./types";

/**
 * Job history.
 *
 * The sandbox used to be the only record of a render, which made every job as
 * ephemeral as the microVM that produced it — reload the page and it was
 * unreachable, and once the snapshot expired it was gone. This table is the
 * durable half: what was asked for, what the build printed, what it produced.
 *
 * The video is deliberately NOT here. Artifacts stream straight off the sandbox
 * and are downloaded as-is; nothing copies those bytes anywhere. So a row can
 * outlive its downloads, and `downloadable` records that.
 *
 * Every write is best-effort. History is a convenience, and a Supabase outage
 * (or a project that has not been provisioned yet) must not be able to fail a
 * render — so failures here are logged and swallowed, never thrown.
 */

const URL = process.env.SUPABASE_URL ?? process.env.NEXT_PUBLIC_SUPABASE_URL;
// Service role: this table has RLS on with no policies, so anon cannot see it.
// Server-only — it must never be exposed to the browser.
const KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;

let client: SupabaseClient | null = null;

/**
 * Null when Supabase is not configured. Callers treat that as "history is
 * switched off" and carry on, so the app still runs before the project exists.
 */
function db(): SupabaseClient | null {
  if (!URL || !KEY) return null;
  client ??= createClient(URL, KEY, { auth: { persistSession: false } });
  return client;
}

export function historyEnabled(): boolean {
  return Boolean(URL && KEY);
}

type Row = {
  id: string;
  slug: string;
  title: string;
  status: JobStatus;
  created_at: string;
  finished_at: string | null;
  exit_code: number | null;
  artifacts: string[] | null;
  log: string | null;
  qc: string | null;
  video_json: VideoConfig | null;
  render_scenes: string | null;
  source: Draft["source"] | null;
};

export type JobRecord = Job & { log: string; downloadable: boolean };

/**
 * Artifacts are readable for exactly as long as the sandbox snapshot holding
 * them survives, so `downloadable` is derived from the job's age rather than
 * stored. Nothing can keep a stored flag honest: a snapshot record carries a
 * session id, not the sandbox name a job is keyed by, so the prune has no way
 * to say which rows it just expired. Keep this in step with
 * JOB_SNAPSHOT_TTL_MS in sandbox.ts.
 */
const ARTIFACT_TTL_MS = 24 * 60 * 60 * 1000;

function toJob(r: Row): JobRecord {
  return {
    id: r.id,
    slug: r.slug,
    title: r.title,
    status: r.status,
    createdAt: r.created_at,
    finishedAt: r.finished_at ?? undefined,
    exitCode: r.exit_code ?? undefined,
    artifacts: r.artifacts ?? [],
    qc: r.qc ?? undefined,
    log: r.log ?? "",
    downloadable: Date.now() - new Date(r.created_at).getTime() < ARTIFACT_TTL_MS,
  };
}

function warn(what: string, err: unknown) {
  console.warn(`[db] ${what} failed:`, err instanceof Error ? err.message : err);
}

/** Called the moment a render starts, so a job exists in history even if it dies. */
export async function recordJobStart(job: Job, draft?: Draft): Promise<void> {
  const supabase = db();
  if (!supabase) return;
  try {
    const { error } = await supabase.from("jobs").upsert({
      id: job.id,
      slug: job.slug,
      title: job.title,
      status: job.status,
      created_at: job.createdAt,
      // Bundled episodes live in the repo, so there is nothing worth copying.
      video_json: draft?.videoJson ?? null,
      render_scenes: draft?.renderScenes ?? null,
      source: draft?.source ?? null,
    });
    if (error) throw error;
  } catch (err) {
    warn("recordJobStart", err);
  }
}

/**
 * Mirror the sandbox's view of a finished job into Postgres.
 *
 * The poller already reads the log and status out of the sandbox on every tick,
 * so this piggybacks on that rather than giving the sandbox its own database
 * credentials — a build script running generated Python has no business holding
 * a service key.
 *
 * Only terminal states are written. The UI polls every 4s for up to 25 minutes,
 * so mirroring every tick would mean ~375 updates per render, each rewriting a
 * log that only grows. Nothing needs those intermediate rows: while the sandbox
 * is alive it is the source of truth and the record is never read, and the
 * record is only consulted once the sandbox is gone — which implies the build
 * already ended.
 *
 * The cost of that choice: a render whose end is never observed (tab closed
 * before it finished, function timeout) leaves a row stuck at 'running'. It
 * means "the poller never saw this finish", not "still building".
 */
export async function mirrorJob(job: Job & { log: string }): Promise<void> {
  const supabase = db();
  if (!supabase) return;
  if (job.status !== "done" && job.status !== "failed") return;
  try {
    const { error } = await supabase
      .from("jobs")
      .update({
        status: job.status,
        exit_code: job.exitCode ?? null,
        artifacts: job.artifacts,
        log: job.log,
        qc: job.qc ?? null,
        finished_at: job.finishedAt ?? new Date().toISOString(),
      })
      .eq("id", job.id);
    if (error) throw error;
  } catch (err) {
    warn("mirrorJob", err);
  }
}

/** The stored record, for when the sandbox is gone. Null if history is off or unknown. */
export async function getJobRecord(id: string): Promise<JobRecord | null> {
  const supabase = db();
  if (!supabase) return null;
  try {
    const { data, error } = await supabase.from("jobs").select("*").eq("id", id).maybeSingle();
    if (error) throw error;
    return data ? toJob(data as Row) : null;
  } catch (err) {
    warn("getJobRecord", err);
    return null;
  }
}

/** Newest first. The history list the UI never had. */
export async function listJobs(limit = 50): Promise<JobRecord[]> {
  const supabase = db();
  if (!supabase) return [];
  try {
    const { data, error } = await supabase
      .from("jobs")
      .select("*")
      .order("created_at", { ascending: false })
      .limit(limit);
    if (error) throw error;
    return (data as Row[]).map(toJob);
  } catch (err) {
    warn("listJobs", err);
    return [];
  }
}

