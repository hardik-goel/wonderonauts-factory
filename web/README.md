# Wonder-o-nauts Studio

A hosted UI over the factory: get a finished episode without a terminal.

## Four ways in — three of them need no API key

The factory's promise is "no API keys, no accounts". Writing the *words* is the
one step that needs either a model or a human, so only that step can require a
key. Everything downstream — scene art, narration, music, captions, thumbnails,
encoding, mastering — never calls a paid API.

| Mode | Needs a key? | What you supply |
|---|---|---|
| **Write it for me** | yes — `ANTHROPIC_API_KEY` | a question, or a YouTube link to research |
| **I'll write it** | **no** | the narration; the studio generates the scene art |
| **Render a sample** | **no** | nothing — builds one of the five bundled episodes |
| **Dad jokes** | **no** | two dogs' dialogue; the studio picks the setting |

The UI reads `/api/capabilities` on load. With no key set, the AI tab is
disabled with the reason shown and "I'll write it" is selected by default — no
dead-end error.

```
                    ┌── /api/draft ─────► Claude writes the script   (key)
topic / link / words ┼── /api/scaffold ──► templated script + art    (keyless)
                    ├── /api/dogs ──────► two-dog dialogue + art     (keyless)
                    └── preset ─────────► already in the repo        (keyless)
        │
        ▼
  you review & edit the narration
        │
        ▼
  /api/render ─────────► Vercel Sandbox: clone repo → factory.py --shorts
        │                (detached; the build outlives the request)
        ▼
  /api/jobs/[id] ──────► poll status + log, then stream artifacts
```

### What the keyless art looks like

`lib/scaffold.ts` composes each frame from real toolkit primitives, rotating
through four layouts so ten scenes don't look identical. It is deliberately
template-driven rather than bespoke: a watchable episode, not a designed one.
The generated `render_scenes.py` is shown in the review step and is ordinary
Python — download it and art-direct it by hand if you want more.

`pnpm exec tsx scripts/verify-scaffold.ts` renders every prop and look through
the real toolkit and lints the result, because a bad primitive call in generated
code would otherwise first surface a minute into someone's build.

### Dad jokes: two dogs, one setting, two voices

Paste dialogue as `Name: line`, one line per beat, with an optional
`Title: ...`. `lib/dogs.ts` turns it into an episode where the two characters
never blur together:

- **Voice** — each speaker gets its own Edge TTS voice, written per scene as
  `scenes[].voice`. `factory.py` synthesizes that scene with that voice; the TTS
  cache key includes it, so changing one character re-synthesizes only their
  lines.
- **Mouth and expression** — the dog with the current line is drawn with an open
  muzzle, the other with a closed one, and the punchline gets the `laugh` face.
  This is a per-**line** mouth state, not phoneme lip-sync: the pipeline renders
  one still per scene and pans it, so there is no frame-by-frame mouth to
  animate. Real lip-sync needs a frame-sequence renderer and a forced aligner —
  it is in `BACKLOG.md`, not in this.
- **Setting** — beach, mountains, park, night camp, rainy day or the moon,
  shuffled per title so it differs every time, except that an obvious word in
  the title wins: "Mountain Hike Havoc" is set in the mountains, not on the moon.
  You can also pick one explicitly.

The generated `video.json` carries `format: "dialogue"`, which tells
`factory.py` and the QC report to judge it as a two-hander: "Why not?" is a
complete beat, not a scene that forgot its narration, and half a minute is a
finished joke, not a short episode.

`pnpm exec tsx scripts/verify-dogs.ts` renders all six settings through the real
toolkit and asserts each speaker keeps exactly one voice.

## Why the split

**Vercel runs the UI; the Sandbox runs the render.** A build is ~6 minutes of
CPU, needs the ffmpeg binary plus Pillow/numpy, and writes hundreds of MB of
intermediates — none of which fits a serverless function. The function creates a
microVM, starts the build **detached**, and returns.

**The sandbox is the job store.** A job id *is* a sandbox name. The log, the exit
code, the metadata and the artifacts all live in that sandbox's filesystem, and
sandboxes are persistent by default (auto-snapshot on stop, restored on resume).
That means no database, no queue, and no state that can drift out of sync with
the render.

## Setup

```bash
cd web
pnpm install
vercel link                  # creates/links the Vercel project
vercel env pull              # writes .env.local with VERCEL_OIDC_TOKEN
```

Set these in the Vercel project (and in `.env.local` for local dev):

| Variable | Required | What it's for |
|---|---|---|
| `ANTHROPIC_API_KEY` | **yes** | Writing the script and the scene art |
| `FACTORY_SNAPSHOT_ID` | no, but do it | Pre-baked ffmpeg + deps; saves ~90s per render |
| `FACTORY_REPO_URL` | no | Defaults to the public factory repo |
| `FACTORY_REPO_TOKEN` | only if private | GitHub token for cloning |
| `VERCEL_TOKEN` / `VERCEL_TEAM_ID` / `VERCEL_PROJECT_ID` | local dev only | Sandbox auth when `VERCEL_OIDC_TOKEN` is absent |

Then bake the snapshot once:

```bash
pnpm dlx tsx scripts/create-snapshot.ts
# → FACTORY_SNAPSHOT_ID=snap_...
```

Run it:

```bash
pnpm dev            # http://localhost:3000
vercel deploy       # preview
vercel deploy --prod
```

## Costs per episode

| | |
|---|---|
| Script generation | one Claude Opus 5 call, ~15-30k output tokens |
| Render | ~6 min on 4 vCPU ≈ **$0.03-0.06** of Sandbox compute |
| Narration, music, art | $0 — Edge TTS is free, everything else is generated |

Hobby includes 5 Sandbox CPU-hours/month (roughly 50 renders) and caps a
sandbox at 45 minutes. Pro raises both. Sandbox runs in `iad1` only.

## The YouTube boundary

A link is used as **research input only**: the transcript is fetched, and the
model writes an original script informed by it. No audio, no frames, no phrasing
is carried over. That boundary is what keeps the factory's copyright-clean
guarantee intact — do not extend `lib/youtube.ts` to download media.

Transcript scraping has no official API and is regularly blocked from datacenter
IPs. Every failure path degrades to "use the video title as the topic" rather
than erroring, so a blocked fetch still produces an episode.

## Layout

```
app/page.tsx                          the studio (one client component)
app/api/draft/route.ts                topic → script            (maxDuration 300)
app/api/render/route.ts               script → sandbox build    (maxDuration 120)
app/api/jobs/[id]/route.ts            poll status + log; DELETE stops the VM
app/api/jobs/[id]/artifact/[name]     streams an artifact out of the sandbox
lib/script.ts                         the script writer + JSON schema
lib/toolkit-reference.ts              condensed toolkit API — KEEP IN SYNC
lib/sandbox.ts                        render orchestration
lib/youtube.ts                        transcript research
scripts/create-snapshot.ts            one-time dependency bake
```

`lib/toolkit-reference.ts` is the one file that can rot silently: it tells the
model which primitives exist. Add a primitive to `engine/toolkit.py` and it must
be added there too, or generated scene code will call something that isn't there.

## Limits worth knowing

- **Artifacts live in the sandbox.** They stream out on demand and disappear when
  the sandbox is deleted. Download anything you want to keep. Add Vercel Blob if
  you need durable storage.
- **No auth.** Anyone who can reach the deployment can spend your Sandbox and
  Anthropic budget. Put Vercel Authentication (or your own gate) in front of it
  before sharing the URL.
- **One episode at a time per browser tab.** The UI holds a single job; the
  backend has no such limit.
