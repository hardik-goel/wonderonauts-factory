#!/usr/bin/env python3
"""
Wonder-o-nauts video factory -- one command turns a project folder into a
YouTube-ready episode.

    python3 factory.py projects/why-is-the-sky-blue            # full 1080p build
    python3 factory.py projects/why-is-the-sky-blue --shorts   # + vertical Short
    python3 factory.py projects/why-is-the-sky-blue --preview  # fast low-res draft
    python3 factory.py projects/why-is-the-sky-blue --lang hi  # language variant
    python3 factory.py projects/why-is-the-sky-blue --voice en-GB-SoniaNeural
    python3 factory.py --all                                   # every 'ready' episode
    python3 factory.py --check                                 # preflight

Everything is generated: visuals by Pillow, music by numpy, narration by
edge-tts (the only network step, and it is cached). No paid APIs, no keys.

Outputs land in <project>/output/:
    final.mp4  short.mp4  captions.srt  thumbnail_a.jpg  thumbnail_b.jpg
    metadata.txt  qc_report.txt  build_manifest.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

VERSION = "3.0.0"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# ---- pipeline constants (change these together, not one at a time) --------
FPS = 30
ZOOM_PER_SEC = 0.004          # Ken Burns speed
ZOOM_MAX = 1.25
FADE = 0.4                    # scene fade in/out, seconds
SCENE_PAD = 0.7               # silence added after narration
NARRATION_OFFSET = 0.3        # narration starts after the fade-in has opened
SFX_VOL = 0.45
STING_VOL = 0.28
BGM_VOL = 0.13
BGM_FADE_OUT = 2.0
CRF, PRESET = 19, "medium"
AUDIO_BR, AUDIO_SR = "192k", 44100

PREVIEW = dict(w=640, h=360, crf=30, preset="ultrafast")
SHORT_W, SHORT_H = 1080, 1920

DEFAULT_VOICE = "en-US-AnaNeural"
DEFAULT_RATE = "-8%"
VALID_SFX = ("whoosh", "pop", "sparkle", "success")


class BuildError(Exception):
    pass


# ==========================================================================
# Shell helpers
# ==========================================================================

def sh(cmd, quiet=True, timeout=3600):
    """Run a command, raising BuildError with the tail of stderr on failure."""
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if p.returncode != 0:
        tail = "\n".join((p.stderr or p.stdout or "").strip().splitlines()[-14:])
        raise BuildError(f"command failed: {' '.join(cmd[:4])} ...\n{tail}")
    if not quiet and p.stdout:
        print(p.stdout)
    return p


def ffprobe_duration(path: str) -> float:
    p = sh(["ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=nw=1:nk=1", path])
    try:
        return float(p.stdout.strip().splitlines()[0])
    except (ValueError, IndexError):
        raise BuildError(f"could not read duration of {path}")


def ffprobe_size(path: str):
    p = sh(["ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", path])
    w, h = p.stdout.strip().split("x")[:2]
    return int(w), int(h)


def ffmpeg_version() -> str:
    try:
        p = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
        return p.stdout.splitlines()[0].strip()
    except Exception:
        return "unknown"


def newer(target: str, *deps: str) -> bool:
    """True if `target` exists and is newer than every existing dependency."""
    if not os.path.exists(target):
        return False
    t = os.path.getmtime(target)
    return all(t >= os.path.getmtime(d) for d in deps if os.path.exists(d))


def concat_list(paths, list_path: str) -> str:
    """Write an ffmpeg concat demuxer list. Handles Windows paths and quotes."""
    with open(list_path, "w", encoding="utf-8") as f:
        for p in paths:
            ap = os.path.abspath(p).replace("\\", "/").replace("'", r"'\''")
            f.write(f"file '{ap}'\n")
    return list_path


def fmt_ts(sec: float) -> str:
    return f"{int(sec // 60)}:{int(sec % 60):02d}"


def srt_ts(sec: float) -> str:
    sec = max(0.0, sec)
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int(round((s - int(s)) * 1000)):03d}"


# ==========================================================================
# Project loading
# ==========================================================================

def list_projects():
    """Episode slugs in projects/. Names starting with _ are scratch (e.g. _smoke)."""
    root = os.path.join(HERE, "projects")
    if not os.path.isdir(root):
        return []
    return sorted(d for d in os.listdir(root)
                  if not d.startswith("_")
                  and os.path.exists(os.path.join(root, d, "video.json")))


def load_project(project: str):
    proj = os.path.abspath(project.rstrip("/\\"))
    cfg_path = os.path.join(proj, "video.json")
    if not os.path.isdir(proj):
        raise BuildError(f"no such project folder: {project}")
    if not os.path.exists(cfg_path):
        raise BuildError(f"missing {cfg_path}")
    with open(cfg_path, encoding="utf-8") as f:
        cfg = json.load(f)
    if not cfg.get("scenes"):
        raise BuildError(f"{cfg_path} has no scenes")
    return proj, cfg


def ensure_frames(proj: str, cfg: dict):
    """Run the project's render_scenes.py if any scene image is missing."""
    missing = [s["image"] for s in cfg["scenes"]
               if not os.path.exists(os.path.join(proj, s["image"]))]
    if not missing:
        return
    script = os.path.join(proj, "render_scenes.py")
    if not os.path.exists(script):
        raise BuildError(f"missing frames {missing[:3]} and no render_scenes.py")
    print(f"  frames: {len(missing)} missing -> running render_scenes.py")
    p = subprocess.run([sys.executable, script], cwd=proj, capture_output=True, text=True)
    if p.returncode != 0:
        raise BuildError(f"render_scenes.py failed:\n{p.stderr[-1200:]}")
    still = [s["image"] for s in cfg["scenes"]
             if not os.path.exists(os.path.join(proj, s["image"]))]
    if still:
        raise BuildError(f"render_scenes.py did not produce: {still}")


