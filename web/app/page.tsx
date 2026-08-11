"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { Draft, Job } from "@/lib/types";

type JobView = Job & { log: string };
type Phase = "idle" | "writing" | "review" | "rendering" | "done" | "failed";

const EXAMPLES = [
  "Why do magnets stick together?",
  "Why do we need to sleep?",
  "What are clouds made of?",
  "Why does the Moon change shape?",
];

export default function Studio() {
  const [topic, setTopic] = useState("");
  const [phase, setPhase] = useState<Phase>("idle");
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [job, setJob] = useState<JobView | null>(null);

  const busy = phase === "writing" || phase === "rendering";

  async function writeScript() {
    setError(null);
    setDraft(null);
    setJob(null);
    setPhase("writing");
    try {
      const res = await fetch("/api/draft", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ topic }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error ?? "Script generation failed.");
      setDraft(data as Draft);
      setPhase("review");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setPhase("idle");
    }
  }

  async function render() {
    if (!draft) return;
    setError(null);
    setPhase("rendering");
    try {
      const res = await fetch("/api/render", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(draft),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error ?? "Could not start the render.");
      setJob({ ...(data as Job), log: "" });
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setPhase("review");
    }
  }

  // Poll while a render is in flight.
  const jobId = job?.id;
  useEffect(() => {
    if (phase !== "rendering" || !jobId) return;
    let alive = true;
    const tick = async () => {
      try {
        const res = await fetch(`/api/jobs/${jobId}`);
        if (!res.ok) return;
        const data = (await res.json()) as JobView;
        if (!alive) return;
        setJob(data);
        if (data.status === "done") setPhase("done");
        if (data.status === "failed") setPhase("failed");
      } catch {
        /* transient; the next tick retries */
      }
    };
    void tick();
    const t = setInterval(tick, 4000);
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, [phase, jobId]);

  function reset() {
    setPhase("idle");
    setDraft(null);
    setJob(null);
    setError(null);
  }

  return (
    <main className="mx-auto w-full max-w-5xl px-5 py-10 sm:py-14">
      <Header />

      <section className="mt-8 rounded-2xl border border-border bg-surface p-5 sm:p-6">
        <label htmlFor="topic" className="block text-sm font-medium text-muted">
          A question a child would ask — or a YouTube link to research
        </label>
        <div className="mt-3 flex flex-col gap-3 sm:flex-row">
          <input
            id="topic"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && topic.trim() && !busy) void writeScript();
            }}
            placeholder="Why is the sea salty?"
            disabled={busy}
            className="min-w-0 flex-1 rounded-xl border border-border bg-surface-2 px-4 py-3 text-base
                       outline-none placeholder:text-muted/60 focus:border-sky disabled:opacity-60"
          />
          <button
            onClick={() => void writeScript()}
            disabled={!topic.trim() || busy}
            className="rounded-xl bg-accent px-5 py-3 font-semibold text-accent-ink
                       transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {phase === "writing" ? "Writing…" : "Write the script"}
          </button>
        </div>

        {phase === "idle" && (
          <div className="mt-4 flex flex-wrap gap-2">
            {EXAMPLES.map((e) => (
              <button
                key={e}
                onClick={() => setTopic(e)}
                className="rounded-full border border-border px-3 py-1.5 text-xs text-muted
                           transition hover:border-sky hover:text-foreground"
              >
                {e}
              </button>
            ))}
          </div>
        )}

        {phase === "writing" && (
          <p className="mt-4 text-sm text-muted">
            Researching and writing ten scenes plus the scene art. This takes a
            minute or two.
          </p>
        )}
      </section>

      {error && (
        <p className="mt-5 rounded-xl border border-bad/40 bg-bad/10 px-4 py-3 text-sm text-bad">
          {error}
        </p>
      )}

      {draft && phase === "review" && (
        <DraftReview draft={draft} onChange={setDraft} onRender={() => void render()} />
      )}

      {job && phase !== "review" && phase !== "idle" && (
        <RenderPanel job={job} phase={phase} onReset={reset} />
      )}

      <Footer />
    </main>
  );
}

function Header() {
  return (
    <header>
      <div className="flex items-center gap-3">
        <span aria-hidden className="text-3xl">
          🚀
        </span>
        <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">
          Wonder-o-nauts Studio
        </h1>
      </div>
      <p className="mt-3 max-w-2xl text-[15px] leading-relaxed text-muted">
        Type a question. Get a finished episode: 1080p video with motion and
        music, a vertical Short with burned-in captions, subtitles, chapters,
        two thumbnails and a QC report. Every frame is drawn from code, every
        note synthesised — nothing is downloaded or licensed.
      </p>
    </header>
  );
}

