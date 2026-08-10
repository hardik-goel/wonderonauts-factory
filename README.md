# Wonder-o-nauts Video Factory

One command turns a project folder into a finished, YouTube-ready children's
science episode: 1080p video, captions, chapters, two thumbnails, a vertical
Short, metadata and a QC report.

Everything is generated. Visuals are drawn by Pillow, music and sound effects
are synthesized from math with numpy, scripts are original, narration comes
from free Edge TTS voices. Nothing is downloaded, sampled or traced. No API
keys, no accounts, no paid services.

---

## Quickstart

```bash
pip install -r requirements.txt          # pillow, numpy, edge-tts
brew install ffmpeg                      # or: sudo apt install ffmpeg
python3 factory.py --check               # preflight: deps, encoders, fonts
```

Then build a sample episode -- three ship with the repo:

```bash
python3 factory.py projects/why-is-the-sky-blue --shorts   # ep 1, light scattering
python3 factory.py projects/how-do-planes-fly  --shorts   # ep 2, lift and thrust
python3 factory.py projects/why-do-we-have-seasons --shorts  # ep 3, axial tilt
```

First run takes a few minutes (frames render, TTS downloads, ten clips encode).
Reruns are near-instant unless something actually changed.

---

## The one command

```bash
python3 factory.py projects/<episode>            # full 1080p build
python3 factory.py projects/<episode> --shorts   # + vertical 9:16 Short
python3 factory.py projects/<episode> --preview  # fast 640x360 draft (<1 min)
python3 factory.py projects/<episode> --lang hi  # language variant
python3 factory.py projects/<episode> --voice en-GB-SoniaNeural
python3 factory.py --all --shorts                # every episode marked 'ready'
python3 factory.py --check                       # preflight
python3 factory.py --season                      # season status table
```

Useful extras: `--force` (ignore caches), `--jobs N` (parallel scene encodes).

### What lands in `projects/<episode>/output/`

| File | What it is |
|---|---|
| `final.mp4` | 1080p H.264 + AAC, Ken Burns motion, music, SFX, sting |
| `short.mp4` | 1080x1920 Short, built from `shorts_scenes` (with `--shorts`) |
| `captions.srt` | Sentence-level subtitles, timed from the measured narration |
| `thumbnail_a.jpg` | Variant A — text dominant |
| `thumbnail_b.jpg` | Variant B — character dominant |
| `metadata.txt` | Title, description, tags, chapter timestamps, upload checklist |
| `qc_report.txt` | PASS/WARN verdict, per-scene pacing, loudness, coverage |
| `build_manifest.json` | Version, seeds, narration hashes, ffmpeg build, file sizes |
| `preview.mp4` | Draft only (`--preview`); never overwrites `final.mp4` |

---

## The two-touchpoint workflow

Per episode the owner does exactly two things: **run one command**, then
**review the output**. Everything between is automated.

1. **Ask Claude for an episode.** Give it a topic and this repo's
   `engine/toolkit.py` plus an existing project as reference. Ask for:
   `video.json` (script, chapters, SFX, tags, thumbnail text) and
   `render_scenes.py` (scene art built from toolkit primitives only).
2. **Drop the two files** into `projects/<slug>/`.
3. **Run** `python3 factory.py projects/<slug> --shorts`.
4. **Review** `output/qc_report.txt` — it should say `PASS`. Skim the contact
   sheet (`python3 projects/<slug>/render_scenes.py --sheet`), watch the video,
   upload using `output/metadata.txt` as the checklist.

### The prompt to give Claude

Paste this, filling in the topic. It is the whole of touchpoint one.

```
Write episode <N> of Wonder-o-nauts: "<your question, e.g. How do planes fly?>"

Give me exactly two files for projects/<slug>/:

1. video.json following the schema in projects/why-is-the-sky-blue/video.json
   - 10 scenes, 35-55 words of narration each (~4 minutes total)
   - spoken to a curious 6-year-old: short sentences, one idea per sentence,
     at most two "secrets" plus one bonus wonder near the end
   - every scene gets a `chapter` label and an `sfx`
     (whoosh | pop | sparkle | success)
   - end with a question to the comments
   - fill title, description (hook + bullets + hashtags), tags,
     thumbnail_text (2 lines), shorts_scenes, music_seed

2. render_scenes.py drawing all 10 frames using ONLY engine/toolkit.py
   primitives (read engine/toolkit.py first). Rules:
   - keep every text element inside toolkit.SAFE
   - the final scene calls end_screen_guides() and must leave the
     bottom-right 40% clear
   - if you need a new shape, add it to engine/toolkit.py as a parameterized
     primitive -- never draw it inline in the episode
```