# ==========================================================================
# Narration (the only network step -- and it is cached)
# ==========================================================================

def tts_key(text: str, voice: str, rate: str) -> str:
    return hashlib.sha256(f"{voice}|{rate}|{text}".encode("utf-8")).hexdigest()


def narrate(text: str, voice: str, rate: str, out_mp3: str, force: bool = False) -> bool:
    """Synthesize narration unless the cache stamp still matches. True if it ran."""
    stamp = out_mp3 + ".stamp"
    key = tts_key(text, voice, rate)
    if not force and os.path.exists(out_mp3) and os.path.exists(stamp):
        if open(stamp, encoding="utf-8").read().strip() == key:
            return False
    os.makedirs(os.path.dirname(os.path.abspath(out_mp3)), exist_ok=True)
    _edge_tts(text, voice, rate, out_mp3)
    with open(stamp, "w", encoding="utf-8") as f:
        f.write(key)
    return True


def _edge_tts(text: str, voice: str, rate: str, out_mp3: str):
    try:
        import asyncio

        import edge_tts
    except ImportError:
        raise BuildError("edge-tts is not installed -- pip install -r requirements.txt")
    tmp = out_mp3 + ".part"
    last = None
    for attempt in range(3):
        try:
            async def go():
                comm = edge_tts.Communicate(text, voice, rate=rate)
                await comm.save(tmp)
            asyncio.run(go())
            if os.path.getsize(tmp) < 512:
                raise BuildError("edge-tts returned an empty file")
            os.replace(tmp, out_mp3)
            return
        except Exception as e:                       # network hiccup -> retry
            last = e
            time.sleep(1.5 * (attempt + 1))
    if os.path.exists(tmp):
        os.remove(tmp)
    raise BuildError(f"edge-tts failed for voice {voice}: {last}")


# ==========================================================================
# Audio assets
# ==========================================================================

def ensure_sfx(audio_dir: str):
    """Render the four SFX + the channel sting once per project."""
    from engine import music

    os.makedirs(audio_dir, exist_ok=True)
    paths = {}
    for name in VALID_SFX:
        p = os.path.join(audio_dir, f"sfx_{name}.wav")
        if not os.path.exists(p):
            music.render_sfx(name, p)
        paths[name] = p
    sting = os.path.join(audio_dir, "sting.wav")
    if not os.path.exists(sting):
        music.render_sting(sting)
    paths["_sting"] = sting
    return paths


# ==========================================================================
# Clip building
# ==========================================================================

