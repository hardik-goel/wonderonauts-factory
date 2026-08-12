"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { Draft, Job } from "@/lib/types";
import { parseScript } from "@/lib/parse-script";

type JobView = Job & { log: string };
type Phase = "idle" | "writing" | "review" | "rendering" | "done" | "failed";
type Mode = "ai" | "write" | "bundled" | "dogs";

type Capabilities = {
  ai: boolean;
  props: string[];
  looks: readonly string[];
  presets: { slug: string; title: string; blurb: string }[];
};

const EXAMPLES = [
  "Why do magnets stick together?",
  "Why do we need to sleep?",
  "What are clouds made of?",
  "Why does the Moon change shape?",
];

const BLANK_SCENES = [
  "Blast off!", "The big question", "Not what you think", "Secret one",
  "A closer look", "Secret two", "Try it yourself", "The numbers",
  "Bonus wonder", "Mission complete!",
].map((chapter) => ({ chapter, narration: "" }));

export default function Studio() {
  const [caps, setCaps] = useState<Capabilities | null>(null);
  const [mode, setMode] = useState<Mode>("write");
  const [phase, setPhase] = useState<Phase>("idle");
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [job, setJob] = useState<JobView | null>(null);

  useEffect(() => {
    fetch("/api/capabilities")
      .then((r) => r.json())
      .then((c: Capabilities) => {
        setCaps(c);
        setMode(c.ai ? "ai" : "write");
      })
      .catch(() => setCaps({ ai: false, props: ["rocket"], looks: ["land"], presets: [] }));
  }, []);

  const busy = phase === "writing" || phase === "rendering";

  const post = useCallback(async (url: string, body: unknown) => {
    const res = await fetch(url, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error ?? "Request failed.");
    return data;
  }, []);

  async function makeDraft(url: string, body: unknown) {
    setError(null);
    setDraft(null);
    setJob(null);
    setPhase("writing");
    try {
      setDraft((await post(url, body)) as Draft);
      setPhase("review");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setPhase("idle");
    }
  }

  async function render(body: unknown) {
    setError(null);
    setPhase("rendering");
    try {
      setJob({ ...((await post("/api/render", body)) as Job), log: "" });
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setPhase(draft ? "review" : "idle");
    }
  }

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

  const showInput = phase === "idle" || phase === "writing";

  return (
    <main className="mx-auto w-full max-w-5xl px-5 py-10 sm:py-14">
      <Header aiEnabled={caps?.ai ?? false} />

      {showInput && caps && (
        <>
          <ModeTabs mode={mode} setMode={setMode} caps={caps} busy={busy} />
          {mode === "ai" && (
            <AiPanel busy={busy} phase={phase} onSubmit={(topic) => void makeDraft("/api/draft", { topic })} />
          )}
          {mode === "write" && (
            <WritePanel caps={caps} busy={busy} onSubmit={(body) => void makeDraft("/api/scaffold", body)} />
          )}
          {mode === "dogs" && (
            <DogsPanel busy={busy} onSubmit={(body) => void makeDraft("/api/dogs", body)} />
          )}
          {mode === "bundled" && (
            <BundledPanel caps={caps} busy={busy} onRender={(preset) => void render({ preset })} />
          )}
        </>
      )}

      {error && (
        <p className="mt-5 rounded-xl border border-bad/40 bg-bad/10 px-4 py-3 text-sm text-bad">
          {error}
        </p>
      )}

      {draft && phase === "review" && (
        <DraftReview draft={draft} onChange={setDraft} onRender={() => void render(draft)} onBack={reset} />
      )}

      {job && (phase === "rendering" || phase === "done" || phase === "failed") && (
        <RenderPanel job={job} phase={phase} onReset={reset} />
      )}

      <Footer />
    </main>
  );
}