Then drop the two files in and run the one command. Scaffold a folder first if
you prefer placeholders to a blank page:

```bash
python3 new_episode.py how-do-planes-fly
python3 factory.py projects/how-do-planes-fly --preview   # pacing check
```

---

## Tweaks

Everything below lives in the episode's `video.json`.

| Key | Default | What it changes |
|---|---|---|
| `voice` | `en-US-AnaNeural` | Any Edge TTS voice (`edge-tts --list-voices`) |
| `rate` | `+0%` (factory default `-8%`) | Speaking speed. QC wants 110–175 wpm |
| `music` | `true` | Set `false` for no background bed |
| `music_seed` | `7` | Different melody per episode, still deterministic |
| `bgm_vol` | `0.13` | Music level under the narration |
| `sfx` (per scene) | `whoosh` | `whoosh` · `pop` · `sparkle` · `success` |
| `chapter` (per scene) | — | Emits a `M:SS Label` line into `metadata.txt` |
| `shorts_scenes` | — | 1-based scene numbers that make up the Short |
| `thumbnail_text` | — | Two lines; line 2 becomes variant B's big word |
| `thumbnail_prop` | `rocket` | Thumbnail hero: `rocket` · `plane` · `paper_plane` · `sun` · `molecule` |
| `languages.<code>` | — | Voice + translated title/description for `--lang` |
| `narration_<code>` per scene | — | Translated narration you supply — never machine-translated |

Pipeline-wide constants (fps, zoom rate, fades, CRF, mix levels) live at the top
of `factory.py`. Change them together, not one at a time.

---

## Season workflow

```bash
python3 plan_season.py add how-do-planes-fly     # scaffold + register as draft
python3 plan_season.py set how-do-planes-fly ready
python3 plan_season.py status                    # the dashboard
python3 factory.py --all --shorts                # builds only 'ready' episodes
python3 plan_season.py set how-do-planes-fly published
```

Statuses: `draft → scripted → ready → published`.

---

## Upload checklist

`output/metadata.txt` carries this per episode; the short version:

- [ ] **Mark as "Made for Kids" = YES** (COPPA — required)
- [ ] Upload `thumbnail_a.jpg`, then A/B it against `thumbnail_b.jpg` with
      YouTube's built-in *Test & Compare*
- [ ] Paste the chapter timestamps from `metadata.txt` into the description
- [ ] Upload `captions.srt` as English subtitles (don't rely on auto-captions)
- [ ] Category *Education*, hold questionable comments for review
- [ ] No external links in the description aimed at children
- [ ] `qc_report.txt` says `PASS`

---

## Repo map

```
factory.py          the one command (build, preview, shorts, lang, all, check)
new_episode.py      scaffolder
plan_season.py      season dashboard (season.json)
engine/toolkit.py   cartoon component library -- the channel's visual identity
engine/music.py     procedural BGM, 4 SFX, the channel sting
engine/thumbnail.py A/B thumbnail compositions
engine/qc.py        post-build QC report
projects/<slug>/    video.json + render_scenes.py + frames/
season.json         the production dashboard's state
fonts/              drop Poppins-Bold.ttf here (see fonts/README.md)
tests/unit.py       fast logic tests (paths, timing, music, QC, safe zones)
tests/smoke.py      full offline pipeline test (no network TTS)
```

Run the tests with `python3 tests/unit.py` (seconds) and `python3 tests/smoke.py`
(a few minutes, builds a full episode offline in `projects/_smoke/`). CI runs both.

Maintenance notes, gotchas and the roadmap live in [HANDOFF.md](HANDOFF.md).
Episode ideas live in [BACKLOG.md](BACKLOG.md).

Code is MIT. Media generated by the code belongs to the channel owner — see
[LICENSE](LICENSE).