def build_clip(image: str, narration: str, sfx_wav: str, out: str, duration: float,
               preview: bool = False, sting: str | None = None):
    """One scene -> one encoded clip. Ken Burns + fades + narration + SFX."""
    frames = max(1, int(round(duration * FPS)))
    zoom_step = ZOOM_PER_SEC / FPS
    w, h = (PREVIEW["w"], PREVIEW["h"]) if preview else (1920, 1080)
    # zoompan crops from a slightly upscaled copy so the pan lands on whole
    # source pixels (no jitter). ZOOM_MAX is exactly enough headroom -- going
    # wider than that only burns encode time.
    pre_w = int(w * ZOOM_MAX) // 2 * 2

    vf = (
        f"scale={pre_w}:-2,"
        f"zoompan=z='min(zoom+{zoom_step:.7f},{ZOOM_MAX})'"
        f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
        f":d={frames}:s={w}x{h}:fps={FPS},"
        f"fade=t=in:st=0:d={FADE},"
        f"fade=t=out:st={max(0.0, duration - FADE):.3f}:d={FADE},"
        f"format=yuv420p[v]"
    )

    inputs = ["-loop", "1", "-i", image, "-i", narration, "-i", sfx_wav]
    delay = int(NARRATION_OFFSET * 1000)
    parts = [
        f"[1:a]adelay={delay}|{delay}[nar]",
        f"[2:a]volume={SFX_VOL}[sfx]",
    ]
    mix_in = "[nar][sfx]"
    n_mix = 2
    if sting:
        # the channel audio logo: it opens scene 1 and closes the outro scene
        inputs += ["-i", sting]
        parts.append(f"[3:a]volume={STING_VOL}[stg]")
        mix_in += "[stg]"
        n_mix = 3
    # normalize=0 is critical: amix would otherwise halve the narration
    parts.append(f"{mix_in}amix=inputs={n_mix}:duration=longest:normalize=0,"
                 f"apad,atrim=0:{duration:.3f},asetpts=N/SR/TB[a]")
    fc = f"[0:v]{vf};" + ";".join(parts)

    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
           *inputs, "-filter_complex", fc, "-map", "[v]", "-map", "[a]",
           "-frames:v", str(frames), "-r", str(FPS),
           "-c:v", "libx264",
           "-crf", str(PREVIEW["crf"] if preview else CRF),
           "-preset", PREVIEW["preset"] if preview else PRESET,
           "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", AUDIO_BR, "-ar", str(AUDIO_SR), "-ac", "2",
           "-movflags", "+faststart", out]
    sh(cmd)
    return out


def concat_clips(clips, out: str, work_dir: str, name: str = "concat"):
    lst = concat_list(clips, os.path.join(work_dir, f"{name}.txt"))
    sh(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy",
        "-movflags", "+faststart", out])
    return out


def add_music(video: str, bgm_wav: str, out: str, total: float, vol: float):
    """Mix the synthesized bed under the narration. Video stream is copied."""
    fade_start = max(0.0, total - BGM_FADE_OUT)
    fc = (f"[1:a]volume={vol},afade=t=out:st={fade_start:.3f}:d={BGM_FADE_OUT}[bg];"
          f"[0:a][bg]amix=inputs=2:duration=first:normalize=0[a]")
    sh(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", video, "-i", bgm_wav, "-filter_complex", fc,
        "-map", "0:v", "-map", "[a]", "-c:v", "copy",
        "-c:a", "aac", "-b:a", AUDIO_BR, "-ar", str(AUDIO_SR), "-ac", "2",
        "-movflags", "+faststart", out])
    return out


