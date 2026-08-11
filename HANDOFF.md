# HANDOFF

Maintenance notes for the Wonder-o-nauts video factory: what was decided and
why, what will bite you, and what is worth building next.

---

## Design decisions (and the reasons behind them)

**Per-scene encoding, then concat with `-c copy`.**
Each scene is encoded to its own clip and the clips are joined with the concat
demuxer. That is what makes caching possible: change scene 7's narration and
only scene 7 re-encodes. A single mega-filtergraph would be marginally faster on
a cold build and dramatically slower on every rebuild. Do not "optimize" this.

**Everything is generated, nothing is fetched.**
Frames come from `engine/toolkit.py` (Pillow), music and SFX from
`engine/music.py` (numpy oscillators + noise), narration from Edge TTS. There is
no asset directory to license, attribute or lose. If you ever add a downloaded
asset, the copyright-clean guarantee is gone.

**The toolkit is the channel's visual identity.**
New shapes go into `engine/toolkit.py`, never inline in an episode's
`render_scenes.py`. Episodes compose primitives; that is why every episode looks
like the same channel. Episode 1 contributed `sun`, `kid`, `rocket`, `molecule`,
`zig_ray` and `prism`; episode 2 added `plane`, `paper_plane`, `airfoil`,
`wind_streaks` and `force_arrow`; episode 3 added `planet`, `orbit_ring` and
`light_beam`; episode 4 added `raindrop`, `rainfall`, `puddle` and
`cycle_arrow`; episode 5 added `sea`, `wave`, `salt_crystal`, `mountain` and
`river`. Each reused everything else unchanged. Budget
one or two new primitives per episode -- more than that usually means the
episode is fighting the identity instead of extending it. (Episode 5 needed
five, which is over budget and worth noticing: an ocean episode simply had no
water primitives to inherit. The next water episode should add none.)

**Every master leaves at -14 LUFS.** YouTube attenuates loud uploads and does
nothing at all to quiet ones, so a quiet master is quiet forever. `finalize()`
runs a *two-pass* `loudnorm`: measure, then apply one constant gain with
`linear=true`. Single-pass loudnorm is a dynamic compressor and audibly pumps
the bed up in the gaps between sentences. QC re-measures with `ebur128` and
flags drift, so a build that silently skipped the pass cannot ship looking fine.

The measurement pass runs over the *filtergraph*, not over an intermediate file
(`loudnorm_measure(inputs, graph)`). That is deliberate: mixing to disk, then
measuring, then normalizing would put three generations of AAC on the shipped
audio. Measuring the graph means the music mix and the normalization happen in
one encode. If you ever add a stage here, keep it inside `mix_filter()` so it
stays that way.

**Shorts carry burned-in captions.** They are watched muted. `engine/captions.py`
renders one RGBA card per cue with Pillow and `burn_captions()` composites them
with `overlay` + `enable=`. It deliberately does not use `subtitles=` or
`drawtext`: both are optional ffmpeg build features (libass / libfreetype) and
the Homebrew build this was developed against has neither. Drawing the cards
ourselves also keeps the channel's font and rounded-banner look.

**Supersampled drawing.** `toolkit.canvas()` renders at 2x and `toolkit.save()`
downsamples with LANCZOS. That is where the clean edges come from. `ScaledDraw`
multiplies logical 1920x1080 coordinates into that space, so primitives never
think about pixels — but it also means every new `ImageDraw` method you want to
use must be forwarded through `ScaledDraw` first.

**Narration cache is keyed by content, not by timestamp.**
`audio/scene_NN.mp3.stamp` holds `sha256(voice|rate|text)`. Rerunning with
unchanged text never touches the network — which is also what lets CI run the
whole pipeline offline.

**Preview artifacts are named differently on purpose.**
`preview.mp4` / `preview_captions.srt` can never be confused with `final.mp4`,
and preview clips live in `clips/preview/` so they cannot poison the real cache.

**Safe zones are proven, not promised.** `toolkit` records a bbox for every
piece of text, character and badge drawn on the current canvas, so a scene can
assert it complies: episode 1's outro calls `safe_zone_violations()` on the
end-card zone and raises if anything intrudes. `tests/unit.py` re-checks the
last scene of every project. Backgrounds never register.

**QC is advisory, not a gate.** It writes `PASS`/`WARN` and exits 0 either way.
The owner decides; the report just makes the decision take two minutes.

---

## Gotchas (learned the hard way — leave these alone)

1. **`amix` without `normalize=0` silently halves the narration.** Every mix in
   `factory.py` passes `normalize=0`. If narration ever sounds distant, this is
   the first thing to check.
2. **`zoompan` needs a pre-computed frame count.** `d=` is `round(duration*FPS)`
   and the per-frame zoom step is `ZOOM_PER_SEC / FPS`. Changing `FPS` means
   changing both, in lockstep, or the Ken Burns move drifts.
