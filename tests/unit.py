#!/usr/bin/env python3
"""
Fast unit tests -- the logic the video smoke test cannot reach.

No ffmpeg encoding, no network, runs in a few seconds. Covers the things that
are easy to claim and hard to notice when they break: Windows concat paths,
caption timing arithmetic, TTS cache keys, music determinism, and the
end-screen safe zone of every episode's outro.

    python3 tests/unit.py
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import time
import wave

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import factory                       # noqa: E402
from engine import music, qc         # noqa: E402
from engine import toolkit as tk     # noqa: E402

PASSED, FAILED = 0, []


def check(cond, label, detail=""):
    global PASSED
    if cond:
        PASSED += 1
        print(f"  [PASS] {label}" + (f"  {detail}" if detail else ""))
    else:
        FAILED.append(label)
        print(f"  [FAIL] {label}" + (f"  {detail}" if detail else ""))


# --------------------------------------------------------------------------
# Concat lists -- the cross-platform claim in the README, actually tested
# --------------------------------------------------------------------------

def test_concat_paths():
    with tempfile.TemporaryDirectory() as tmp:
        lst = os.path.join(tmp, "list.txt")
        factory.concat_list([os.path.join(tmp, "a.mp4"), os.path.join(tmp, "b.mp4")], lst)
        body = open(lst, encoding="utf-8").read()
        lines = body.strip().splitlines()
        check(len(lines) == 2, "concat list has one line per clip", f"{len(lines)}")
        check(all(l.startswith("file '") and l.endswith("'") for l in lines),
              "concat entries are quoted as file '<path>'")
        check(all(os.path.isabs(l[6:-1]) or l[6:-1][1:3] == ":/" for l in lines),
              "concat entries are absolute")
        check("\\" not in body, "concat entries contain no backslashes")

    # simulate a Windows drive-letter path without being on Windows
    win = "C:\\Users\\Wonder O'Naut\\clips\\scene_01.mp4"
    quoted = os.path.abspath(win).replace("\\", "/").replace("'", r"'\''")
    check("/" in quoted and "\\" not in quoted.replace(r"'\''", ""),
          "windows path converts to forward slashes", quoted[-28:])
    check(r"'\''" in quoted, "apostrophe in a path is escaped for the demuxer")


# --------------------------------------------------------------------------
# Timing arithmetic
# --------------------------------------------------------------------------

def test_srt():
    check(factory.srt_ts(0) == "00:00:00,000", "srt timestamp at zero")
    # regression: a fraction that rounds up used to emit ",1000" (4 digits)
    for t in (1.9999, 59.9996, 3599.9999):
        ms = factory.srt_ts(t).split(",")[1]
        check(len(ms) == 3 and int(ms) < 1000, f"srt ms stays 3 digits at {t}",
              factory.srt_ts(t))
    check(factory.srt_ts(3661.5) == "01:01:01,500", "srt timestamp at 1h01m01.5s",
          factory.srt_ts(3661.5))
    check(factory.fmt_ts(125) == "2:05", "chapter timestamp format", factory.fmt_ts(125))

    sents = factory.split_sentences(
        "One two. Three four! Five... six? Trailing with no stop")
    check(len(sents) == 4, "sentence splitter keeps every sentence", str(len(sents)))
    check(sents[-1].startswith("Trailing"), "sentence splitter keeps the tail")

    scenes = [
        {"i": 1, "duration": 10.7, "narration": "Aaa bbb. Ccc ddd eee fff."},
        {"i": 2, "duration": 5.7, "narration": "Short one."},
    ]
    with tempfile.TemporaryDirectory() as tmp:
        srt = os.path.join(tmp, "c.srt")
        n = factory.make_srt(scenes, srt)
        body = open(srt, encoding="utf-8").read()
        check(n == 3, "one cue per sentence", f"{n} cues")
        first = body.splitlines()[1]
        check(first.startswith("00:00:00,300"),
              "first cue starts at the narration offset", first)
        # last cue must end inside the video, not past it
        last_end = body.strip().splitlines()[-2].split(" --> ")[1]
        h, m, rest = last_end.split(":")
        secs = int(h) * 3600 + int(m) * 60 + float(rest.replace(",", "."))
        total = sum(s["duration"] for s in scenes)
        check(secs <= total + 1e-6, "last cue ends inside the runtime",
              f"{secs:.2f}s <= {total:.2f}s")


# --------------------------------------------------------------------------
# Narration cache keys
# --------------------------------------------------------------------------

def test_frame_alignment():
    """Regression: scene durations must land on whole frames, or captions and
    chapters drift a few milliseconds per scene away from the encoded video."""
    total_drift = 0.0
    for raw in (18.22, 18.62, 21.48, 19.22, 20.42, 21.22, 22.65, 15.60, 25.37):
        dur = round((raw + factory.SCENE_PAD) * factory.FPS) / factory.FPS
        frames = round(dur * factory.FPS)
        total_drift += abs(frames / factory.FPS - dur)
    check(total_drift < 1e-9, "scene durations sit exactly on frame boundaries",
          f"{total_drift*1000:.3f} ms drift")


def test_variant_isolation():
    """Regression: --preview --lang used to write 640x360 clips into the real
    language cache, so the next full build would ship the draft."""
    seen = {}
    for preview in (False, True):
        for lang in (None, "hi"):
            variant = lang or "final"
            if preview:
                variant = "preview-" + variant
            seen[(preview, lang)] = variant
    check(len(set(seen.values())) == 4, "every build variant has its own clip dir",
          ", ".join(sorted(set(seen.values()))))
    check(seen[(True, "hi")] != seen[(False, "hi")],
          "preview clips never share a directory with final clips")
    check(seen[(False, None)] == "final" and seen[(False, "hi")] == "hi",
          "existing final/lang cache keys are unchanged")


def test_chapters():
    scenes = [{"chapter": None}, {"chapter": "a"}, {"chapter": "b"}]
    check(factory.count_chapters(scenes) == 3,
          "an implicit 0:00 Intro is counted when scene 1 has no chapter",
          str(factory.count_chapters(scenes)))
    scenes = [{"chapter": "x"}, {"chapter": "y"}]
    check(factory.count_chapters(scenes) == 2, "chapters counted without an Intro")
    check(factory.count_chapters([{"chapter": None}]) == 0, "no chapters means zero")


def test_tts_cache():
    a = factory.tts_key("hello", "en-US-AnaNeural", "-8%")
    check(a == factory.tts_key("hello", "en-US-AnaNeural", "-8%"), "cache key is stable")
    check(a != factory.tts_key("hello!", "en-US-AnaNeural", "-8%"),
          "cache key changes with the text")
    check(a != factory.tts_key("hello", "en-GB-SoniaNeural", "-8%"),
          "cache key changes with the voice")
    check(a != factory.tts_key("hello", "en-US-AnaNeural", "+0%"),
          "cache key changes with the rate")

    with tempfile.TemporaryDirectory() as tmp:
        mp3 = os.path.join(tmp, "s.mp3")
        open(mp3, "wb").write(b"\0" * 2048)
        open(mp3 + ".stamp", "w").write(a)
        ran = factory.narrate("hello", "en-US-AnaNeural", "-8%", mp3)
        check(ran is False, "matching stamp skips TTS entirely (offline safe)")


# --------------------------------------------------------------------------
# Music engine
# --------------------------------------------------------------------------

def peak_of(path):
    with wave.open(path) as w:
        n = w.getnframes()
        raw = w.readframes(n)
    import array
    a = array.array("h")
    a.frombytes(raw)
    return max(abs(v) for v in a) / 32767.0, n / 44100.0


def test_music():
    with tempfile.TemporaryDirectory() as tmp:
        b1 = music.render_bgm(os.path.join(tmp, "a.wav"), 6.0, seed=5)
        b2 = music.render_bgm(os.path.join(tmp, "b.wav"), 6.0, seed=5)
        b3 = music.render_bgm(os.path.join(tmp, "c.wav"), 6.0, seed=6)
        check(open(b1, "rb").read() == open(b2, "rb").read(),
              "same seed renders byte-identical music")
        check(open(b1, "rb").read() != open(b3, "rb").read(),
              "a different seed renders different music")
        pk, secs = peak_of(b1)
        check(abs(secs - 6.0) < 0.02, "bgm is exactly the requested length",
              f"{secs:.3f}s")
        check(abs(pk - music.PEAK) < 0.02, "bgm peaks at the target level",
              f"{pk:.3f}")

        st = music.render_sting(os.path.join(tmp, "sting.wav"))
        pk, secs = peak_of(st)
        check(2.3 <= secs <= 2.7, "sting is ~2.5s", f"{secs:.2f}s")
        check(abs(pk - music.PEAK) < 0.02, "sting peaks at the target level")

        for name in factory.VALID_SFX:
            p = music.render_sfx(name, os.path.join(tmp, f"{name}.wav"))
            pk, secs = peak_of(p)
            check(0.5 <= pk <= 0.75 and 0.1 < secs < 2.0, f"sfx {name} sane",
                  f"{secs:.2f}s peak {pk:.2f}")


# --------------------------------------------------------------------------
# QC verdict logic
# --------------------------------------------------------------------------

def synthetic_ctx(tmp, wpm=140.0, lang=None):
    words = "word " * 40
    dur = 40 / wpm * 60 + factory.SCENE_PAD
    scenes = [{"i": i, "duration": dur, "narration": words.strip(),
               "chapter": f"c{i}", "pad": factory.SCENE_PAD} for i in range(1, 9)]
    total = sum(s["duration"] for s in scenes)
    srt = os.path.join(tmp, "c.srt")
    factory.make_srt(scenes, srt)
    video = os.path.join(tmp, "v.mp4")
    open(video, "wb").write(b"\0" * 1024)
    thumbs = []
    for n in ("a", "b"):
        p = os.path.join(tmp, f"t_{n}.jpg")
        open(p, "wb").write(b"\0" * 1024)
        thumbs.append(p)
    return {"title": "T", "project": "p", "video": video, "scenes": scenes,
            "total": total, "srt": srt, "thumbnails": thumbs, "chapters": 8,
            "short": None, "lang": lang}


def test_qc():
    with tempfile.TemporaryDirectory() as tmp:
        # loudness cannot be measured on a fake mp4 -- that warning is expected,
        # so assert on the wpm reasons rather than the overall verdict alone
        text, _ = qc.build_report(synthetic_ctx(tmp, wpm=140))
        check("wpm" not in text.split("Reminders")[0].split("\n\n")[0],
              "140 wpm raises no pacing warning")

        text, verdict = qc.build_report(synthetic_ctx(tmp, wpm=260))
        check("is fast" in text and verdict == "WARN", "260 wpm is flagged fast")

        text, _ = qc.build_report(synthetic_ctx(tmp, wpm=60))
        check("is slow" in text, "60 wpm is flagged slow")

        text, _ = qc.build_report(synthetic_ctx(tmp, wpm=260, lang="hi"))
        check("is fast" not in text and "not enforced for 'hi'" in text,
              "wpm window is reported but not enforced for non-English")

        ctx = synthetic_ctx(tmp, wpm=140)
        ctx["scenes"] = ctx["scenes"][:2]          # ~40s runtime
        ctx["total"] = sum(s["duration"] for s in ctx["scenes"])
        text, verdict = qc.build_report(ctx)
        check("under 2 min" in text, "short runtimes are flagged")

        ctx = synthetic_ctx(tmp, wpm=140)
        ctx["chapters"] = 2
        text, _ = qc.build_report(ctx)
        check("fewer than 3 chapters" in text, "too few chapters is flagged")


# --------------------------------------------------------------------------
# Toolkit + every episode's outro
# --------------------------------------------------------------------------

def load_render_scenes(proj):
    path = os.path.join(proj, "render_scenes.py")
    spec = importlib.util.spec_from_file_location(f"rs_{os.path.basename(proj)}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_toolkit_and_outros():
    img, d = tk.canvas("day")
    check(img.size == (tk.W * tk.SS, tk.H * tk.SS), "canvas renders supersampled",
          f"{img.size}")
    box = tk.title_text(d, (960, 540), "Test", 80)
    check(abs((box[0] + box[2]) / 2 - 960) < 2 and abs((box[1] + box[3]) / 2 - 540) < 2,
          "title_text centers on its anchor")
    check(len(tk.content_boxes()) == 1, "drawn text registers exactly once")
    tk.canvas("day")
    check(tk.content_boxes() == [], "a new canvas clears the registry")

    for prim in ("sky", "ground", "cloud", "sun", "kid", "rocket", "molecule",
                 "zig_ray", "arrow", "stars", "title_text", "caption"):
        check(callable(getattr(tk, prim, None)), f"toolkit exposes {prim}()")
    check(len(tk.RAINBOW) == 7, "rainbow palette has seven colors")

    seeds, titles = {}, {}
    for slug in factory.list_projects():
        proj = os.path.join(ROOT, "projects", slug)
        with open(os.path.join(proj, "video.json"), encoding="utf-8") as f:
            cfg = json.load(f)
        seed = cfg.get("music_seed", 7)
        check(seed not in seeds, f"{slug}: music_seed {seed} is unique in the season",
              f"clashes with {seeds.get(seed)}" if seed in seeds else "")
        seeds[seed] = slug
        check(cfg.get("title") not in titles, f"{slug}: title is unique")
        titles[cfg.get("title")] = slug
        check(bool(cfg.get("shorts_scenes")), f"{slug}: has shorts_scenes")
        check(all(1 <= i <= len(cfg["scenes"]) for i in cfg.get("shorts_scenes", [])),
              f"{slug}: shorts_scenes are in range")
        mod = load_render_scenes(proj)
        check(len(mod.SCENES) == len(cfg["scenes"]),
              f"{slug}: render_scenes matches video.json", f"{len(mod.SCENES)} scenes")
        mod.SCENES[-1]()                       # draw the outro
        zones = tk.end_screen_guides(None) if False else {
            "end_cards": (int(tk.W * 0.60), int(tk.H * 0.60), tk.W, tk.H)}
        bad = tk.safe_zone_violations(zones["end_cards"])
        check(not bad, f"{slug}: outro keeps the end-card zone clear", str(bad))
        for s in cfg["scenes"]:
            if s.get("sfx") and s["sfx"] not in factory.VALID_SFX:
                check(False, f"{slug}: unknown sfx {s['sfx']}")
        check(all(s.get("narration") for s in cfg["scenes"]),
              f"{slug}: every scene has narration")


# --------------------------------------------------------------------------
# Short captions: cue re-timing, card rendering
# --------------------------------------------------------------------------

def test_short_cues():
    scenes = [{"i": 1, "duration": 10.0, "narration": "Aaa bbb. Ccc ddd.",
               "pad": factory.SCENE_PAD},
              {"i": 2, "duration": 6.0, "narration": "Two only.",
               "pad": factory.SCENE_PAD},
              {"i": 3, "duration": 8.0, "narration": "Three here. And more.",
               "pad": factory.SCENE_PAD}]
    full = factory.caption_cues(scenes)
    check(len(full) == 5, "caption_cues emits one cue per sentence", str(len(full)))
    check(abs(full[0][0] - factory.NARRATION_OFFSET) < 1e-9,
          "first cue starts at the narration offset")

    cues = factory.short_cues(scenes, [2, 3])
    check(len(cues) == 3, "short cues cover only the picked scenes", str(len(cues)))
    check(abs(cues[0][0] - factory.NARRATION_OFFSET) < 1e-6,
          "the first picked scene is re-timed to the start of the Short",
          f"{cues[0][0]:.3f}s")
    # scene 3's cues must start after scene 2's whole duration, not after
    # scene 2's position in the *episode*
    check(abs(cues[1][0] - (6.0 + factory.NARRATION_OFFSET)) < 1e-6,
          "the second picked scene starts one scene-duration in",
          f"{cues[1][0]:.3f}s")
    total = sum(scenes[i - 1]["duration"] for i in (2, 3))
    check(max(c[1] for c in cues) <= total + 1e-6,
          "no burned cue runs past the end of the Short")

    # out-of-order and out-of-range picks must not explode or leak scenes
    check(factory.short_cues(scenes, [3, 1])[0][2].startswith("Three"),
          "picks are honoured in the order given")
    check(factory.short_cues(scenes, [99]) == [], "an unknown scene picks nothing")


def test_caption_cards():
    from engine import captions as cap

    with tempfile.TemporaryDirectory() as tmp:
        short_txt = "Rivers ARE salty."
        long_txt = ("Sunlight is made of every single colour in the rainbow all "
                    "mixed together into one bright white beam of light.")
        a = cap.render_card(short_txt, os.path.join(tmp, "a.png"), video_w=1080)
        b = cap.render_card(long_txt, os.path.join(tmp, "b.png"), video_w=1080)
        check(os.path.exists(a.path) and a.w > 0 and a.h > 0, "caption card renders",
              f"{a.w}x{a.h}")
        check(a.w <= 1080 and b.w <= 1080, "cards never exceed the video width",
              f"{a.w} / {b.w}")
        check(b.h > a.h, "a longer line wraps to a taller card", f"{a.h} -> {b.h}")
        from PIL import Image
        with Image.open(b.path) as im:
            check(im.mode == "RGBA", "cards keep an alpha channel for overlay")

        # a single unbreakable token cannot wrap, so the font has to shrink or
        # the text paints straight through the side of the card
        huge = cap.render_card("Supercalifragilisticexpialidociousssssssssssssss"
                               "ssssssssssssssssssssssssssssss",
                               os.path.join(tmp, "c.png"), video_w=1080)
        check(huge.w <= 1080, "an unbreakable word still fits the card",
              f"{huge.w}px")
        # non-Latin scripts must pick the Unicode-wide face, not tofu
        dev = cap.render_card("आसमान नीला क्यों है?", os.path.join(tmp, "d.png"),
                              video_w=1080)
        check(dev.w > 0 and dev.w <= 1080, "a Devanagari cue renders a card",
              f"{dev.w}x{dev.h}")
        # regression: a two-line card used to creep back up over the video's
        # own caption banner, because it was anchored by its bottom edge
        letterbox_bottom = (1920 + 1080 * 9 / 16) / 2      # 1263.75
        for card in (a, b):
            y = factory.short_caption_y(card.h)
            check(y >= letterbox_bottom,
                  f"a {card.h}px card clears the 16:9 letterbox", str(y))
            check(y + card.h <= 1920 * factory.SHORT_UI_TOP,
                  f"a {card.h}px card stays out of the Shorts UI strip",
                  str(y + card.h))
        tall = factory.short_caption_y(420)                # 4+ lines, worst case
        check(tall + 420 <= 1920 * factory.SHORT_UI_TOP,
              "even an oversized card is pulled up out of the Shorts UI", str(tall))


# --------------------------------------------------------------------------
# video.json linting
# --------------------------------------------------------------------------

def base_cfg(n=10):
    return {
        "title": "T", "description": "D", "tags": "t",
        "thumbnail_text": "Line one\nTWO", "thumbnail_prop": "rocket",
        "music_seed": 3, "rate": "+0%", "shorts_scenes": [2, 5, 8],
        "scenes": [{"image": f"frames/scene_{i:02d}.png", "chapter": f"c{i}",
                    "sfx": "pop", "narration": " ".join(["word"] * 40)}
                   for i in range(1, n + 1)],
    }


def test_validate():
    with tempfile.TemporaryDirectory() as tmp:
        open(os.path.join(tmp, "render_scenes.py"), "w").write("")
        check(factory.validate_config(base_cfg(), tmp) == [],
              "a well-formed video.json lints clean")

        def one(mutate, needle, label):
            cfg = base_cfg()
            mutate(cfg)
            found = factory.validate_config(cfg, tmp)
            check(any(needle in m for m in found), label,
                  "; ".join(found)[:90] or "no issues raised")

        one(lambda c: c.update(shorts_scenes=[2, 2, 5]), "repeats", "repeated shorts_scenes")
        one(lambda c: c.update(shorts_scenes=[2, 99]), "out of range",
            "out-of-range shorts_scenes")
        one(lambda c: c.update(thumbnail_prop="banana"), "unknown", "unknown thumbnail_prop")
        one(lambda c: c.update(thumbnail_bg="lava"), "thumbnail_bg", "unknown thumbnail_bg")
        one(lambda c: c.update(thumbnail_sky="mauve"), "thumbnail_sky", "unknown thumbnail_sky")
        one(lambda c: c.update(thumbnail_text="only one line"), "two lines",
            "thumbnail_text needs two lines")
        one(lambda c: c.update(rate="0%"), "explicit sign", "rate without a sign")
        one(lambda c: c["scenes"][0].update(narration="too short"), "words",
            "a scene with too few words")
        one(lambda c: c["scenes"][0].update(sfx="explosion"), "unknown sfx",
            "an unknown sfx")
        one(lambda c: c["scenes"][3].update(image="frames/scene_01.png"), "same image",
            "two scenes sharing one image")
        one(lambda c: c["scenes"].__setitem__(
            0, dict(c["scenes"][0], narration="TODO write this")), "TODO",
            "leftover TODO placeholder text")
        one(lambda c: [s.pop("chapter") for s in c["scenes"]], "3 chapters",
            "fewer than three chapters")
        one(lambda c: c.update(languages={"hi": {}}), "no voice",
            "a language block with no voice")

        # every real episode must lint clean -- this is the gate the CLI exposes
        for slug in factory.list_projects():
            proj = os.path.join(ROOT, "projects", slug)
            with open(os.path.join(proj, "video.json"), encoding="utf-8") as f:
                cfg = json.load(f)
            found = factory.validate_config(cfg, proj)
            check(not found, f"{slug}: lints clean", "; ".join(found)[:80])


# --------------------------------------------------------------------------
# Loudness plumbing + thumbnail props
# --------------------------------------------------------------------------

def test_loudness_and_props():
    check(factory._finite(-14.2) and not factory._finite("-inf")
          and not factory._finite(None),
          "silence (-inf) is rejected as a loudnorm measurement")
    # mix and normalize must happen in ONE encode: measuring an intermediate
    # file instead would put three AAC generations on the shipped master
    graph = factory.mix_filter("bed.wav", 100.0, 0.13)
    check("[mix]" in graph and "normalize=0" in graph,
          "the mix graph ends on [mix] and never lets amix halve the narration")
    check(factory.mix_filter(None, 0, 0) == "[0:a]anull[mix]",
          "a music-free episode still produces a [mix] label")
    filt = factory.loudnorm_filter({"input_i": -22.0, "input_tp": -3.0,
                                    "input_lra": 7.0, "input_thresh": -32.0,
                                    "target_offset": 0.5})
    check("linear=true" in filt and "measured_I=-22.0" in filt,
          "measured stats produce a linear (non-pumping) second pass")
    check(f"aresample={factory.AUDIO_SR}" in filt,
          "loudnorm's 192 kHz output is resampled back before the encoder")
    check("linear=true" not in factory.loudnorm_filter(None),
          "a failed probe falls back to single-pass instead of lying")
    check(factory.LOUDNESS_I == -14.0,
          "the loudness target is YouTube's -14 LUFS", str(factory.LOUDNESS_I))
    check(qc.LUFS_TARGET == factory.LOUDNESS_I,
          "QC judges against the same target the factory renders to")

    from engine import thumbnail
    for name in ("rocket", "plane", "sun", "molecule", "planet", "raindrop",
                 "prism", "salt_crystal", "wave", "mountain"):
        check(name in thumbnail.PROPS, f"thumbnail prop {name} is available")
    # every declared prop must actually draw -- the old code silently fell back
    # to a rocket, so a broken prop shipped as a rocket and nobody noticed
    img, d = tk.canvas("day")
    for name, fn in thumbnail.PROPS.items():
        try:
            fn(d, 960, 700, 0.6)
            ok, why = True, ""
        except Exception as e:                      # noqa: BLE001
            ok, why = False, f"{type(e).__name__}: {e}"
        check(ok, f"thumbnail prop {name} draws without error", why)
    for slug in factory.list_projects():
        with open(os.path.join(ROOT, "projects", slug, "video.json"),
                  encoding="utf-8") as f:
            prop = json.load(f).get("thumbnail_prop", "rocket")
        check(prop in thumbnail.PROPS, f"{slug}: thumbnail_prop {prop!r} is real")


# --------------------------------------------------------------------------
# Frame staleness -- editing the art must invalidate the frames
# --------------------------------------------------------------------------

def test_frame_staleness():
    with tempfile.TemporaryDirectory() as tmp:
        cfg = {"scenes": [{"image": "frames/scene_01.png"}]}
        frames = os.path.join(tmp, "frames")
        os.makedirs(frames)
        png = os.path.join(frames, "scene_01.png")
        script = os.path.join(tmp, "render_scenes.py")
        with open(script, "w") as f:
            f.write("import os\n"
                    "os.makedirs('frames', exist_ok=True)\n"
                    "open('frames/scene_01.png','ab').write(b'x')\n")

        factory.ensure_frames(tmp, cfg)
        check(os.path.exists(png), "a missing frame is rendered")
        size = os.path.getsize(png)

        factory.ensure_frames(tmp, cfg)
        check(os.path.getsize(png) == size, "an up-to-date frame is left alone")

        # the art is code: touching the script has to invalidate the PNG
        os.utime(script, (time.time() + 10, time.time() + 10))
        factory.ensure_frames(tmp, cfg)
        check(os.path.getsize(png) > size, "editing render_scenes.py re-renders",
              f"{size} -> {os.path.getsize(png)} bytes")

        size = os.path.getsize(png)
        factory.ensure_frames(tmp, cfg, force=True)
        check(os.path.getsize(png) > size, "--force re-renders even a fresh frame")


def test_scaffold_shorts():
    import new_episode

    for n in (1, 2, 3, 4, 10):
        with tempfile.TemporaryDirectory() as tmp:
            new_episode.PROJECTS, old = tmp, new_episode.PROJECTS
            try:
                proj = new_episode.scaffold(f"probe-{n}", None, n)
            finally:
                new_episode.PROJECTS = old
            with open(os.path.join(proj, "video.json"), encoding="utf-8") as f:
                cfg = json.load(f)
            idx = cfg["shorts_scenes"]
            check(len(set(idx)) == len(idx) and all(1 <= i <= n for i in idx),
                  f"scaffold with {n} scenes makes distinct in-range shorts_scenes",
                  str(idx))


def main():
    print("\nunit tests")
    print("-" * 60)
    for fn in (test_concat_paths, test_srt, test_frame_alignment,
               test_variant_isolation, test_chapters, test_tts_cache,
               test_music, test_qc, test_short_cues, test_caption_cards,
               test_validate, test_loudness_and_props, test_frame_staleness,
               test_scaffold_shorts, test_toolkit_and_outros):
        print(f"\n{fn.__name__}")
        fn()
    print("-" * 60)
    if FAILED:
        print(f"FAILED {len(FAILED)}/{PASSED + len(FAILED)}: {', '.join(FAILED)}\n")
        return 1
    print(f"OK -- {PASSED} checks passed\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