def make_short(clips, out: str, work_dir: str, bgm_wav: str | None = None,
               vol: float = BGM_VOL):
    """Re-frame selected clips to 1080x1920 using the blurred-fill technique."""
    joined = os.path.join(work_dir, "short_src.mp4")
    concat_clips(clips, joined, work_dir, name="short_concat")
    reframed = os.path.join(work_dir, "short_reframed.mp4")
    fc = (
        f"[0:v]split=2[bg][fg];"
        f"[bg]scale={SHORT_W}:{SHORT_H}:force_original_aspect_ratio=increase,"
        f"crop={SHORT_W}:{SHORT_H},boxblur=28:2,eq=brightness=-0.06[bgb];"
        f"[fg]scale={SHORT_W}:-2[fgs];"
        f"[bgb][fgs]overlay=(W-w)/2:(H-h)/2,format=yuv420p[v]"
    )
    sh(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", joined,
        "-filter_complex", fc, "-map", "[v]", "-map", "0:a",
        "-c:v", "libx264", "-crf", str(CRF), "-preset", PRESET,
        "-c:a", "aac", "-b:a", AUDIO_BR, "-ar", str(AUDIO_SR), "-ac", "2",
        "-movflags", "+faststart", reframed])
    if bgm_wav:
        add_music(reframed, bgm_wav, out, ffprobe_duration(reframed), vol)
    else:
        shutil.copyfile(reframed, out)
    return out


# ==========================================================================
# Captions, metadata, manifest
# ==========================================================================

# A sentence ends at . ! ? … or the Devanagari danda -- but only when the next
# word starts a new sentence. Without the lookahead, "Why is the sky... blue?"
# becomes two captions, which reads as a stutter on screen.
SENT_BOUNDARY = re.compile(r"(?<=[.!?…।])[\"'\u201d\u2019)\]]*\s+(?![a-z])")


def split_sentences(text: str):
    parts = [p.strip() for p in SENT_BOUNDARY.split(text.strip())]
    return [p for p in parts if p] or [text.strip()]


def make_srt(scenes, path: str) -> int:
    """Sentence-level SRT; each scene's measured speech time is split across
    its sentences in proportion to character count."""
    cues, t = [], 0.0
    for s in scenes:
        speech = max(0.2, s["duration"] - SCENE_PAD)
        start = t + NARRATION_OFFSET
        sents = split_sentences(s["narration"])
        total_chars = sum(max(1, len(x)) for x in sents)
        cur = start
        for sent in sents:
            share = speech * (max(1, len(sent)) / total_chars)
            cues.append((cur, cur + share, sent))
            cur += share
        t += s["duration"]
    with open(path, "w", encoding="utf-8") as f:
        for i, (a, b, txt) in enumerate(cues, 1):
            f.write(f"{i}\n{srt_ts(a)} --> {srt_ts(b)}\n{txt}\n\n")
    return len(cues)


def make_metadata(path: str, cfg: dict, scenes, total: float, lang: str | None,
                  artifacts: dict) -> int:
    """Title / description / tags / chapters / upload checklist in one file."""
    title = cfg.get("title", "Untitled")
    desc = cfg.get("description", "")
    tags = cfg.get("tags", "")
    if lang:
        lc = cfg.get("languages", {}).get(lang, {})
        title = lc.get("title", title)
        desc = lc.get("description", desc)
        tags = lc.get("tags", tags)

    chapters, t = [], 0.0
    for s in scenes:
        if s.get("chapter"):
            chapters.append((t, s["chapter"]))
        t += s["duration"]
    if chapters and chapters[0][0] > 0:
        chapters.insert(0, (0.0, "Intro"))

    L = []
    L.append("=" * 68)
    L.append("  YOUTUBE UPLOAD SHEET" + (f"  [{lang}]" if lang else ""))
    L.append("=" * 68)
    L.append("")
    L.append("--- TITLE " + "-" * 57)
    L.append(title)
    L.append("")
    L.append("--- DESCRIPTION " + "-" * 51)
    L.append(desc.strip())
    if chapters:
        L.append("")
        L.append("Chapters:")
        for ts, label in chapters:
            L.append(f"{fmt_ts(ts)} {label}")
    L.append("")
    L.append("--- TAGS " + "-" * 58)
    L.append(tags)
    L.append("")
    L.append("--- RUNTIME " + "-" * 55)
    L.append(f"{fmt_ts(total)} ({total:.1f}s), {len(scenes)} scenes, "
             f"{len(chapters)} chapters")
    L.append("")
    L.append("--- FILES " + "-" * 57)
    for k, v in artifacts.items():
        if v and os.path.exists(v):
            L.append(f"{k:<14} {os.path.basename(v):<22} "
                     f"{os.path.getsize(v)/1e6:.2f} MB")
    L.append("")
    L.append("--- UPLOAD CHECKLIST " + "-" * 46)
    L.append("[ ] *** Mark as 'Made for Kids' = YES *** (COPPA -- required)")
    L.append("[ ] Audience: 'Yes, it's made for kids'; age restriction: none")
    L.append("[ ] Upload thumbnail_a.jpg, then run YouTube 'Test & Compare'")
    L.append("    with thumbnail_b.jpg to A/B test the click-through rate")
    L.append("[ ] Paste the chapter timestamps above into the description")
    L.append("[ ] Upload captions.srt as English subtitles (do not auto-generate)")
    L.append("[ ] Category: Education   |   Playlist: Wonder-o-nauts")
    L.append("[ ] Comments: hold potentially inappropriate comments for review")
    L.append("[ ] No external links in the description aimed at children")
    if artifacts.get("short"):
        L.append("[ ] Upload short.mp4 separately with #Shorts in its title")
    L.append("[ ] Check qc_report.txt says PASS before publishing")
    L.append("")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    return len(chapters)