3. **`zoompan` is single-threaded**, so it — not x264 — is usually the slowest
   part of a build. The source is pre-scaled to exactly `1920 * ZOOM_MAX` wide:
   enough headroom to kill pan jitter, not a pixel more. Scaling to 4K "for
   quality" made builds ~5x slower with no visible gain. Scene encodes run in
   parallel (`--jobs`, default 4) which is where the real wall-clock win is.
4. **Concat lists need absolute, forward-slashed, quoted paths.**
   `concat_list()` writes `file '<abs path>'`, converts `\` to `/` (Windows
   drive letters work fine that way) and escapes embedded quotes.
5. **edge-tts is the only network step.** It retries three times with backoff and
   writes to a `.part` file first, so an interrupted run can never leave a
   truncated mp3 that later looks cached.
6. **Stroked text is the whole kid-video look.** `toolkit.title_text()` uses
   Pillow's `stroke_width`; anchoring is computed manually from the text bbox so
   it also works when Pillow falls back to its built-in font.
7. **`rate` interacts with the QC wpm window.** Edge's Ana voice at `-8%` lands
   around 103–110 wpm, which trips the `<110 wpm` flag. Episode 1 therefore sets
   `"rate": "+0%"` in its `video.json` (~112–125 wpm). The factory-wide default
   stays `-8%` for voices that run faster.
8. **edge-tts rate strings need an explicit sign**: `"+0%"`, not `"0%"`.
9. **The Ken Burns move eats the edges.** By the end of a ~20s scene the zoom
   has cropped roughly 4% off each side. Anything drawn outside `toolkit.SAFE`
   (120, 80) - (1800, 1000) will be shaved off on screen. Episode 1 was caught
   by exactly this: two headlines and two caption banners had to move inward.
10. **Caption splitting is lookahead-based, not "split on every dot".**
    `factory.split_sentences()` only breaks at `. ! ? … ।` when the next word
    does not start lowercase, so "Why is the sky... blue?" stays one caption.
    The Devanagari danda counts as a terminator, which is what makes Hindi
    captions break at sentences instead of once per scene.
11. **Rotatable primitives cannot use `rounded_rectangle`.** Pillow draws it
    axis-aligned, so `plane(pitch=...)` tilted every part except the fuselage
    until it was rebuilt as a rotated polygon plus two end caps. Any primitive
    that takes an angle must be built from polygons, lines and circles only.
12. **The art is code, so frames expire.** `ensure_frames()` re-renders when a
    frame is missing *or* older than `render_scenes.py` or `engine/toolkit.py`.
    The original version only checked for missing files, which meant you could
    redraw a scene, rebuild, and silently get the old picture back. Be aware of
    the cost: editing one toolkit primitive invalidates every episode's frames,
    so the next `--all` is a full re-encode. That is the right trade -- a wrong
    frame ships, a slow build does not -- but do the toolkit edits together.
13. **`loudnorm` resamples to 192 kHz internally.** Always follow it with
    `aresample=44100` or the AAC encoder inherits the wrong rate.
14. **A caption card is anchored by its top, not its bottom.** Anchoring by the
    bottom made a two-line cue grow upward over the video's own caption banner.
    `short_caption_y()` derives the position from the letterbox geometry and
    pulls tall cards up out of the Shorts UI strip.
15. **Fonts**: Poppins Bold is the intended face. Drop `Poppins-Bold.ttf` into
   `fonts/` and the toolkit picks it up automatically; otherwise it falls back to
   DejaVu (Linux/CI), Arial Rounded Bold (macOS) or Pillow's default. Devanagari
   and other non-Latin scripts fall back to a Unicode-wide face — check
   `factory.py --check` output before shipping a language variant.

---

## Where things live

| Concern | File |
|---|---|
| Pipeline constants (fps, zoom, fades, CRF, mix levels, LUFS) | top of `factory.py` |
| Ken Burns / fades / SFX mix | `factory.py: build_clip()` |
| Music mix + loudness | `factory.py: finalize()` / `loudnorm_apply()` |
| Short reframing + caption burn-in | `factory.py: make_short()` / `burn_captions()` |
| video.json linting (`--validate`) | `factory.py: validate_config()` |
| Music bed, SFX, sting | `engine/music.py` |
| Scene art primitives | `engine/toolkit.py` |
| Caption card rendering | `engine/captions.py` |
| Thumbnail compositions + `PROPS` | `engine/thumbnail.py` |
| QC thresholds | top of `engine/qc.py` |
| Fast logic tests | `tests/unit.py` (seconds, no ffmpeg encoding) |
| Offline end-to-end test | `tests/smoke.py` (also run by CI) |

`tests/smoke.py` copies the episode to `projects/_smoke/` and builds there, so a
test run can never overwrite the real project's narration cache or output.
Folders whose name starts with `_` are ignored by `--check` and `--all`.

---

## Roadmap / not built on purpose

- **YouTube upload API** — out of scope: it needs OAuth credentials, which
  breaks the "no accounts, no keys" rule. Upload stays manual, guided by
  `metadata.txt`.
- **Machine translation** — deliberately absent. `--lang` builds a variant only
  from translations the owner puts in `video.json`; a mistranslated science
  explanation for children is worse than no translation.
- **Word-level captions** — current SRT is sentence-level, timed by character
  share of the measured narration. Word-level timing would need a forced
  aligner; sentence cues read better for young viewers anyway. The Short's
  burned-in cards use the same sentence cues.
- **Animated scenes** — the pipeline is stills + Ken Burns. Real animation would
  mean rendering frame sequences from the toolkit; the primitives are already
  parameterized for it (`rotate`, `wobble`, `phase`), so it is a natural next
  step if retention data ever asks for it.
- **Loudness normalization (EBU R128)** — *built* in 3.1.0. `finalize()` runs a
  two-pass `loudnorm` to -14 LUFS and QC re-measures with `ebur128`. It lives at
  the final mix, not in `build_clip()`: normalizing per scene would flatten the
  deliberate dynamic between a quiet explanation and a loud "BOING!".

---

## Audit trail: bugs found and fixed after the first build

Each of these is now covered by a regression test in `tests/unit.py` or
`tests/smoke.py`, because every one of them was invisible in the output until
someone went looking.

1. **`--preview --lang xx` poisoned the real language cache.** Preview clips
   landed in `clips/<lang>/`, so the next full build saw them as up to date and
   would have shipped a 640x360 draft. Clip directories are now keyed
   `final` / `<lang>` / `preview-<lang>`.
2. **SRT emitted 4-digit milliseconds.** A fraction of .9996 rounded to 1000 and
   produced `00:00:01,1000`, which some players reject. Timestamps now round to
   whole milliseconds before splitting into fields.
3. **Captions drifted from the video.** Scene durations were raw floats while
   clips are encoded as a whole number of frames, so captions and chapters
   slipped a few milliseconds per scene. Durations are now quantized to frame
   boundaries before anything else uses them.
4. **`build_manifest.json` recorded `"project": "output"` for `--lang` builds.**
   The slug was being derived from the output path. It is passed in explicitly
   now.
5. **The manifest and metadata never listed `qc_report.txt`**, because QC ran
   after both were written. Order is now QC -> metadata -> manifest.

## Audit trail: second pass (3.1.0)

1. **Editing the art changed nothing.** `ensure_frames()` only re-rendered
   *missing* frames, so redrawing a scene and rebuilding silently reused the old
   PNG. It now also re-renders when `render_scenes.py` or `engine/toolkit.py` is
   newer than a frame, and on `--force`. Covered by `test_frame_staleness`.
2. **An unknown `thumbnail_prop` shipped a rocket.** `engine/thumbnail._prop()`
   ended in `else: rocket`, so a typo -- or a prop the toolkit had grown but the
   thumbnail module had not -- produced a plausible-looking wrong thumbnail.
   Props now live in a `PROPS` registry, an unknown value is a hard error, and
   `test_loudness_and_props` draws every registered prop.
3. **Episodes shipped at about -24 dB.** Loud enough to pass the old QC floor,
   quiet enough that every viewer reaches for the volume. Two-pass `loudnorm` to
   -14 LUFS now runs on `final.mp4` and `short.mp4`.
4. **Shorts had no on-screen text at all**, which is most of the message on a
   platform watched muted. Cards are rendered by `engine/captions.py` and burned
   in with `overlay`.
5. **`season_table()` never printed "empty".** `"  " + "".join(...) or "  empty"`
   parses as `("  " + join) or "  empty"`, and a two-space string is truthy.
6. **The scaffolder produced a Short that played one scene twice.**
   `[2, min(6, n), min(8, n)]` collapses to `[2, 3, 3]` for a 3-scene episode --
   which is exactly what CI scaffolds. It now dedupes.
7. **A scene shorter than two fades flickered.** `fade=t=out` started before
   `fade=t=in` finished; the fade length is now clamped to `duration / 2.2`.
8. **`--lang` builds reused the English thumbnail text.** A language block can
   now carry its own `thumbnail_text` / `thumbnail_prop`.
9. **`--jobs 0` or a negative value** reached `ThreadPoolExecutor` unchecked.
   Clamped to at least 1.
10. **A two-line burned caption overlapped the video's own banner**, because the
    card was anchored by its bottom edge. Caught by a unit test that asserted
    the letterbox geometry, not by watching the file.

## Release checklist for the repo itself

```bash
python3 factory.py --check                 # deps + encoders + fonts + filters
python3 factory.py --validate              # every episode's video.json lints
python3 tests/unit.py                      # fast logic tests (seconds)
python3 tests/smoke.py                     # full offline pipeline
python3 -m engine.music --demo /tmp/audio  # peaks should read ~0.72
python3 -m engine.captions "A test caption" # burned-in caption card
python3 projects/why-is-the-sky-blue/render_scenes.py --sheet
```

Bump `VERSION` in `factory.py` when the pipeline changes shape — it is recorded
in every `build_manifest.json`, which is how you diff "what changed since the
last build".