function Header({ aiEnabled }: { aiEnabled: boolean }) {
  return (
    <header>
      <div className="flex flex-wrap items-center gap-3">
        <span aria-hidden className="text-3xl">🚀</span>
        <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">
          Wonder-o-nauts Studio
        </h1>
        <span
          className={`rounded-full border px-2.5 py-1 text-[11px] ${
            aiEnabled
              ? "border-sky/40 bg-sky/10 text-sky"
              : "border-good/40 bg-good/10 text-good"
          }`}
        >
          {aiEnabled ? "AI writing enabled" : "no API key — keyless mode"}
        </span>
      </div>
      <p className="mt-3 max-w-2xl text-[15px] leading-relaxed text-muted">
        A finished episode: 1080p video with motion and music, a vertical Short
        with burned-in captions, subtitles, chapters, two thumbnails and a QC
        report. Every frame is drawn from code, every note synthesised — nothing
        is downloaded or licensed.
      </p>
    </header>
  );
}

function ModeTabs({
  mode,
  setMode,
  caps,
  busy,
}: {
  mode: Mode;
  setMode: (m: Mode) => void;
  caps: Capabilities;
  busy: boolean;
}) {
  const tabs: { id: Mode; label: string; hint: string; disabled?: boolean }[] = [
    {
      id: "ai",
      label: "Write it for me",
      hint: caps.ai ? "Claude drafts the script" : "needs ANTHROPIC_API_KEY",
      disabled: !caps.ai,
    },
    { id: "write", label: "I'll write it", hint: "no API key needed" },
    { id: "dogs", label: "\u{1F436} Dad jokes", hint: "two dogs, new setting each time" },
    { id: "bundled", label: "Render a sample", hint: "zero typing" },
  ];

  return (
    <div className="mt-8 flex flex-wrap gap-2">
      {tabs.map((t) => (
        <button
          key={t.id}
          onClick={() => !t.disabled && setMode(t.id)}
          disabled={t.disabled || busy}
          title={t.disabled ? "Set ANTHROPIC_API_KEY to enable this" : undefined}
          className={`rounded-xl border px-4 py-2.5 text-left transition disabled:cursor-not-allowed disabled:opacity-40 ${
            mode === t.id
              ? "border-accent bg-accent/10"
              : "border-border hover:border-sky"
          }`}
        >
          <span className="block text-sm font-medium">{t.label}</span>
          <span className="block text-xs text-muted">{t.hint}</span>
        </button>
      ))}
    </div>
  );
}

function AiPanel({
  busy,
  phase,
  onSubmit,
}: {
  busy: boolean;
  phase: Phase;
  onSubmit: (topic: string) => void;
}) {
  const [topic, setTopic] = useState("");
  return (
    <section className="mt-4 rounded-2xl border border-border bg-surface p-5 sm:p-6">
      <label htmlFor="topic" className="block text-sm font-medium text-muted">
        A question a child would ask — or a YouTube link to research
      </label>
      <div className="mt-3 flex flex-col gap-3 sm:flex-row">
        <input
          id="topic"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && topic.trim() && !busy) onSubmit(topic);
          }}
          placeholder="Why is the sea salty?"
          disabled={busy}
          className="min-w-0 flex-1 rounded-xl border border-border bg-surface-2 px-4 py-3 text-base
                     outline-none placeholder:text-muted/60 focus:border-sky disabled:opacity-60"
        />
        <button
          onClick={() => onSubmit(topic)}
          disabled={!topic.trim() || busy}
          className="rounded-xl bg-accent px-5 py-3 font-semibold text-accent-ink transition
                     hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-40"
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
          Researching and writing ten scenes plus the scene art. A minute or two.
        </p>
      )}
    </section>
  );
}