def write_manifest(path: str, cfg: dict, scenes, opts, artifacts: dict,
                   total: float, lang: str | None):
    man = {
        "factory_version": VERSION,
        "built_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "project": os.path.basename(os.path.dirname(os.path.dirname(path))),
        "title": cfg.get("title"),
        "language": lang or "en",
        "voice": opts["voice"],
        "rate": opts["rate"],
        "music": bool(cfg.get("music", True)),
        "music_seed": cfg.get("music_seed", 7),
        "bgm_vol": cfg.get("bgm_vol", BGM_VOL),
        "fps": FPS,
        "total_duration": round(total, 3),
        "ffmpeg": ffmpeg_version(),
        "python": sys.version.split()[0],
        "scenes": [{
            "index": s["i"],
            "image": s["image"],
            "sfx": s.get("sfx"),
            "chapter": s.get("chapter"),
            "duration": round(s["duration"], 3),
            "narration_sha256": hashlib.sha256(s["narration"].encode("utf-8")).hexdigest(),
            "narration_chars": len(s["narration"]),
        } for s in scenes],
        "artifacts": {k: {"path": os.path.basename(v),
                          "bytes": os.path.getsize(v)}
                      for k, v in artifacts.items() if v and os.path.exists(v)},
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(man, f, indent=2)
    return path


# ==========================================================================
# The build
# ==========================================================================

def default_jobs() -> int:
    return max(1, min(4, (os.cpu_count() or 2)))


def build(project: str, shorts=False, preview=False, lang=None, voice=None,
          force=False, jobs: int | None = None) -> dict:
    proj, cfg = load_project(project)
    jobs = jobs or default_jobs()
    name = os.path.basename(proj)
    langs = cfg.get("languages", {}) or {}
    if lang and lang not in langs:
        raise BuildError(f"--lang {lang}: video.json has no languages.{lang} block")

    nkey = f"narration_{lang}" if lang else "narration"
    voice = voice or (langs.get(lang, {}).get("voice") if lang else None) \
        or cfg.get("voice", DEFAULT_VOICE)
    rate = cfg.get("rate", DEFAULT_RATE)
    opts = {"voice": voice, "rate": rate}

    tag = f" [{lang}]" if lang else (" [preview]" if preview else "")
    print(f"\n== {name}{tag} ==")
    print(f"  voice {voice} @ {rate}")

    audio_dir = os.path.join(proj, "audio", lang) if lang else os.path.join(proj, "audio")
    clip_dir = os.path.join(proj, "clips", lang or ("preview" if preview else "final"))
    out_dir = os.path.join(proj, "output", lang) if lang else os.path.join(proj, "output")
    work = os.path.join(proj, "clips", "_work")
    for d in (audio_dir, clip_dir, out_dir, work):
        os.makedirs(d, exist_ok=True)

    ensure_frames(proj, cfg)
    sfx = ensure_sfx(os.path.join(proj, "audio"))

    # ---- narration + durations ------------------------------------------
    scenes = []
    n_tts = 0
    for i, s in enumerate(cfg["scenes"], 1):
        text = s.get(nkey) or s.get("narration")
        if not text:
            raise BuildError(f"scene {i} has no '{nkey}' text")
        mp3 = os.path.join(audio_dir, f"scene_{i:02d}.mp3")
        if narrate(text, voice, rate, mp3, force=force):
            n_tts += 1
            print(f"  tts   scene {i:02d}")
        dur = ffprobe_duration(mp3) + SCENE_PAD
        sfx_name = s.get("sfx", "whoosh")
        if sfx_name not in VALID_SFX:
            raise BuildError(f"scene {i}: unknown sfx {sfx_name!r} (use {VALID_SFX})")
        scenes.append({
            "i": i, "image": s["image"], "narration": text, "chapter": s.get("chapter"),
            "sfx": sfx_name, "mp3": mp3, "duration": dur, "pad": SCENE_PAD,
        })
    print(f"  tts   {n_tts} generated, {len(scenes) - n_tts} cached")

    total = sum(s["duration"] for s in scenes)

    # ---- clips (encoded in parallel; each one still caches individually) --
    clips, todo = [], []
    for s in scenes:
        img = os.path.join(proj, s["image"])
        clip = os.path.join(clip_dir, f"scene_{s['i']:02d}.mp4")
        deps = [img, s["mp3"], sfx[s["sfx"]]]
        use_sting = s["i"] in (1, len(scenes))
        if use_sting:
            deps.append(sfx["_sting"])
        if force or not newer(clip, *deps):
            todo.append((s, img, clip, use_sting))
        clips.append(clip)

    if todo:
        def one(job):
            s, img, clip, use_sting = job
            build_clip(img, s["mp3"], sfx[s["sfx"]], clip, s["duration"],
                       preview=preview,
                       sting=sfx["_sting"] if use_sting else None)
            return f"  clip  scene {s['i']:02d}  {s['duration']:5.2f}s"

        with ThreadPoolExecutor(max_workers=jobs) as pool:
            for msg in pool.map(one, todo):
                print(msg)
    print(f"  clip  {len(todo)} built, {len(clips) - len(todo)} cached "
          f"({jobs} parallel)")

    # ---- concat ---------------------------------------------------------
    joined = os.path.join(work, f"joined_{lang or ('preview' if preview else 'final')}.mp4")
    concat_clips(clips, joined, work, name=f"list_{lang or ('preview' if preview else 'final')}")
    total = ffprobe_duration(joined)

    artifacts: dict = {}

    if preview:
        final = os.path.join(out_dir, "preview.mp4")
        shutil.copyfile(joined, final)
        artifacts["preview"] = final
        srt = os.path.join(out_dir, "preview_captions.srt")
        make_srt(scenes, srt)
        artifacts["captions"] = srt
        print(f"  DONE  preview {fmt_ts(total)} -> {os.path.relpath(final, proj)}")
        return {"total": total, "artifacts": artifacts, "verdict": "PREVIEW",
                "project": proj, "scenes": scenes}

    # ---- music ----------------------------------------------------------
    cfg_path = os.path.join(proj, "video.json")
    final = os.path.join(out_dir, "final.mp4")
    if cfg.get("music", True):
        from engine import music
        bgm = os.path.join(proj, "audio", f"bgm_{int(round(total))}s_"
                                          f"{cfg.get('music_seed', 7)}.wav")
        if force or not os.path.exists(bgm):
            print(f"  music synthesizing {fmt_ts(total)} bed "
                  f"(seed {cfg.get('music_seed', 7)})")
            music.render_bgm(bgm, total, seed=int(cfg.get("music_seed", 7)))
        if force or not newer(final, *clips, bgm, cfg_path):
            add_music(joined, bgm, final, total, float(cfg.get("bgm_vol", BGM_VOL)))
        else:
            print("  music cached")
    else:
        bgm = None
        if force or not newer(final, *clips, cfg_path):
            shutil.copyfile(joined, final)
    artifacts["final"] = final

    # ---- short ----------------------------------------------------------
    short_path = None
    if shorts:
        idx = cfg.get("shorts_scenes") or []
        picks = [clips[i - 1] for i in idx if 1 <= i <= len(clips)]
        if not picks:
            print("  short SKIPPED (no valid shorts_scenes in video.json)")
        else:
            short_path = os.path.join(out_dir, "short.mp4")
            sdur = sum(scenes[i - 1]["duration"] for i in idx if 1 <= i <= len(scenes))
            sbgm = None
            if cfg.get("music", True):
                from engine import music
                sbgm = os.path.join(proj, "audio", f"bgm_short_{int(round(sdur))}s_"
                                                   f"{cfg.get('music_seed', 7)}.wav")
                if force or not os.path.exists(sbgm):
                    music.render_bgm(sbgm, sdur + 2, seed=int(cfg.get("music_seed", 7)))
            deps = picks + ([sbgm] if sbgm else []) + [cfg_path]
            if force or not newer(short_path, *deps):
                make_short(picks, short_path, work, sbgm,
                           float(cfg.get("bgm_vol", BGM_VOL)))
                print(f"  short scenes {idx} -> {os.path.relpath(short_path, proj)}")
            else:
                print("  short cached")
            artifacts["short"] = short_path

    # ---- captions -------------------------------------------------------
    srt = os.path.join(out_dir, "captions.srt")
    n_cues = make_srt(scenes, srt)
    artifacts["captions"] = srt

    # ---- thumbnails -----------------------------------------------------
    from engine import thumbnail
    ta = os.path.join(out_dir, "thumbnail_a.jpg")
    tb = os.path.join(out_dir, "thumbnail_b.jpg")
    thumbnail.render_pair(cfg.get("thumbnail_text", cfg.get("title", "")), ta, tb,
                          prop=cfg.get("thumbnail_prop", "rocket"))
    artifacts["thumbnail_a"] = ta
    artifacts["thumbnail_b"] = tb

    # ---- metadata + manifest + QC ---------------------------------------
    meta = os.path.join(out_dir, "metadata.txt")
    n_chapters = make_metadata(meta, cfg, scenes, total, lang, artifacts)
    artifacts["metadata"] = meta

    manifest = os.path.join(out_dir, "build_manifest.json")
    write_manifest(manifest, cfg, scenes, opts, artifacts, total, lang)
    artifacts["manifest"] = manifest

    from engine import qc
    qc_path = os.path.join(out_dir, "qc_report.txt")
    qc_title = cfg.get("title")
    if lang:
        qc_title = langs.get(lang, {}).get("title", qc_title)
    _, verdict = qc.write_report({
        "title": qc_title, "project": name, "video": final, "lang": lang,
        "scenes": scenes, "total": total, "srt": srt,
        "thumbnails": [ta, tb], "chapters": n_chapters, "short": short_path,
    }, qc_path)
    artifacts["qc"] = qc_path

    print(f"  meta  {n_cues} caption cues, {n_chapters} chapters")
    print(f"  DONE  {fmt_ts(total)}  QC {verdict}  -> {os.path.relpath(out_dir, proj)}/")
    return {"total": total, "artifacts": artifacts, "verdict": verdict,
            "project": proj, "scenes": scenes}


# ==========================================================================
# Preflight
# ==========================================================================

def preflight() -> int:
    ok = True

    def line(good, label, detail=""):
        nonlocal ok
        ok = ok and good
        print(f"  [{'OK ' if good else 'FAIL'}] {label:<16} {detail}")

    print("Wonder-o-nauts factory preflight")
    print(f"  version {VERSION}")
    v = sys.version_info
    line(v >= (3, 9), "python", f"{v.major}.{v.minor}.{v.micro}")
    for mod, pkg in (("PIL", "pillow"), ("numpy", "numpy"), ("edge_tts", "edge-tts")):
        try:
            m = __import__(mod)
            line(True, pkg, getattr(m, "__version__", "installed"))
        except ImportError:
            line(False, pkg, "missing -- pip install -r requirements.txt")
    for tool in ("ffmpeg", "ffprobe"):
        p = shutil.which(tool)
        line(bool(p), tool, p or "not on PATH")
    if shutil.which("ffmpeg"):
        print(f"         {ffmpeg_version()}")
        enc = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"],
                             capture_output=True, text=True).stdout
        line("libx264" in enc, "libx264", "H.264 encoder")
        line(" aac " in enc, "aac", "AAC encoder")
    try:
        from engine import toolkit as tk
        fp = tk.font_path()
        line(True, "font", fp or "Pillow default (install Poppins for best look)")
        tk.font(40)
    except Exception as e:
        line(False, "toolkit", str(e))
    projects = list_projects()
    line(bool(projects), "projects", ", ".join(projects) or "none found")
    print("\n  " + ("ALL GOOD -- run: python3 factory.py projects/<episode>"
                    if ok else "FIX THE FAILURES ABOVE"))
    return 0 if ok else 1


