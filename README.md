# Wonder-o-nauts Video Factory

**One command turns a folder of text and Python into a finished, YouTube-ready
children's science episode.**

1080p video with motion and music, a vertical Short with burned-in captions,
subtitles, chapters, two A/B thumbnails, an upload sheet, and a QC report — from
`python3 factory.py projects/<episode> --shorts`.

Everything is generated. Visuals are drawn by Pillow, music and sound effects
are synthesized from oscillators with numpy, scripts are original, narration
comes from free Edge TTS voices. Nothing is downloaded, sampled, traced or
licensed. **No API keys, no accounts, no paid services, zero marginal cost per
episode.**

```
projects/why-is-the-ocean-salty/          →   final.mp4        3:19, 1080p, −14 LUFS
  video.json         (script + config)        short.mp4        1080×1920, captions burned in
  render_scenes.py   (scene art as code)      captions.srt     52 sentence cues
                                              thumbnail_a/b.jpg
                                              metadata.txt     title, chapters, checklist
                                              qc_report.txt    PASS
```

---

## Table of contents

- [Why this exists](#why-this-exists) · [What you get](#what-you-get-per-episode)
- [Quickstart](#quickstart) · [Usage](#usage) · [`video.json` reference](#videojson-reference)
- [Architecture](#architecture) · [Caching model](#caching-model) · [Design decisions](#design-decisions)
- [Making a new episode](#making-a-new-episode) · [Extending the toolkit](#extending-the-toolkit)
- [Quality control](#quality-control) · [Uploading](#uploading) · [Season workflow](#season-workflow)
- [Testing and CI](#testing-and-ci) · [Troubleshooting](#troubleshooting)
- [Provenance and licensing](#provenance-and-licensing) · [Roadmap](#roadmap)

---

## Why this exists

Children's educational video is expensive to make and cheap to make *badly*.
The usual costs are animation, voice talent, music licensing, and the editing
labour of assembling all three. The usual failure is a channel that publishes
three good episodes and then stops, because episode four costs the same as
episode one.

This repo removes the marginal cost. An episode is **two text files**. Everything
downstream — art, voice, music, motion, captions, thumbnails, loudness, metadata
— is derived from them by code. Episode twenty costs the same as episode five:
the time it takes to research and write it.

**The economics.** Stock music subscriptions, TTS credits, and stock footage
licences all price per asset or per month. Here the marginal cost of an episode
is zero and the fixed cost is a laptop. Nothing in an output file traces back to
a third-party licence, so there is no rights holder who can demand a takedown,
no attribution to maintain, and no subscription that can lapse and orphan a back
catalogue.

**The consistency argument.** Because every frame is composed from one shared
primitive library (`engine/toolkit.py`), episodes look like they belong to the
same channel without anyone enforcing a style guide. A new shape added for
episode five is available to episode twelve. The visual identity compounds
instead of drifting.

**The two-touchpoint workflow.** Per episode the owner does exactly two things:
run one command, then review the output. Everything between is automated, and
the review is designed to take two minutes — `qc_report.txt` leads with a
`PASS`/`WARN` verdict and the reasons.

### Who it's for

- A solo creator running an educational channel who wants a repeatable pipeline
  rather than a per-video editing project.
- Anyone who needs consistent explainer video at volume: internal training,
  documentation, course material, localisation.
- As a reference implementation: a deterministic, fully-generated media pipeline
  with real caching, real QC, and no external dependencies.

### What it is not

Not an animation studio. The pipeline is **stills plus Ken Burns motion** — a
deliberate constraint that keeps builds fast and the art authorable as code. If
you need character animation, this is the wrong tool.

---

## What you get per episode

Everything lands in `projects/<episode>/output/`:

| File | What it is |
|---|---|
| `final.mp4` | 1080p H.264 / AAC. Ken Burns motion, music bed, SFX, channel sting, mastered to −14 LUFS |
| `short.mp4` | 1080×1920 vertical Short with burned-in captions, built from `shorts_scenes` (needs `--shorts`) |
| `captions.srt` | Sentence-level subtitles, timed from the *measured* narration audio |
| `short_captions.srt` | The same cues re-timed onto the Short's own timeline |
| `thumbnail_a.jpg` | Variant A — text dominant, 1280×720, under 2 MB |
| `thumbnail_b.jpg` | Variant B — character dominant, for A/B testing |
| `metadata.txt` | Title, description, tags, chapter timestamps, file sizes, upload checklist |
| `qc_report.txt` | `PASS`/`WARN` verdict with reasons, per-scene pacing, loudness, caption coverage |
| `build_manifest.json` | Version, seeds, per-scene narration hashes, ffmpeg build, artifact sizes |
| `preview.mp4` | Draft only (`--preview`); named differently so it can never overwrite `final.mp4` |

Language variants land in `output/<code>/` with the same layout.

---

## Quickstart

### Requirements

| | |
|---|---|
| Python | 3.9 or newer |
| ffmpeg + ffprobe | on `PATH`, with `libx264`, `aac`, `loudnorm`, `overlay` |
| Python packages | `pillow>=10.0`, `numpy>=1.24`, `edge-tts>=6.1` |
| Network | only for Edge TTS, and only when narration text changes |
| Disk | ~300 MB per built episode (~200 MB reclaimable with `--clean`) |

`libass` and `libfreetype` are **not** required — captions are drawn with Pillow
precisely so minimal ffmpeg builds work.

### Install

```bash
git clone https://github.com/hardik-goel/wonderonauts-factory
cd wonderonauts-factory

python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

brew install ffmpeg          # macOS
# sudo apt install ffmpeg fonts-dejavu-core     # Debian/Ubuntu
```

> **Use the venv.** A system `python3` without numpy will fail at the music
> stage. Either `source .venv/bin/activate` once, or prefix commands with
> `.venv/bin/python`. Examples below use plain `python3` and assume the venv is
> active.

### Verify the toolchain

```bash
python3 factory.py --check
```

Checks Python version, the three packages, ffmpeg/ffprobe, the `libx264`, `aac`,
`libmp3lame`, `loudnorm` and `overlay` capabilities, the display font, and which
projects it can see. Fix anything marked `FAIL` before building.

### Build an episode

Five ship with the repo:

```bash
python3 factory.py projects/why-is-the-sky-blue      --shorts   # ep 1, light scattering
python3 factory.py projects/how-do-planes-fly        --shorts   # ep 2, lift and thrust
python3 factory.py projects/why-do-we-have-seasons   --shorts   # ep 3, axial tilt
python3 factory.py projects/where-does-rain-come-from --shorts  # ep 4, the water cycle
python3 factory.py projects/why-is-the-ocean-salty   --shorts   # ep 5, weathering
```

First run takes about six minutes: frames render, narration downloads, ten
scenes encode in parallel, the master is normalized. **Re-runs finish in seconds
unless something actually changed.**

Then read the two-minute review:

```bash
cat  projects/why-is-the-ocean-salty/output/qc_report.txt   # should say PASS
open projects/why-is-the-ocean-salty/output/final.mp4
cat  projects/why-is-the-ocean-salty/output/metadata.txt    # your upload sheet
```

---

## Usage

### Every command

```bash
# Building
python3 factory.py projects/<episode>                 # full 1080p build
python3 factory.py projects/<episode> --shorts        # + vertical 9:16 Short
python3 factory.py projects/<episode> --preview       # fast 640×360 draft, under a minute
python3 factory.py projects/<episode> --lang hi       # language variant
python3 factory.py projects/<episode> --voice en-GB-SoniaNeural
python3 factory.py --all --shorts                     # every episode marked 'ready'

# Inspecting
python3 factory.py --check                            # preflight: deps, encoders, filters, fonts
python3 factory.py --validate                         # lint every episode's video.json
python3 factory.py projects/<episode> --validate      # lint one
python3 factory.py --season                           # season status table
python3 factory.py --version

# Housekeeping
python3 factory.py projects/<episode> --clean         # drop rebuildable caches
python3 factory.py --all --clean                      # ...for the whole season
python3 factory.py projects/<episode> --force         # ignore every cache and rebuild
```

### Every flag

| Flag | Effect |
|---|---|
| `--shorts` | Also build `short.mp4` from `shorts_scenes`, with captions burned in |
| `--preview` | 640×360, `ultrafast`, CRF 30. No music, no thumbnails, no QC. Writes `preview.mp4`, never `final.mp4` |
| `--lang CODE` | Build the variant declared in `languages.<CODE>`. Output goes to `output/<CODE>/` |
| `--voice NAME` | Override the Edge TTS voice. `edge-tts --list-voices` for the catalogue |
| `--all` | Build every episode whose `season.json` status is `ready` |
| `--check` | Preflight only |
| `--validate` | Lint `video.json` and exit. Non-zero exit if anything is wrong |
| `--clean` | Delete `clips/` and synthesized music beds. **Keeps narration and `output/`.** Requires a project path or `--all` |
| `--force` | Rebuild everything, including frames and narration |
| `--jobs N` | Parallel scene encodes (default 4) |
| `--no-loudnorm` | Skip EBU R128 normalization |
| `--no-short-captions` | Do not burn caption cards into the Short |

### Typical loops

**Writing a script** — check pacing without waiting for a full encode:

```bash
python3 factory.py projects/<slug> --validate    # instant
python3 factory.py projects/<slug> --preview     # under a minute
```

**Iterating on scene art** — editing `render_scenes.py` automatically invalidates
the frames, so just rebuild:

```bash
python3 projects/<slug>/render_scenes.py --sheet   # contact sheet, no encoding
python3 projects/<slug>/render_scenes.py 6 7       # redraw only scenes 6 and 7
python3 factory.py projects/<slug> --shorts
```

**Shipping a season**:

```bash
python3 factory.py --validate
python3 factory.py --all --shorts
python3 plan_season.py report
```

---

## `video.json` reference

The complete schema. Only `title` and `scenes` are strictly required, but
`--validate` will complain about anything that would produce a weak upload.

### Top level

| Key | Default | Meaning |
|---|---|---|
| `title` | — | YouTube title |
| `format` | `explainer` | `explainer` or `dialogue`. A two-hander is linted against 2–45 words a scene instead of 20–80, and QC stops flagging its short runtime and punchline pacing |
| `description` | — | Full description: hook, bullets, hashtags |
| `tags` | — | Comma-separated YouTube tags |
| `voice` | `en-US-AnaNeural` | Any Edge TTS voice |
| `rate` | `-8%` | Speaking speed. **Needs an explicit sign** (`+0%`, not `0%`) |
| `music` | `true` | Background bed on/off |
| `music_seed` | `7` | Melody seed. Different per episode, deterministic. Must be unique in a season |
| `bgm_vol` | `0.13` | Music level under the narration |
| `loudness` | `true` | Master to −14 LUFS |
| `short_captions` | `true` | Burn caption cards into the Short |
| `shorts_scenes` | — | 1-based scene numbers making up the Short. Must be distinct and in range |
| `thumbnail_text` | — | Exactly two lines. Line 2 becomes variant B's big word |
| `thumbnail_prop` | `rocket` | Hero object — see the list below |
| `thumbnail_bg` | `land` | Lower third: `land`, `sea`, `none` |
| `thumbnail_sky` | `day` | `day`, `sunset`, `night`, `plain` |
| `languages.<code>` | — | `{ voice, title, description, tags, thumbnail_text?, thumbnail_prop? }` |
| `scenes` | — | The array below |

**`thumbnail_prop` values:** `airfoil`, `cloud`, `kid`, `molecule`, `mountain`,
`paper_plane`, `plane`, `planet`, `prism`, `raindrop`, `rocket`, `salt_crystal`,
`sun`, `wave`. An unknown value is a **hard error**, not a silent fallback.

### Per scene

| Key | Meaning |
|---|---|
| `image` | Path to the frame, relative to the project (`frames/scene_01.png`) |
| `narration` | What the voice says. 20–80 words enforced; 35–55 is the sweet spot (2–45 when `format` is `dialogue`) |
| `voice` | Overrides the episode voice for this scene. How a two-hander gives each character its own voice instead of one narrator reading both parts |
| `rate` | Overrides the episode speaking rate for this scene |
| `chapter` | Chapter label. Emits a `M:SS Label` line into `metadata.txt` |
| `sfx` | `whoosh`, `pop`, `sparkle` or `success` |
| `narration_<code>` | Translated narration you supply — never machine-translated |

Pipeline-wide constants (fps, zoom rate, fades, CRF, mix levels, loudness
targets) live at the top of `factory.py`. Change them together, not one at a
time.

---

## Architecture

### The pipeline

```
video.json ──┐
             ├─► validate_config()      lint, advisory during a build
render_scenes.py                        (fatal only via --validate)
             │
             ├─► ensure_frames()        run render_scenes.py if any frame is
             │                          missing OR older than the art code
             │                          → frames/scene_NN.png   (1920×1080)
             │
             ├─► narrate()              Edge TTS, content-hashed cache
             │                          → audio/scene_NN.mp3 + .stamp
             │                          ── the only network step ──
             │
             ├─► ensure_sfx()           numpy oscillators
             │                          → audio/sfx_*.wav, sting.wav
             │
             ▼
        per-scene durations   = ffprobe(mp3) + SCENE_PAD, quantized to whole frames
             │
             ├─► build_clip() ×N        ThreadPoolExecutor(--jobs)
             │     zoompan (Ken Burns) + fade in/out
             │     amix: narration(+300 ms) + SFX + sting on scenes 1 and N
             │     → clips/<variant>/scene_NN.mp4
             │
             ├─► concat_clips()         demuxer, -c copy  ← why caching works
             │
             ├─► finalize()             mix music bed, measure over the graph,
             │     apply linear loudnorm → one AAC generation
             │     → output/final.mp4                     (−14 LUFS)
             │
             ├─► make_short()           concat picks → blurred-fill 9:16
             │     → burn_captions()    one PNG card per cue, overlay+enable
             │     → finalize()         → output/short.mp4
             │
             ├─► caption_cues()         → captions.srt, short_captions.srt
             ├─► thumbnail.render_pair()→ thumbnail_a.jpg, thumbnail_b.jpg
             │
             └─► qc → metadata → manifest        (in that order, deliberately)
```

The last line matters: QC runs **first** so `metadata.txt` and
`build_manifest.json` can both list `qc_report.txt`, and the manifest runs
**last** so it records every artifact the build produced.

### Module map

| Module | Responsibility | Rough size |
|---|---|---|
| `factory.py` | The only entry point. Orchestration, ffmpeg invocation, caching, captions, metadata, manifest, CLI | ~1340 lines |
| `engine/toolkit.py` | Cartoon primitive library — the channel's visual identity. Palette, fonts, characters, props, safe zones | ~1250 lines |
| `engine/music.py` | Procedural BGM (I–V–vi–IV, pentatonic melody), 4 SFX, the channel sting. Pure numpy | ~335 lines |
| `engine/captions.py` | Caption cards burned into Shorts. Word wrap, font fitting, RGBA rendering | ~155 lines |
| `engine/thumbnail.py` | A/B thumbnail compositions, the `PROPS` and `BACKDROPS` registries | ~155 lines |
| `engine/qc.py` | Post-build measurement and the `PASS`/`WARN` verdict. Measures only, never re-renders | ~260 lines |
| `new_episode.py` | Scaffolder — writes a buildable placeholder project | ~180 lines |
| `plan_season.py` | Season dashboard over `season.json` | ~180 lines |

### On-disk layout

```
factory.py  new_episode.py  plan_season.py  season.json
engine/           toolkit · music · captions · thumbnail · qc
fonts/            drop Poppins-Bold.ttf here (optional)
tests/            unit.py (fast) · smoke.py (full pipeline, offline)
projects/<slug>/
    video.json          script + config          ← committed
    render_scenes.py    scene art as code        ← committed
    frames/             scene_NN.png             ← generated, gitignored
    audio/              scene_NN.mp3 + .stamp    ← generated, cached, gitignored
                        sfx_*.wav, sting.wav, bgm_*.wav
    clips/
        final/          scene_NN.mp4             ← per-variant clip cache
        hi/             ...                        (language)
        preview-final/  ...                        (draft — cannot poison the real cache)
        _work/          concat lists, caption PNGs, intermediates
    output/             the deliverables
        <code>/         language variants
```

Only `video.json` and `render_scenes.py` are committed. Everything else is
reproducible from them, which is the whole point.

### Data flow invariants

- **Scene duration** is `ffprobe(narration.mp3) + SCENE_PAD`, **quantized to a
  whole frame**. Clips are encoded as exactly that many frames, so captions and
  chapters cannot drift against the video.
- **Narration starts at `NARRATION_OFFSET` (0.3 s)**, after the fade-in has
  opened. Caption cues use the same offset, so subtitles match speech.
- **Caption cues are the single source of truth** for `captions.srt`, the
  Short's re-timed `short_captions.srt`, and the burned-in cards. They cannot
  disagree because they come from one function.
- **Safe zones are proven, not promised.** The toolkit records a bbox for every
  text, character and badge drawn. An outro scene calls `safe_zone_violations()`
  and raises if anything intrudes on the end-card zone; `tests/unit.py`
  re-checks the last scene of every episode.

---

## Caching model

Builds are incremental at four independent levels. This is what makes the
"change one sentence, rebuild in seconds" loop work.

| Layer | Cache key | Invalidated by |
|---|---|---|
| Frames | file mtime vs `render_scenes.py` and `engine/toolkit.py` | editing the art code, `--force` |
| Narration | `sha256(voice \| rate \| text)` in `audio/scene_NN.mp3.stamp` | changing the text, voice or rate |
| Scene clips | mtime vs frame, mp3, SFX, sting | any of those changing, `--force` |
| Master / Short | mtime vs clips, music bed, `video.json` | any of those changing, `--force` |

Two consequences worth knowing:

- **Content-hashed narration** means a rerun with unchanged text never touches
  the network — which is also what lets CI run the whole pipeline offline.
- **Editing one toolkit primitive invalidates every episode's frames**, so the
  next `--all` is a full re-encode. That is the correct trade — a wrong frame
  ships, a slow build does not — but batch your toolkit edits.

Clip directories are keyed `final` / `<lang>` / `preview-<lang>` so a 640×360
draft can never be mistaken for a finished clip.

---

## Design decisions

**Per-scene encoding, then concat with `-c copy`.** Each scene becomes its own
clip and the clips are joined with the concat demuxer. That is what makes
caching possible: change scene 7's narration and only scene 7 re-encodes. One
mega-filtergraph would be marginally faster cold and dramatically slower on
every rebuild.

**Everything is generated, nothing is fetched.** If you ever add a downloaded
asset, the copyright-clean guarantee is gone.

**Supersampled drawing.** `toolkit.canvas()` renders at 2× and downsamples with
LANCZOS on save. That is where the clean edges come from.

**Mastering to −14 LUFS, in one encode.** YouTube attenuates loud uploads and
does nothing to quiet ones, so a quiet master stays quiet forever. `finalize()`
runs a two-pass `loudnorm` — measure, then apply one constant gain with
`linear=true`, because single-pass loudnorm is a dynamic compressor that pumps
the music bed up between sentences. The measurement runs over the *filtergraph*
rather than an intermediate file, so mixing and normalizing happen in a single
AAC generation instead of three.

**Captions on Shorts are drawn, not filtered.** Shorts are mostly watched muted,
so on-screen text is most of the message. The cards are rendered with Pillow and
composited with `overlay` + `enable=`, deliberately **not** with `subtitles=` or
`drawtext`: both are optional ffmpeg build features that many builds omit, and
drawing them ourselves keeps the channel's own font and rounded-banner look.

**QC is advisory, not a gate.** It writes `PASS`/`WARN` and exits 0 either way.
The owner decides; the report just makes the decision take two minutes.

**Machine translation is deliberately absent.** `--lang` builds a variant only
from translations the owner supplies. A mistranslated science explanation for
children is worse than no translation.

Longer rationale, and the gotchas that will bite you, live in
[HANDOFF.md](HANDOFF.md).

---

## Making a new episode

An episode is two files. There are two ways to get them.

### Option A — scaffold, then write

```bash
python3 new_episode.py why-is-the-ocean-salty --scenes 10
python3 factory.py projects/why-is-the-ocean-salty --preview   # buildable immediately
```

The scaffold writes a `video.json` with placeholder narration and a
`render_scenes.py` that draws placeholder frames, so the pipeline runs before a
single real word is written.

### Option B — ask an LLM, paste the result

Paste this, filling in the topic:

```
Write episode <N> of Wonder-o-nauts: "<your question, e.g. How do planes fly?>"

Give me exactly two files for projects/<slug>/:

1. video.json following the schema in projects/why-is-the-sky-blue/video.json
   - 10 scenes, 35-55 words of narration each (~4 minutes total)
   - spoken to a curious 6-year-old: short sentences, one idea per sentence,
     at most two "secrets" plus one bonus wonder near the end
   - name the common misconception and kill it explicitly
   - every scene gets a `chapter` label and an `sfx`
     (whoosh | pop | sparkle | success)
   - end with a question to the comments
   - fill title, description (hook + bullets + hashtags), tags,
     thumbnail_text (2 lines), thumbnail_prop, thumbnail_bg,
     shorts_scenes (3 distinct scenes that stand alone), music_seed

2. render_scenes.py drawing all 10 frames using ONLY engine/toolkit.py
   primitives (read engine/toolkit.py first). Rules:
   - keep every text element inside toolkit.SAFE
   - the final scene calls end_screen_guides() and must leave the
     bottom-right 40% clear
   - if you need a new shape, add it to engine/toolkit.py as a parameterized
     primitive -- never draw it inline in the episode
```

### Then

```bash
python3 factory.py projects/<slug> --validate    # must print OK
python3 projects/<slug>/render_scenes.py --sheet # eyeball the contact sheet
python3 factory.py projects/<slug> --shorts
```

### Editorial rules that hold up

Learned across episodes 1–5, kept in [BACKLOG.md](BACKLOG.md):

- 10 scenes at 35–55 words lands at 3.5–4.5 minutes. That is the sweet spot for
  ages 4–9.
- Two "secrets" per episode, maximum, plus one bonus wonder near the end — the
  bit viewers repeat to a grown-up.
- Name the misconception and kill it. Episode 2 says outright that planes do not
  fly because "the air on top has further to go".
- Draw the physics, not a picture of it. If a frame shows a tilted Earth in two
  orbital positions, the axis must point the same way in both.
- Always end with a question to the comments.

---

## Extending the toolkit

New shapes go in `engine/toolkit.py`, **never inline in an episode**. Episodes
compose primitives; that is why every episode looks like the same channel.

```python
def salt_crystal(d: ScaledDraw, x: int, y: int, size: float = 90, ...):
    """A grain of salt, drawn as the cube it actually is."""
```

Rules:

- Coordinates are logical 1920×1080; `ScaledDraw` handles the supersampling.
- Anything that takes an angle must be built from polygons, lines and circles —
  Pillow draws `rounded_rectangle` axis-aligned, so it cannot rotate.
- Keep text and characters inside `toolkit.SAFE` = `(120, 80, 1800, 1000)`. The
  Ken Burns zoom crops roughly 4% off each edge by the end of a scene.
- Call `register_box()` for anything that must respect a safe zone.
- Budget two or three new primitives per episode. More usually means the episode
  is fighting the visual identity instead of extending it.

Contributions by episode: ep 1 `sun`, `kid`, `rocket`, `molecule`, `zig_ray`,
`prism` · ep 2 `plane`, `paper_plane`, `airfoil`, `wind_streaks`, `force_arrow` ·
ep 3 `planet`, `orbit_ring`, `light_beam` · ep 4 `raindrop`, `rainfall`,
`puddle`, `cycle_arrow` · ep 5 `sea`, `wave`, `salt_crystal`, `mountain`,
`river` · Studio `hare`, `tortoise`, `dog`.

The last three exist because the pipeline is generic but the art library is not.
Any storyline renders — the format, the audio, the captions and the mastering
know nothing about science — but a story only *looks* like itself if its
characters exist as primitives. A fable needs a hare and a tortoise; two dogs
telling dad jokes need a dog that can face either way, open its muzzle for the
line it is delivering, and hold an expression (`happy`, `laugh`, `surprised`,
`deadpan`, `smug`). Adding a new cast member is the one real cost of a new kind
of story.

---

## Quality control

Two independent gates.

### `--validate` — before the build

Lints `video.json` in milliseconds: empty title/description/tags, leftover
`TODO` text, non-integer `music_seed`, a `rate` missing its sign, unknown
`thumbnail_prop`/`thumbnail_bg`/`thumbnail_sky`, `thumbnail_text` that isn't two
lines, empty/duplicated/out-of-range `shorts_scenes`, missing images with no
`render_scenes.py`, narration outside 20–80 words, unknown `sfx`, two scenes
sharing an image, fewer than 3 chapters, and language blocks missing a voice or
a translation. Exits non-zero if anything is wrong; it also runs advisorily at
the start of every build.

### `qc_report.txt` — after the build

Measures the actual output file:

| Check | Threshold |
|---|---|
| Narration pace | 110–175 wpm per scene (English only; reported but not enforced otherwise) |
| Runtime | 2–15 minutes |
| Streams | video and audio both present — a silent render is the defect humans miss |
| Integrated loudness | within 2 LU of −14 LUFS |
| True peak | at or below 0 dBTP |
| Mean / peak volume | above −30 dB / below −1 dB |
| Caption coverage | every scene has at least one cue |
| Thumbnails | both present, 1280×720, under YouTube's 2 MB limit |
| Chapters | 3 or more, or YouTube won't show a chapter list |

`plan_season.py report` rolls the verdicts and loudness up across the season, so
an un-normalized episode cannot hide behind a column of `PASS`.

---

## Uploading

`metadata.txt` carries the full checklist per episode. The short version:

- [ ] **Mark as "Made for Kids" = YES** (COPPA — required)
- [ ] Upload `thumbnail_a.jpg`, then A/B it against `thumbnail_b.jpg` with
      YouTube's built-in *Test & Compare*
- [ ] Paste the chapter timestamps from `metadata.txt` into the description
- [ ] Upload `captions.srt` as English subtitles — don't rely on auto-captions
- [ ] Category *Education*; hold questionable comments for review
- [ ] No external links in the description aimed at children
- [ ] Upload `short.mp4` separately with `#Shorts` in the title. Its captions are
      already burned in; `short_captions.srt` is the same text as a sidecar
- [ ] `qc_report.txt` says `PASS`

Upload is manual on purpose — the YouTube Data API needs OAuth credentials,
which would break the "no accounts, no keys" guarantee.

---

## Season workflow

```bash
python3 plan_season.py add how-do-magnets-work       # scaffold + register as draft
python3 plan_season.py set how-do-magnets-work ready
python3 plan_season.py status                        # the plan
python3 plan_season.py report                        # what is built: QC, runtime, loudness
python3 factory.py --all --shorts                    # builds only 'ready' episodes
python3 plan_season.py set how-do-magnets-work published
```

Statuses flow `draft → scripted → ready → published`. State lives in
`season.json`.

---

## Testing and CI

```bash
python3 tests/unit.py     # 181 checks, ~20 s, no encoding, no network
python3 tests/smoke.py    # full pipeline offline, ~7 min
```

`tests/unit.py` covers the logic that is easy to claim and hard to notice when
it breaks: Windows concat paths, SRT timestamp arithmetic, frame-boundary
alignment, clip-variant isolation, TTS cache keys, music determinism, QC verdict
logic, `video.json` linting, Short cue re-timing, caption card fitting and
placement, loudness filter construction, frame staleness, and the end-screen
safe zone of every episode's outro.

`tests/smoke.py` builds a whole episode for real — frames, music, clips, concat,
loudness, Short with burned-in captions, thumbnails, metadata, manifest, QC —
with **no network**. It fabricates narration audio plus the exact cache stamps
`factory.py` would have written, so TTS is never called. It builds in
`projects/_smoke/` so a test run can never touch a real project's cache.

CI (`.github/workflows/ci.yml`) runs preflight → lint every episode → unit tests
→ music sanity → scene art → caption cards → full smoke test → preview mode →
season dashboard → scaffolder, and uploads the QC report, metadata, captions,
manifest, thumbnails and a contact sheet as artifacts.

---

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `No module named 'numpy'` | You're on the system Python. `source .venv/bin/activate` |
| `edge-tts failed` | The only network step. Check connectivity; it retries 3× with backoff. Cached narration is unaffected |
| Narration sounds distant | An `amix` missing `normalize=0`. Every mix in `factory.py` passes it |
| Edited the art, nothing changed | Should be impossible since 3.1.0 — the build prints `frames: N stale`. If not, `--force` |
| Text shaved off the frame edge | Drawn outside `toolkit.SAFE`. The Ken Burns zoom crops ~4% per edge |
| QC warns `narration is slow` | Edge's Ana voice at `-8%` lands near 105 wpm. Set `"rate": "+0%"` in that episode |
| Tofu boxes instead of Devanagari | No Unicode-wide font. Drop `NotoSans-Bold.ttf` into `fonts/`; check `--check` output |
| Builds are slow | `zoompan` is single-threaded and usually the bottleneck. Raise `--jobs`. Don't scale to 4K "for quality" — it was ~5× slower with no visible gain |
| Ran out of disk | `python3 factory.py --all --clean` drops clips and music beds, keeps narration and outputs |
| Fonts look generic | Poppins Bold is the intended face. Drop `Poppins-Bold.ttf` into `fonts/` and the toolkit picks it up |

---

## Provenance and licensing

Every frame is drawn by `engine/toolkit.py` with Pillow. Every note and sound
effect is synthesized from oscillators and noise by `engine/music.py`. Scripts
are original. Narration comes from Microsoft Edge's free TTS voices via
`edge-tts`. Nothing is sampled, downloaded, traced or scraped, so there is no
third-party rights holder anywhere in an output file.

`build_manifest.json` records the factory version, music seeds, per-scene
narration SHA-256 hashes, the ffmpeg build and every artifact size — an audit
trail for exactly how a given file was produced.

Code is MIT. Media generated by the code belongs to the channel owner — see
[LICENSE](LICENSE).

---

## Roadmap

Deliberately not built, with reasons:

- **YouTube upload API** — needs OAuth credentials, which breaks "no accounts,
  no keys". Upload stays manual, guided by `metadata.txt`.
- **Machine translation** — a mistranslated science explanation for children is
  worse than no translation.
- **Word-level captions** — would need a forced aligner; sentence cues read
  better for this age band anyway.
- **Animated scenes** — the pipeline is stills plus Ken Burns. The primitives
  are already parameterized for animation (`rotate`, `wobble`, `phase`), so it
  is a natural next step if retention data ever asks for it.

Episode ideas live in [BACKLOG.md](BACKLOG.md). Maintenance notes, the gotchas
that will bite you, and the full audit trail live in [HANDOFF.md](HANDOFF.md).