function WritePanel({
  caps,
  busy,
  onSubmit,
}: {
  caps: Capabilities;
  busy: boolean;
  onSubmit: (body: unknown) => void;
}) {
  const [title, setTitle] = useState("");
  const [prop, setProp] = useState("rocket");
  const [look, setLook] = useState("land");
  const [scenes, setScenes] = useState(BLANK_SCENES);
  const [pasting, setPasting] = useState(false);
  const [paste, setPaste] = useState("");
  const [pasteNote, setPasteNote] = useState<string | null>(null);

  const words = (s: string) => s.trim().split(/\s+/).filter(Boolean).length;
  const written = scenes.filter((s) => s.narration.trim()).length;

  const update = (i: number, patch: Partial<(typeof scenes)[number]>) =>
    setScenes(scenes.map((s, j) => (j === i ? { ...s, ...patch } : s)));

  function applyPaste() {
    const { title: t, scenes: parsed } = parseScript(paste);
    if (!parsed.length) {
      setPasteNote("Couldn't find any scenes in that. Separate them with blank lines, or paste a table.");
      return;
    }
    if (t) setTitle(t);
    setScenes(parsed);
    setPasting(false);
    setPaste("");
    setPasteNote(null);
  }

  return (
    <section className="mt-4 space-y-4">
      <div className="rounded-2xl border border-border bg-surface p-5 sm:p-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <p className="max-w-xl text-sm text-muted">
            You write the narration; the studio builds the scene art, voice,
            music, captions, thumbnails and the upload sheet. Aim for{" "}
            <strong className="text-foreground">35–55 words</strong> a scene —
            that lands around four minutes. Already have a script? Use{" "}
            <strong className="text-foreground">Paste a whole script</strong> and
            it fills every scene for you.
          </p>
          <button
            onClick={() => {
              setPasting(!pasting);
              setPasteNote(null);
            }}
            disabled={busy}
            className="shrink-0 rounded-lg border border-accent bg-accent/10 px-3 py-2
                       text-sm font-medium text-foreground transition hover:bg-accent/20"
          >
            {pasting ? "Cancel" : "📋 Paste a whole script"}
          </button>
        </div>

        {pasting && (
          <div className="mt-4">
            <textarea
              value={paste}
              onChange={(e) => setPaste(e.target.value)}
              rows={10}
              autoFocus
              placeholder={`Paste the whole thing here — a table, a numbered outline, or just paragraphs.

Title: The Hare and the Tortoise

1. Blast off!
Hello, Wonder-o-nauts! Today we are telling a very old story…

2. Meet the hare
The hare was fast. Really fast…`}
              className="log w-full resize-y rounded-lg border border-border bg-surface-2 px-3 py-2
                         outline-none placeholder:text-muted/50 focus:border-sky"
            />
            <div className="mt-3 flex flex-wrap items-center gap-3">
              <button
                onClick={applyPaste}
                disabled={!paste.trim()}
                className="rounded-lg bg-sky px-4 py-2 text-sm font-medium text-white
                           transition hover:brightness-110 disabled:opacity-40"
              >
                Fill the scenes
              </button>
              <span className="text-xs text-muted">
                Markdown tables, “1. Chapter” outlines and blank-line-separated
                paragraphs all work. Missing chapter labels get filled in.
              </span>
            </div>
            {pasteNote && <p className="mt-2 text-xs text-bad">{pasteNote}</p>}
          </div>
        )}

        <div className="mt-4 grid gap-3 sm:grid-cols-[1fr_auto_auto]">
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Why do magnets stick together?"
            disabled={busy}
            className="min-w-0 rounded-xl border border-border bg-surface-2 px-4 py-3
                       outline-none placeholder:text-muted/60 focus:border-sky"
          />
          <select
            value={prop}
            onChange={(e) => setProp(e.target.value)}
            disabled={busy}
            className="rounded-xl border border-border bg-surface-2 px-3 py-3 text-sm outline-none focus:border-sky"
          >
            {caps.props.map((p) => (
              <option key={p} value={p}>{p.replace(/_/g, " ")}</option>
            ))}
          </select>
          <select
            value={look}
            onChange={(e) => setLook(e.target.value)}
            disabled={busy}
            className="rounded-xl border border-border bg-surface-2 px-3 py-3 text-sm outline-none focus:border-sky"
          >
            {caps.looks.map((l) => (
              <option key={l} value={l}>{l}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="space-y-2">
        {scenes.map((s, i) => {
          const w = words(s.narration);
          const off = w > 0 && (w < 20 || w > 80);
          return (
            <div key={i} className="rounded-xl border border-border bg-surface p-4">
              <div className="flex flex-wrap items-center gap-3 text-xs">
                <span className="rounded-md bg-surface-2 px-2 py-1 font-mono text-muted">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <input
                  value={s.chapter}
                  onChange={(e) => update(i, { chapter: e.target.value })}
                  placeholder="Chapter label"
                  className="rounded-md border border-border bg-surface-2 px-2 py-1 text-xs outline-none focus:border-sky"
                />
                <span className={`ml-auto ${off ? "text-bad" : "text-muted"}`}>
                  {w} words
                </span>
              </div>
              <textarea
                value={s.narration}
                onChange={(e) => update(i, { narration: e.target.value })}
                rows={2}
                placeholder={
                  i === 0
                    ? "Hello, Wonder-o-nauts! Today we are finding out…"
                    : "What the narrator says in this scene."
                }
                className="mt-3 w-full resize-y rounded-lg border border-border bg-surface-2 px-3 py-2
                           text-sm leading-relaxed outline-none placeholder:text-muted/50 focus:border-sky"
              />
            </div>
          );
        })}
      </div>

      <button
        onClick={() => onSubmit({ title, scenes, prop, look })}
        disabled={busy || !title.trim() || written < 3}
        className="rounded-xl bg-accent px-5 py-3 font-semibold text-accent-ink transition
                   hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-40"
      >
        Build the episode ({written} scene{written === 1 ? "" : "s"} written)
      </button>
    </section>
  );
}

const DOG_EXAMPLE = `Title: Beach Day Bonanza

Rex: Hey Bo, why don't crabs ever share their snacks?
Bo: I don't know Rex. Why not?
Rex: Because they are shellfish!
Bo: That is the worst one yet. Do another.
Rex: What do you call a dog that does magic tricks?
Bo: Please stop.
Rex: A labracadabrador!`;

function DogsPanel({
  busy,
  onSubmit,
}: {
  busy: boolean;
  onSubmit: (body: unknown) => void;
}) {
  const [script, setScript] = useState("");
  const [setting, setSetting] = useState("");
  const [settings, setSettings] = useState<{ id: string; label: string }[]>([]);

  useEffect(() => {
    fetch("/api/dogs")
      .then((r) => r.json())
      .then((d) => setSettings(d.settings ?? []))
      .catch(() => setSettings([]));
  }, []);

  const lineRe = /^\s*[A-Za-z][\w '.-]{0,24}\s*[:\-\u2014]\s*\S/;
  const lines = script
    .split("\n")
    .filter((l) => lineRe.test(l) && !/^\s*title\s*[:\-\u2014]/i.test(l));
  const speakers = Array.from(
    new Set(lines.map((l) => l.split(/[:\-\u2014]/)[0].trim().toLowerCase())),
  );

  return (
    <section className="mt-4 space-y-4">
      <div className="rounded-2xl border border-border bg-surface p-5 sm:p-6">
        <p className="text-sm text-muted">
          Two dogs, one dad joke, a different setting every time. Write it as{" "}
          <code className="rounded bg-surface-2 px-1.5 py-0.5 text-xs">Name: line</code>{" "}
          \u2014 one line each. Each dog gets its own voice, and only the one with
          the line is drawn with its mouth open.
        </p>

        <textarea
          value={script}
          onChange={(e) => setScript(e.target.value)}
          rows={12}
          placeholder={DOG_EXAMPLE}
          className="log mt-4 w-full resize-y rounded-lg border border-border bg-surface-2 px-3 py-2
                     outline-none placeholder:text-muted/50 focus:border-sky"
        />

        <div className="mt-3 flex flex-wrap items-center gap-3">
          <button
            onClick={() => setScript(DOG_EXAMPLE)}
            disabled={busy}
            className="rounded-lg border border-border px-3 py-2 text-sm text-muted
                       transition hover:border-sky hover:text-foreground"
          >
            Use the example
          </button>
          <select
            value={setting}
            onChange={(e) => setSetting(e.target.value)}
            disabled={busy}
            className="rounded-lg border border-border bg-surface-2 px-3 py-2 text-sm outline-none focus:border-sky"
          >
            <option value="">Surprise me (a new setting each time)</option>
            {settings.map((s) => (
              <option key={s.id} value={s.id}>{s.label}</option>
            ))}
          </select>
          <span className="text-xs text-muted">
            {lines.length} line{lines.length === 1 ? "" : "s"} \u00b7{" "}
            {speakers.length} speaker{speakers.length === 1 ? "" : "s"}
            {speakers.length > 2 && " \u2014 only the first two get a dog"}
          </span>
        </div>
      </div>

      <button
        onClick={() => onSubmit({ script, setting: setting || undefined })}
        disabled={busy || lines.length < 2}
        className="rounded-xl bg-accent px-5 py-3 font-semibold text-accent-ink transition
                   hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-40"
      >
        Build the episode
      </button>
    </section>
  );
}

function BundledPanel({
  caps,
  busy,
  onRender,
}: {
  caps: Capabilities;
  busy: boolean;
  onRender: (slug: string) => void;
}) {
  return (
    <section className="mt-4 rounded-2xl border border-border bg-surface p-5 sm:p-6">
      <p className="text-sm text-muted">
        Five finished episodes ship with the repo. Rendering one needs no API key
        and no typing — it proves the whole pipeline end to end in about six
        minutes.
      </p>
      <div className="mt-4 space-y-2">
        {caps.presets.map((p) => (
          <button
            key={p.slug}
            onClick={() => onRender(p.slug)}
            disabled={busy}
            className="flex w-full items-center gap-4 rounded-xl border border-border bg-surface-2 p-4
                       text-left transition hover:border-sky disabled:opacity-40"
          >
            <span className="min-w-0">
              <span className="block text-sm font-medium">{p.title}</span>
              <span className="block text-xs text-muted">{p.blurb}</span>
            </span>
            <span className="ml-auto shrink-0 text-xs text-sky">Render →</span>
          </button>
        ))}
      </div>
    </section>
  );
}

function DraftReview({
  draft,
  onChange,
  onRender,
  onBack,
}: {
  draft: Draft;
  onChange: (d: Draft) => void;
  onRender: () => void;
  onBack: () => void;
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
                  : `topic from “${draft.source.label}” (no transcript available)`
                : "written from the topic"}
            </p>
          </div>
          <div className="flex shrink-0 gap-2">
            <button
              onClick={onBack}
              className="rounded-xl border border-border px-4 py-3 text-sm text-muted
                         transition hover:border-sky hover:text-foreground"
            >
              Back
            </button>
            <button
              onClick={onRender}
              className="rounded-xl bg-accent px-5 py-3 font-semibold text-accent-ink transition hover:brightness-110"
            >
              Render episode
            </button>
          </div>
        </div>
        <p className="mt-4 text-sm text-muted">
          Edit any narration before rendering — this is the moment to fix a fact.
          Rendering takes roughly six minutes.
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
                <span className={`ml-auto ${off ? "text-bad" : "text-muted"}`}>{w} words</span>
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
          Scene art (render_scenes.py) — edit this file after downloading to art-direct it
        </summary>
        <pre className="log mt-3 max-h-96 overflow-auto rounded-lg bg-surface-2 p-3 text-muted">
          {draft.renderScenes}
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
            "Drawing frames, synthesising narration and music, encoding scenes, mastering to −14 LUFS."}
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
              { }
              <video src={art("final.mp4")} controls className="w-full rounded-lg bg-black" />
              <Download href={art("final.mp4")} name="final.mp4" />
            </Card>
          )}
          {has("short.mp4") && (
            <Card title="Short (captions burned in)">
              { }
              <video src={art("short.mp4")} controls className="mx-auto max-h-[420px] rounded-lg bg-black" />
              <Download href={art("short.mp4")} name="short.mp4" />
            </Card>
          )}
          {(has("thumbnail_a.jpg") || has("thumbnail_b.jpg")) && (
            <Card title="Thumbnails (A/B)">
              <div className="grid grid-cols-2 gap-2">
                {(["thumbnail_a.jpg", "thumbnail_b.jpg"] as const).filter(has).map((n) => (
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
        <details
          open={phase === "done" && !qcPassed}
          className="rounded-xl border border-border bg-surface p-4"
        >
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
        <strong className="text-foreground">No API key required.</strong> Writing
        the words is the only step that needs a model — “I’ll write it” and
        “Render a sample” run entirely without one. Rendering, art, narration,
        music and captions never call a paid API.
      </p>
      <p className="mt-2">
        A YouTube link is used as <strong>research only</strong> — the transcript
        informs an original script. No audio, frames or phrasing from the source
        ends up in the output.
      </p>
      <p className="mt-2">
        Rendering runs in an ephemeral Vercel Sandbox. Artifacts stream from that
        sandbox, so download anything you want to keep.
      </p>
    </footer>
  );
}