# ==========================================================================
# Season handling
# ==========================================================================

SEASON_PATH = os.path.join(HERE, "season.json")


def load_season():
    if not os.path.exists(SEASON_PATH):
        return {"season": "Season 1", "episodes": []}
    with open(SEASON_PATH, encoding="utf-8") as f:
        return json.load(f)


def season_table(season=None):
    season = season or load_season()
    eps = season.get("episodes", [])
    print(f"\n  {season.get('season', 'Season')}  --  {len(eps)} episodes")
    print(f"  {'#':<3} {'status':<10} {'slug':<32} title")
    print("  " + "-" * 76)
    for i, e in enumerate(eps, 1):
        print(f"  {i:<3} {e.get('status', '?'):<10} {e.get('slug', ''):<32} "
              f"{e.get('title', '')[:38]}")
    counts: dict = {}
    for e in eps:
        counts[e.get("status", "?")] = counts.get(e.get("status", "?"), 0) + 1
    print("  " + "-" * 76)
    print("  " + "  ".join(f"{k}: {v}" for k, v in sorted(counts.items())) or "  empty")
    print()
    return eps


def build_all(args) -> int:
    season = load_season()
    eps = season.get("episodes", [])
    if eps:
        season_table(season)
        targets = [e["slug"] for e in eps if e.get("status") == "ready"]
        if not targets:
            print("  nothing to build: no episode has status 'ready'\n"
                  "  mark one with: python3 plan_season.py set <slug> ready")
            return 0
    else:
        targets = list_projects()
        print(f"  no season.json -- building all {len(targets)} projects")

    rc, results = 0, []
    for slug in targets:
        path = os.path.join(HERE, "projects", slug)
        try:
            r = build(path, shorts=args.shorts, preview=args.preview,
                      lang=args.lang, voice=args.voice, force=args.force,
                      jobs=args.jobs)
            results.append((slug, r["verdict"], fmt_ts(r["total"])))
        except BuildError as e:
            print(f"  ERROR {slug}: {e}")
            results.append((slug, "ERROR", "-"))
            rc = 1
    print("\n  build summary")
    print("  " + "-" * 56)
    for slug, verdict, dur in results:
        print(f"  {verdict:<8} {dur:>7}  {slug}")
    print()
    return rc