function DraftReview({
  draft,
  onChange,
  onRender,
}: {
  draft: Draft;
  onChange: (d: Draft) => void;
  onRender: () => void;
}) {
  const cfg = draft.videoJson;
  const words = (s: string) => s.trim().split(/\s+/).filter(Boolean).length;
  const total = cfg.scenes.reduce((n, s) => n + words(s.narration), 0);

  const setNarration = (i: number, value: string) => {
    const scenes = cfg.scenes.map((s, j) => (j === i ? { ...s, narration: value } : s));
    onChange({ ...draft, videoJson: { ...cfg, scenes } });
  };

  return (
    <section className="mt-6 space-y-5">
      <div className="rounded-2xl border border-border bg-surface p-5 sm:p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <h2 className="text-lg font-semibold">{cfg.title}</h2>
            <p className="mt-1 text-sm text-muted">
              {cfg.scenes.length} scenes · {total} words · about{" "}
              {Math.round((total / 135) * 10) / 10} minutes ·{" "}
              {draft.source.kind === "youtube"
                ? draft.source.transcriptChars > 0
                  ? `researched from “${draft.source.label}”`
                  : `topic taken from “${draft.source.label}” (no transcript available)`
                : "written from the topic"}
            </p>
          </div>
          <button
            onClick={onRender}
            className="shrink-0 rounded-xl bg-accent px-5 py-3 font-semibold text-accent-ink
                       transition hover:brightness-110"
          >
            Render episode
          </button>
        </div>
        <p className="mt-4 text-sm text-muted">
          Edit any narration before rendering — this is the moment to fix a fact
          or soften a phrase. Rendering takes roughly six minutes.
        </p>
      </div>

      <div className="space-y-3">
        {cfg.scenes.map((s, i) => {
          const w = words(s.narration);
          const off = w < 20 || w > 80;
          return (
            <div key={i} className="rounded-xl border border-border bg-surface p-4">
              <div className="flex flex-wrap items-center gap-3 text-xs">
                <span className="rounded-md bg-surface-2 px-2 py-1 font-mono text-muted">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <span className="font-medium">{s.chapter}</span>
                <span className="text-muted">· {s.sfx}</span>
                {cfg.shorts_scenes?.includes(i + 1) && (
                  <span className="rounded-md bg-sky/20 px-2 py-1 text-sky">in the Short</span>
                )}
                <span className={`ml-auto ${off ? "text-bad" : "text-muted"}`}>
                  {w} words
                </span>
              </div>
              <textarea
                value={s.narration}
                onChange={(e) => setNarration(i, e.target.value)}
                rows={3}
                className="mt-3 w-full resize-y rounded-lg border border-border bg-surface-2 px-3 py-2
                           text-sm leading-relaxed outline-none focus:border-sky"
              />
            </div>
          );
        })}
      </div>

      <details className="rounded-xl border border-border bg-surface p-4">
        <summary className="cursor-pointer text-sm font-medium">
          Scene art (render_scenes.py)
        </summary>
        <pre className="log mt-3 max-h-96 overflow-auto rounded-lg bg-surface-2 p-3 text-muted">
          {draft.renderScenes}
        </pre>
      </details>

      <details className="rounded-xl border border-border bg-surface p-4">
        <summary className="cursor-pointer text-sm font-medium">
          Description &amp; tags
        </summary>
        <pre className="log mt-3 overflow-auto rounded-lg bg-surface-2 p-3 text-muted">
          {cfg.description}
          {"\n\n"}
          {cfg.tags}
        </pre>
      </details>
    </section>
  );
}

