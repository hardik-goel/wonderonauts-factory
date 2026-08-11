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
        # A bare sine is a pathological input for the loudness stage: it has no
        # crest factor, so loudnorm's limiter cannot hold the true-peak target
        # and QC correctly-but-uselessly warns about clipping on every CI run.
        # The tremolo gives the tone a speech-like envelope, which is what the
        # real pipeline is actually tuned for.
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
             "-f", "lavfi", "-i", f"sine=frequency={200 + i * 40}:duration={dur}",
             "-af", "tremolo=f=4.5:d=0.85,volume=0.22", "-ar", "44100", "-ac", "1",
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

    expected = ["final.mp4", "short.mp4", "captions.srt", "short_captions.srt",
                "thumbnail_a.jpg", "thumbnail_b.jpg", "metadata.txt",
                "qc_report.txt", "build_manifest.json"]
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
        # the Short must be exactly the picked scenes, not the whole episode
        picked = [i for i in cfg.get("shorts_scenes", [])
                  if 1 <= i <= len(cfg["scenes"])]
        want = sum(s["duration"] for s in result["scenes"] if s["i"] in picked)
        got = factory.ffprobe_duration(short)
        check(abs(got - want) < 0.5, "short.mp4 runs for its picked scenes only",
              f"{got:.1f}s vs {want:.1f}s")
        scues = factory.short_cues(result["scenes"], picked)
        check(len(scues) > 0, "the Short has caption cues to burn in",
              f"{len(scues)} cues")
        check(max(c[1] for c in scues) <= got + 0.5,
              "no burned caption outlives the Short")

    # Loudness: the whole point is that a quiet master cannot ship silently.
    lufs, tp = None, None
    if os.path.exists(final):
        from engine import qc as qc_mod
        lufs, tp = qc_mod.measure_lufs(final)
        check(lufs is not None, "integrated loudness is measurable",
              f"{lufs} LUFS")
        if lufs is not None:
            check(abs(lufs - factory.LOUDNESS_I) <= qc_mod.LUFS_TOLERANCE,
                  f"final.mp4 lands on the {factory.LOUDNESS_I} LUFS target",
                  f"{lufs:.1f} LUFS")
        if tp is not None:
            check(tp <= 0.0, "true peak stays under 0 dBTP", f"{tp:.1f} dBTP")

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
    check(man.get("loudnorm") is True and man.get("target_lufs") == factory.LOUDNESS_I,
          "manifest records the loudness target", str(man.get("target_lufs")))
    check(man.get("short_captions_burned") is True,
          "manifest records that the Short carries burned-in captions")
    check(man.get("lint_issues") == [], "manifest records a clean lint",
          str(man.get("lint_issues"))[:80])

    for p in (os.path.join(out, "thumbnail_a.jpg"), os.path.join(out, "thumbnail_b.jpg")):
        if os.path.exists(p):
            check(os.path.getsize(p) < 2_000_000, f"{os.path.basename(p)} under 2MB",
                  f"{os.path.getsize(p)/1024:.0f} KB")

    check(not os.path.exists(os.path.join(out, "preview.mp4")),
          "no preview artifact leaked into a full build")

    man_project = man.get("project")
    check(man_project == os.path.basename(proj),
          "manifest records the project slug", str(man_project))

    # Regression: --preview --lang used to drop 640x360 clips into the real
    # language cache, so the next full build would silently ship the draft.
    langs = cfg.get("languages") or {}
    if langs:
        code = sorted(langs)[0]
        lang_audio = os.path.join(proj, "audio", code)
        os.makedirs(lang_audio, exist_ok=True)
        voice = langs[code].get("voice", factory.DEFAULT_VOICE)
        rate = cfg.get("rate", factory.DEFAULT_RATE)
        for i, s in enumerate(cfg["scenes"], 1):
            text = s.get(f"narration_{code}") or s["narration"]
            mp3 = os.path.join(lang_audio, f"scene_{i:02d}.mp3")
            subprocess.run(
                ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                 "-f", "lavfi", "-i", f"sine=frequency={300 + i * 30}:duration=3",
                 "-af", "volume=0.22", "-ar", "44100", "-ac", "1",
                 "-c:a", "libmp3lame", "-b:a", "128k", mp3], check=True)
            with open(mp3 + ".stamp", "w", encoding="utf-8") as f:
                f.write(factory.tts_key(text, voice, rate))
        factory.build(proj, preview=True, lang=code)
        check(os.path.isdir(os.path.join(proj, "clips", f"preview-{code}")),
              f"--preview --lang {code} writes to its own clip dir")
        check(not os.path.isdir(os.path.join(proj, "clips", code)),
              f"--preview --lang {code} does NOT touch the real {code} clip cache")
        check(os.path.exists(os.path.join(proj, "output", code, "preview.mp4")),
              f"preview.mp4 written under output/{code}/")
        lman = os.path.join(proj, "output", code, "preview_manifest.json")
        check(os.path.exists(lman), "preview build writes a manifest too")
        if os.path.exists(lman):
            with open(lman, encoding="utf-8") as f:
                lm = json.load(f)
            check(lm["project"] == os.path.basename(proj) and lm["mode"] == "preview",
                  "preview manifest records slug and mode",
                  f'{lm["project"]}/{lm["mode"]}')

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