# ==========================================================================
# CLI
# ==========================================================================

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="factory.py",
        description="Wonder-o-nauts video factory -- one command per episode.")
    ap.add_argument("project", nargs="?", help="path to projects/<episode>")
    ap.add_argument("--shorts", action="store_true", help="also build a 9:16 Short")
    ap.add_argument("--preview", action="store_true",
                    help="fast 640x360 draft (no music, no thumbnails)")
    ap.add_argument("--lang", metavar="CODE", help="build a language variant, e.g. hi")
    ap.add_argument("--voice", metavar="NAME", help="edge-tts voice override")
    ap.add_argument("--all", action="store_true", help="build every 'ready' episode")
    ap.add_argument("--check", action="store_true", help="preflight: deps, fonts, ffmpeg")
    ap.add_argument("--season", action="store_true", help="print the season status table")
    ap.add_argument("--force", action="store_true", help="ignore caches and rebuild")
    ap.add_argument("--jobs", type=int, metavar="N",
                    help=f"parallel scene encodes (default {default_jobs()})")
    ap.add_argument("--version", action="version", version=f"factory {VERSION}")
    args = ap.parse_args(argv)

    if args.check:
        return preflight()
    if args.season:
        season_table()
        return 0
    if args.all:
        return build_all(args)
    if not args.project:
        ap.print_help()
        return 2

    t0 = time.time()
    try:
        build(args.project, shorts=args.shorts, preview=args.preview,
                  lang=args.lang, voice=args.voice, force=args.force,
                  jobs=args.jobs)
    except BuildError as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        return 1
    print(f"  built in {time.time() - t0:.1f}s\n")
    return 0          # QC is advisory: it reports, the owner decides


if __name__ == "__main__":
    sys.exit(main())