function RenderPanel({
  job,
  phase,
  onReset,
}: {
  job: JobView;
  phase: Phase;
  onReset: () => void;
}) {
  const logRef = useRef<HTMLPreElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);

  useEffect(() => {
    if (autoScroll && logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [job.log, autoScroll]);

  const onScroll = useCallback(() => {
    const el = logRef.current;
    if (!el) return;
    setAutoScroll(el.scrollHeight - el.scrollTop - el.clientHeight < 40);
  }, []);

  const art = (name: string) => `/api/jobs/${job.id}/artifact/${name}`;
  const has = (name: string) => job.artifacts.includes(name);
  const qcPassed = job.qc?.includes("QC PASS");

  return (
    <section className="mt-6 space-y-5">
      <div className="rounded-2xl border border-border bg-surface p-5 sm:p-6">
        <div className="flex flex-wrap items-center gap-3">
          <StatusDot phase={phase} />
          <h2 className="text-lg font-semibold">{job.title}</h2>
          <button
            onClick={onReset}
            className="ml-auto rounded-lg border border-border px-3 py-1.5 text-sm text-muted
                       transition hover:border-sky hover:text-foreground"
          >
            New episode
          </button>
        </div>
        <p className="mt-2 text-sm text-muted">
          {phase === "rendering" &&
            "Drawing frames, synthesising narration and music, encoding ten scenes, mastering to −14 LUFS."}
          {phase === "done" && (
            <>
              Finished. QC says{" "}
              <strong className={qcPassed ? "text-good" : "text-accent"}>
                {qcPassed ? "PASS" : "WARN"}
              </strong>
              {qcPassed ? "." : " — read the report before publishing."}
            </>
          )}
          {phase === "failed" &&
            `The build failed (exit ${job.exitCode}). The log below has the reason.`}
        </p>
      </div>

      {phase === "done" && (
        <div className="grid gap-5 sm:grid-cols-2">
          {has("final.mp4") && (
            <Card title="Episode">
              {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
              <video src={art("final.mp4")} controls className="w-full rounded-lg bg-black" />
              <Download href={art("final.mp4")} name="final.mp4" />
            </Card>
          )}
          {has("short.mp4") && (
            <Card title="Short (captions burned in)">
              {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
              <video
                src={art("short.mp4")}
                controls
                className="mx-auto max-h-[420px] rounded-lg bg-black"
              />
              <Download href={art("short.mp4")} name="short.mp4" />
            </Card>
          )}
          {(has("thumbnail_a.jpg") || has("thumbnail_b.jpg")) && (
            <Card title="Thumbnails (A/B)">
              <div className="grid grid-cols-2 gap-2">
                {(["thumbnail_a.jpg", "thumbnail_b.jpg"] as const)
                  .filter(has)
                  .map((n) => (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img key={n} src={art(n)} alt={n} className="w-full rounded-lg" />
                  ))}
              </div>
            </Card>
          )}
          <Card title="Upload sheet & sidecars">
            <ul className="space-y-1.5 text-sm">
              {job.artifacts
                .filter((n) => !n.endsWith(".mp4") && !n.endsWith(".jpg"))
                .map((n) => (
                  <li key={n}>
                    <a
                      href={art(n)}
                      target="_blank"
                      rel="noreferrer"
                      className="text-sky underline-offset-2 hover:underline"
                    >
                      {n}
                    </a>
                  </li>
                ))}
            </ul>
            <p className="mt-3 text-xs text-muted">
              Mark the upload “Made for Kids = YES” (COPPA). metadata.txt has the
              full checklist.
            </p>
          </Card>
        </div>
      )}

      {job.qc && (
        <details open={phase === "done" && !qcPassed} className="rounded-xl border border-border bg-surface p-4">
          <summary className="cursor-pointer text-sm font-medium">QC report</summary>
          <pre className="log mt-3 max-h-80 overflow-auto rounded-lg bg-surface-2 p-3 text-muted">
            {job.qc}
          </pre>
        </details>
      )}

      <div className="rounded-xl border border-border bg-surface p-4">
        <div className="mb-2 flex items-center gap-2 text-sm font-medium">
          Build log
          {phase === "rendering" && (
            <span className="text-xs font-normal text-muted">· updating every 4s</span>
          )}
        </div>
        <pre
          ref={logRef}
          onScroll={onScroll}
          className="log max-h-80 overflow-auto rounded-lg bg-surface-2 p-3 text-muted"
        >
          {job.log || "Waiting for the first output…"}
        </pre>
      </div>
    </section>
  );
}

function StatusDot({ phase }: { phase: Phase }) {
  const map: Record<string, [string, string]> = {
    rendering: ["bg-accent animate-pulse", "Rendering"],
    done: ["bg-good", "Done"],
    failed: ["bg-bad", "Failed"],
  };
  const [cls, label] = map[phase] ?? ["bg-muted", "Idle"];
  return (
    <span className="flex items-center gap-2 text-xs text-muted">
      <span className={`h-2.5 w-2.5 rounded-full ${cls}`} />
      {label}
    </span>
  );
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-border bg-surface p-4">
      <h3 className="mb-3 text-sm font-semibold">{title}</h3>
      {children}
    </div>
  );
}

function Download({ href, name }: { href: string; name: string }) {
  return (
    <a
      href={href}
      download={name}
      className="mt-3 inline-block rounded-lg border border-border px-3 py-1.5 text-sm text-muted
                 transition hover:border-sky hover:text-foreground"
    >
      Download {name}
    </a>
  );
}

function Footer() {
  return (
    <footer className="mt-14 border-t border-border pt-6 text-xs leading-relaxed text-muted">
      <p>
        A YouTube link is used as <strong>research only</strong> — the transcript
        informs an original script. No audio, frames or phrasing from the source
        ends up in the output, which is what keeps every episode copyright-clean.
      </p>
      <p className="mt-2">
        Rendering runs in an ephemeral Vercel Sandbox. Artifacts stream from that
        sandbox, so download anything you want to keep.
      </p>
    </footer>
  );
}
