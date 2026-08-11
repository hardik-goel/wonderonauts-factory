# Wonder-o-nauts Video Factory

One command turns a project folder into a finished, YouTube-ready children's
science episode: 1080p video, captions, chapters, two thumbnails, a vertical
Short with burned-in captions, broadcast-level loudness, metadata and a QC
report.

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

Then build a sample episode -- five ship with the repo:

```bash
python3 factory.py projects/why-is-the-sky-blue --shorts   # ep 1, light scattering
python3 factory.py projects/how-do-planes-fly  --shorts   # ep 2, lift and thrust
python3 factory.py projects/why-do-we-have-seasons --shorts  # ep 3, axial tilt
python3 factory.py projects/where-does-rain-come-from --shorts  # ep 4, water cycle
python3 factory.py projects/why-is-the-ocean-salty --shorts  # ep 5, weathering
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
python3 factory.py projects/<episode> --validate # lint video.json, no build
python3 factory.py projects/<episode> --clean    # drop rebuildable caches
```

Useful extras: `--force` (ignore caches), `--jobs N` (parallel scene encodes),
`--no-loudnorm`, `--no-short-captions`. `--validate` with no project lints every
episode in `season.json`; `--clean` needs either a project path or an explicit
`--all`, because wiping the season's clip cache costs half an hour to rebuild.

### What lands in `projects/<episode>/output/`

| File | What it is |
|---|---|
| `final.mp4` | 1080p H.264 + AAC, Ken Burns motion, music, SFX, sting, −14 LUFS |
| `short.mp4` | 1080x1920 Short with burned-in captions (with `--shorts`) |
| `captions.srt` | Sentence-level subtitles, timed from the measured narration |
| `short_captions.srt` | The same cues re-timed onto the Short's own timeline |
| `thumbnail_a.jpg` | Variant A — text dominant |
| `thumbnail_b.jpg` | Variant B — character dominant |
| `metadata.txt` | Title, description, tags, chapter timestamps, upload checklist |
| `qc_report.txt` | PASS/WARN verdict, per-scene pacing, loudness, LUFS, coverage |
| `build_manifest.json` | Version, seeds, narration hashes, ffmpeg build, file sizes |
| `preview.mp4` | Draft only (`--preview`); never overwrites `final.mp4` |

### Loudness and Shorts captions

Two things every uploaded episode needs, and neither is optional in practice:

- **−14 LUFS.** YouTube only ever turns *loud* uploads down, so a quiet master
  stays quiet for every viewer forever. Each build measures its own mix and
  applies one constant gain (two-pass `loudnorm`, `linear=true`) so the music
  bed does not pump between sentences. QC re-measures and flags any drift.
- **Burned-in captions on the Short.** Shorts are mostly watched muted. The
  cards are drawn with Pillow in the channel's own font and overlaid with
  `overlay`, so this works on ffmpeg builds without libass or libfreetype.

Turn either off per build with `--no-loudnorm` / `--no-short-captions`, or per
episode with `"loudness": false` / `"short_captions": false` in `video.json`.

---

## The two-touchpoint workflow

Per episode the owner does exactly two things: **run one command**, then
**review the output**. Everything between is automated.

1. **Ask Claude for an episode.** Give it a topic and this repo's
   `engine/toolkit.py` plus an existing project as reference. Ask for:
   `video.json` (script, chapters, SFX, tags, thumbnail text) and
   `render_scenes.py` (scene art built from toolkit primitives only).
2. **Drop the two files** into `projects/<slug>/`.
3. **Run** `python3 factory.py projects/<slug> --validate` (a second) then
   `python3 factory.py projects/<slug> --shorts`.
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
     thumbnail_text (2 lines), thumbnail_prop, thumbnail_bg,
     shorts_scenes (3 distinct scenes that stand alone), music_seed
   - `python3 factory.py projects/<slug> --validate` must print OK

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
| `short_captions` | `true` | Burn caption cards into the Short |
| `loudness` | `true` | Normalize the master to −14 LUFS |
| `thumbnail_text` | — | Two lines; line 2 becomes variant B's big word |
| `thumbnail_prop` | `rocket` | Thumbnail hero — see `engine/thumbnail.py: PROPS` for the full list (`rocket`, `plane`, `paper_plane`, `sun`, `molecule`, `planet`, `raindrop`, `prism`, `cloud`, `airfoil`, `kid`, `salt_crystal`, `wave`, `mountain`) |
| `thumbnail_bg` | `land` | Lower third of the thumbnail: `land` · `sea` · `none` |
| `thumbnail_sky` | `day` | `day` · `sunset` · `night` · `plain` |
| `languages.<code>` | — | Voice + translated title/description/thumbnail for `--lang` |
| `narration_<code>` per scene | — | Translated narration you supply — never machine-translated |

An unknown `thumbnail_prop` is now a hard error rather than a silent fallback to
the rocket. `python3 factory.py projects/<slug> --validate` catches that and a
dozen other mistakes before you spend a build discovering them.

Pipeline-wide constants (fps, zoom rate, fades, CRF, mix levels) live at the top
of `factory.py`. Change them together, not one at a time.

---

## Season workflow

```bash
python3 plan_season.py add how-do-planes-fly     # scaffold + register as draft
python3 plan_season.py set how-do-planes-fly ready
python3 plan_season.py status                    # the plan
python3 plan_season.py report                    # what is built: QC, runtime, files
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
factory.py          the one command (build, preview, shorts, lang, all, check,
                    validate, clean)
new_episode.py      scaffolder
plan_season.py      season dashboard (season.json)
engine/toolkit.py   cartoon component library -- the channel's visual identity
engine/music.py     procedural BGM, 4 SFX, the channel sting
engine/captions.py  caption cards burned into the Short
engine/thumbnail.py A/B thumbnail compositions + the PROPS registry
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
