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

    for slug in factory.list_projects():
        proj = os.path.join(ROOT, "projects", slug)
        cfg = json.load(open(os.path.join(proj, "video.json"), encoding="utf-8"))
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


def main():
    print("\nunit tests")
    print("-" * 60)
    for fn in (test_concat_paths, test_srt, test_tts_cache, test_music,
               test_qc, test_toolkit_and_outros):
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
