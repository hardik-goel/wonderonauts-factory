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
`light_beam`. Each reused everything else unchanged. Budget
one or two new primitives per episode -- more than that usually means the
episode is fighting the identity instead of extending it.

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
12. **Fonts**: Poppins Bold is the intended face. Drop `Poppins-Bold.ttf` into
   `fonts/` and the toolkit picks it up automatically; otherwise it falls back to
   DejaVu (Linux/CI), Arial Rounded Bold (macOS) or Pillow's default. Devanagari
   and other non-Latin scripts fall back to a Unicode-wide face — check
   `factory.py --check` output before shipping a language variant.

---

## Where things live

| Concern | File |
|---|---|
| Pipeline constants (fps, zoom, fades, CRF, mix levels) | top of `factory.py` |
| Ken Burns / fades / SFX mix | `factory.py: build_clip()` |
| Music bed, SFX, sting | `engine/music.py` |
| Scene art primitives | `engine/toolkit.py` |
| Thumbnail compositions | `engine/thumbnail.py` |
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
  aligner; sentence cues read better for young viewers anyway.
- **Animated scenes** — the pipeline is stills + Ken Burns. Real animation would
  mean rendering frame sequences from the toolkit; the primitives are already
  parameterized for it (`rotate`, `wobble`, `phase`), so it is a natural next
  step if retention data ever asks for it.
- **Loudness normalization (EBU R128)** — QC measures loudness but does not fix
  it. If Edge ever ships a quieter voice, add `loudnorm` in `build_clip()`
  rather than turning up `SFX_VOL`.

---

## Release checklist for the repo itself

```bash
python3 factory.py --check                 # deps + encoders + fonts
python3 tests/unit.py                      # fast logic tests (seconds)
python3 tests/smoke.py                     # full offline pipeline
python3 -m engine.music --demo /tmp/audio  # peaks should read ~0.72
python3 projects/why-is-the-sky-blue/render_scenes.py --sheet
```

Bump `VERSION` in `factory.py` when the pipeline changes shape — it is recorded
in every `build_manifest.json`, which is how you diff "what changed since the
last build".
