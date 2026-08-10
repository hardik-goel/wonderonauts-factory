#!/usr/bin/env python3
"""
Network-free smoke test for the whole factory.

edge-tts is the only step that needs the internet, so this test fabricates the
narration: a quiet sine tone per scene, whose length matches the real script at
140 wpm, plus the exact cache stamp factory.py would have written. The factory
therefore finds every narration "already cached" and never touches the network.

Everything else -- frames, music, clips, concat, BGM, captions, thumbnails,
Short, metadata, manifest, QC -- runs for real.

The episode is copied to projects/_smoke/ first, so a test run can never
overwrite the real project's narration cache or output.

    python3 tests/smoke.py                       # episode 1, with --shorts
    python3 tests/smoke.py projects/<episode>
    python3 tests/smoke.py --keep                # leave projects/_smoke/ behind
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import factory  # noqa: E402

WPM = 140.0
FAILURES: list[str] = []


def check(cond, label, detail=""):
    print(f"  [{'PASS' if cond else 'FAIL'}] {label}" + (f"  {detail}" if detail else ""))
    if not cond:
        FAILURES.append(label)
    return cond


SMOKE_DIR = os.path.join(ROOT, "projects", "_smoke")


def stage_copy(src: str) -> str:
    """Copy the episode into projects/_smoke/ -- never build in the real folder."""
    src = os.path.abspath(src.rstrip("/\\"))
    shutil.rmtree(SMOKE_DIR, ignore_errors=True)
    shutil.copytree(src, SMOKE_DIR,
                    ignore=shutil.ignore_patterns("audio", "clips", "output",
                                                  "__pycache__", "*.jpg"))
    return SMOKE_DIR


def fake_narration(project: str):
    """Write sine-tone mp3s + matching cache stamps so TTS is never called."""
    proj, cfg = factory.load_project(project)
    voice = cfg.get("voice", factory.DEFAULT_VOICE)
    rate = cfg.get("rate", factory.DEFAULT_RATE)
    audio = os.path.join(proj, "audio")
    os.makedirs(audio, exist_ok=True)
    made = []
    for i, s in enumerate(cfg["scenes"], 1):
        text = s["narration"]
        words = len(re.findall(r"[\w'’\-]+", text))
        dur = max(2.0, round(words / WPM * 60.0, 2))
        mp3 = os.path.join(audio, f"scene_{i:02d}.mp3")
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
             "-f", "lavfi", "-i", f"sine=frequency={200 + i * 40}:duration={dur}",
             "-af", "volume=0.22", "-ar", "44100", "-ac", "1",
             "-c:a", "libmp3lame", "-b:a", "128k", mp3],
            check=True)
        with open(mp3 + ".stamp", "w", encoding="utf-8") as f:
            f.write(factory.tts_key(text, voice, rate))
        made.append(mp3)
    return proj, cfg, made


def main(argv):
    project = next((a for a in argv if not a.startswith("-")),
                   os.path.join(ROOT, "projects", "why-is-the-sky-blue"))
    keep = "--keep" in argv

    print(f"\nsmoke test: {os.path.relpath(project, ROOT)} -> projects/_smoke/")
    print("-" * 60)
    proj, cfg, mp3s = fake_narration(stage_copy(project))
    check(len(mp3s) == len(cfg["scenes"]), "fake narration written",
          f"{len(mp3s)} files")

    result = factory.build(proj, shorts=True)
    out = os.path.join(proj, "output")

    expected = ["final.mp4", "short.mp4", "captions.srt", "thumbnail_a.jpg",
                "thumbnail_b.jpg", "metadata.txt", "qc_report.txt",
                "build_manifest.json"]
    for name in expected:
        p = os.path.join(out, name)
        check(os.path.exists(p) and os.path.getsize(p) > 0, f"artifact {name}",
              f"{os.path.getsize(p)/1024:.0f} KB" if os.path.exists(p) else "missing")

    final = os.path.join(out, "final.mp4")
    if os.path.exists(final):
        dur = factory.ffprobe_duration(final)
        check(dur > 10.0, "final.mp4 duration > 10s", f"{dur:.1f}s")
        w, h = factory.ffprobe_size(final)
        check((w, h) == (1920, 1080), "final.mp4 is 1920x1080", f"{w}x{h}")

    short = os.path.join(out, "short.mp4")
    if os.path.exists(short):
        w, h = factory.ffprobe_size(short)
        check((w, h) == (1080, 1920), "short.mp4 is 1080x1920", f"{w}x{h}")

    srt = os.path.join(out, "captions.srt")
    if os.path.exists(srt):
        body = open(srt, encoding="utf-8").read()
        check(body.count("-->") >= len(cfg["scenes"]), "captions cover every scene",
              f"{body.count('-->')} cues")

    qc_txt = open(os.path.join(out, "qc_report.txt"), encoding="utf-8").read()
    check(("QC PASS" in qc_txt) or ("QC WARN" in qc_txt), "qc_report has a verdict",
          result["verdict"])

    meta = open(os.path.join(out, "metadata.txt"), encoding="utf-8").read()
    check("Made for Kids" in meta, "metadata has the Made-for-Kids reminder")
    check("0:00" in meta, "metadata has chapter timestamps")

    man = json.load(open(os.path.join(out, "build_manifest.json"), encoding="utf-8"))
    check(man["factory_version"] == factory.VERSION, "manifest records the version",
          man["factory_version"])
    check(len(man["scenes"]) == len(cfg["scenes"]), "manifest lists every scene")

    for p in (os.path.join(out, "thumbnail_a.jpg"), os.path.join(out, "thumbnail_b.jpg")):
        if os.path.exists(p):
            check(os.path.getsize(p) < 2_000_000, f"{os.path.basename(p)} under 2MB",
                  f"{os.path.getsize(p)/1024:.0f} KB")

    check(not os.path.exists(os.path.join(out, "preview.mp4")),
          "no preview artifact leaked into a full build")

    if not keep:
        shutil.rmtree(SMOKE_DIR, ignore_errors=True)

    print("-" * 60)
    if FAILURES:
        print(f"SMOKE FAILED: {len(FAILURES)} check(s): {', '.join(FAILURES)}\n")
        return 1
    print("SMOKE OK -- every artifact built from a cold cache, no network used\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
