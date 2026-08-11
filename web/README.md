# Wonder-o-nauts Studio

A hosted UI over the factory: type a question (or paste a YouTube link), get a
finished episode. No terminal required.

```
topic / YouTube link
        │
        ▼
  /api/draft ──────────► Claude writes video.json + render_scenes.py
        │                (transcript is research only — output stays original)
        ▼
  you review & edit the narration
        │
        ▼
  /api/render ─────────► Vercel Sandbox: clone repo → factory.py --shorts
        │                (detached; the build outlives the request)
        ▼
  /api/jobs/[id] ──────► poll status + log, then stream artifacts
```

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
