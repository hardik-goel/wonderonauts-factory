#!/usr/bin/env python3
"""
Wonder-o-nauts video factory -- one command turns a project folder into a
YouTube-ready episode.

    python3 factory.py projects/why-is-the-sky-blue            # full 1080p build
    python3 factory.py projects/why-is-the-sky-blue --shorts   # + vertical Short
    python3 factory.py projects/why-is-the-sky-blue --preview  # fast low-res draft
    python3 factory.py projects/why-is-the-sky-blue --lang hi  # language variant
    python3 factory.py projects/why-is-the-sky-blue --voice en-GB-SoniaNeural
    python3 factory.py projects/why-is-the-sky-blue --validate # lint, do not build
    python3 factory.py projects/why-is-the-sky-blue --clean    # drop rebuildable caches
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

VERSION = "3.1.0"
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

# EBU R128 targets. YouTube plays quiet uploads quietly -- it only ever turns
# loud content DOWN -- so a bed sitting at -24 dB means every viewer reaches for
# the volume knob. -14 LUFS is YouTube's own playback target.
LOUDNESS_I, LOUDNESS_TP, LOUDNESS_LRA = -14.0, -1.5, 11.0

PREVIEW = dict(w=640, h=360, crf=30, preset="ultrafast")
SHORT_W, SHORT_H = 1080, 1920
# Burned-in caption placement in the 9:16 frame. Derived from the geometry
# rather than guessed: the letterboxed 16:9 video ends partway down, scenes may
# already carry their own banner along its bottom edge, and the Shorts UI owns
# the bottom of the screen. The card goes in the gap between the two.
SHORT_CAPTION_GAP = 28         # px below the letterboxed video
SHORT_UI_TOP = 0.86            # below this fraction the Shorts UI takes over

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
    """SRT timestamp. Rounds to whole milliseconds first, so a fraction of
    .9996 becomes the next second rather than a malformed ',1000'."""
    ms = max(0, int(round(max(0.0, sec) * 1000)))
    h, ms = divmod(ms, 3600_000)
    m, ms = divmod(ms, 60_000)
    sec_i, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{sec_i:02d},{ms:03d}"


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


WORDS_MIN, WORDS_MAX = 20, 80          # per scene; 35-55 is the sweet spot

# A two-hander dialogue is a different animal: "Why not?" is a complete beat and
# a 40-word joke line is a bad one. An episode declares format="dialogue" in its
# video.json to be linted against these bounds instead.
DIALOGUE_WORDS_MIN, DIALOGUE_WORDS_MAX = 2, 45


def validate_config(cfg: dict, proj: str) -> list:
    """Lint one video.json. Returns a list of human-readable problems.

    This exists because every one of these mistakes used to cost a full build
    to discover: a scene with placeholder narration, a Short pointing at scene
    12 of a 10-scene episode, two chapters where YouTube needs three.
    """
    from engine import thumbnail

    bad: list = []
    scenes = cfg.get("scenes") or []
    n = len(scenes)

    for key in ("title", "description", "tags"):
        if not str(cfg.get(key, "")).strip():
            bad.append(f"{key} is empty")
    if "TODO" in json.dumps(cfg, ensure_ascii=False):
        bad.append("video.json still contains TODO placeholder text")

    seed = cfg.get("music_seed", 7)
    if not isinstance(seed, int):
        bad.append(f"music_seed must be an integer, got {seed!r}")
    if not str(cfg.get("rate", DEFAULT_RATE)).startswith(("+", "-")):
        bad.append(f"rate {cfg.get('rate')!r} needs an explicit sign, e.g. '+0%'")

    prop = cfg.get("thumbnail_prop", "rocket")
    if prop not in thumbnail.PROPS:
        bad.append(f"thumbnail_prop {prop!r} is unknown "
                   f"(use one of {sorted(thumbnail.PROPS)})")
    if cfg.get("thumbnail_bg", "land") not in thumbnail.BACKDROPS:
        bad.append(f"thumbnail_bg {cfg['thumbnail_bg']!r} is unknown "
                   f"(use one of {list(thumbnail.BACKDROPS)})")
    if cfg.get("thumbnail_sky", "day") not in ("day", "sunset", "night", "plain"):
        bad.append(f"thumbnail_sky {cfg['thumbnail_sky']!r} is unknown "
                   "(day | sunset | night | plain)")
    tt = cfg.get("thumbnail_text", "")
    if len([ln for ln in tt.split("\n") if ln.strip()]) != 2:
        bad.append("thumbnail_text should be exactly two lines "
                   "(line 2 becomes variant B's big word)")

    idx = cfg.get("shorts_scenes") or []
    if not idx:
        bad.append("shorts_scenes is empty -- --shorts will skip this episode")
    if len(set(idx)) != len(idx):
        bad.append(f"shorts_scenes repeats a scene: {idx}")
    out_of_range = [i for i in idx if not (1 <= i <= n)]
    if out_of_range:
        bad.append(f"shorts_scenes out of range for {n} scenes: {out_of_range}")

    fmt = cfg.get("format", "explainer")
    if fmt not in ("explainer", "dialogue"):
        bad.append(f"format {fmt!r} is unknown (explainer | dialogue)")
    w_min, w_max = ((DIALOGUE_WORDS_MIN, DIALOGUE_WORDS_MAX) if fmt == "dialogue"
                    else (WORDS_MIN, WORDS_MAX))

    images = []
    for i, s in enumerate(scenes, 1):
        if not s.get("image"):
            bad.append(f"scene {i}: no image")
        else:
            images.append(s["image"])
            if not os.path.exists(os.path.join(proj, s["image"])):
                # not an error on its own: render_scenes.py will draw it
                if not os.path.exists(os.path.join(proj, "render_scenes.py")):
                    bad.append(f"scene {i}: {s['image']} missing and no render_scenes.py")
        text = s.get("narration", "")
        if not text.strip():
            bad.append(f"scene {i}: no narration")
            continue
        words = len(re.findall(r"[\w'’\-]+", text))
        if not (w_min <= words <= w_max):
            bad.append(f"scene {i}: {words} words of narration "
                       f"(want {w_min}-{w_max})")
        if s.get("sfx") and s["sfx"] not in VALID_SFX:
            bad.append(f"scene {i}: unknown sfx {s['sfx']!r} (use {list(VALID_SFX)})")
    dupes = {p for p in images if images.count(p) > 1}
    if dupes:
        bad.append(f"two scenes share the same image: {sorted(dupes)}")

    if count_chapters(scenes) < 3:
        bad.append("fewer than 3 chapters -- YouTube will not show a chapter list")

    for code, block in (cfg.get("languages") or {}).items():
        if not block.get("voice"):
            bad.append(f"languages.{code}: no voice")
        missing = [i for i, s in enumerate(scenes, 1) if not s.get(f"narration_{code}")]
        if missing:
            bad.append(f"languages.{code}: scenes {missing[:5]} have no narration_{code}")
    return bad


def cmd_validate(targets) -> int:
    """Lint one or more projects without building anything."""
    rc = 0
    for path in targets:
        try:
            proj, cfg = load_project(path)
        except BuildError as e:
            print(f"\n  {path}\n    ERROR {e}")
            rc = 1
            continue
        issues = validate_config(cfg, proj)
        print(f"\n  {os.path.basename(proj)}  --  "
              f"{'OK' if not issues else f'{len(issues)} issue(s)'}")
        for msg in issues:
            print(f"    ! {msg}")
        if issues:
            rc = 1
    print()
    return rc


def cmd_clean(targets) -> int:
    """Delete only what a rebuild can regenerate.

    Narration mp3s are deliberately kept: they are the one artifact that costs
    a network round trip, and the cache stamp already invalidates them when the
    script changes.
    """
    freed, removed = 0, 0
    for path in targets:
        proj = os.path.abspath(path.rstrip("/\\"))
        if not os.path.isdir(proj):
            print(f"  skip {path}: not a folder")
            continue
        victims = [os.path.join(proj, "clips")]
        audio = os.path.join(proj, "audio")
        if os.path.isdir(audio):
            victims += [os.path.join(audio, f) for f in sorted(os.listdir(audio))
                        if f.startswith("bgm_") and f.endswith(".wav")]
        for v in victims:
            if not os.path.exists(v):
                continue
            if os.path.isdir(v):
                size = sum(os.path.getsize(os.path.join(r, f))
                           for r, _, fs in os.walk(v) for f in fs)
                shutil.rmtree(v)
            else:
                size = os.path.getsize(v)
                os.remove(v)
            freed += size
            removed += 1
            print(f"  removed {os.path.relpath(v, proj)}  ({size/1e6:.1f} MB)")
    print(f"\n  {removed} item(s), {freed/1e6:.1f} MB freed "
          f"(narration cache and output/ left alone)\n")
    return 0


def ensure_frames(proj: str, cfg: dict, force: bool = False):
    """Render the project's frames when they are missing or out of date.

    "Out of date" matters as much as "missing": the art is *code*, so editing
    render_scenes.py (or a toolkit primitive it draws with) has to invalidate
    the PNGs. Checking only for missing files meant you could redraw a scene,
    rerun the build, and get the old picture back with no warning at all.
    """
    script = os.path.join(proj, "render_scenes.py")
    frames = [os.path.join(proj, s["image"]) for s in cfg["scenes"]]
    missing = [s["image"] for s, p in zip(cfg["scenes"], frames)
               if not os.path.exists(p)]
    # the art depends on the episode script and on every toolkit module it draws
    # with, so any of them being newer than a frame means that frame is stale
    sources = [script] + [os.path.join(HERE, "engine", m)
                          for m in ("toolkit.py", "__init__.py")]
    stale = []
    if not missing:
        for p in frames:
            if not newer(p, *sources):
                stale.append(os.path.relpath(p, proj))
    if not missing and not stale and not force:
        return
    if not os.path.exists(script):
        if missing:
            raise BuildError(f"missing frames {missing[:3]} and no render_scenes.py")
        return                       # stale but unfixable: hand-placed frames
    why = (f"{len(missing)} missing" if missing else
           f"{len(stale)} stale (render_scenes.py or the toolkit changed)"
           if stale else "forced")
    print(f"  frames: {why} -> running render_scenes.py")
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
    # a scene shorter than two fades would start fading out before it had
    # finished fading in, which reads as a flicker rather than a transition
    fade = min(FADE, duration / 2.2)
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
        f"fade=t=in:st=0:d={fade:.3f},"
        f"fade=t=out:st={max(0.0, duration - fade):.3f}:d={fade:.3f},"
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


def mix_filter(bgm_wav: str | None, total: float, vol: float) -> str:
    """Filtergraph that produces the finished mix on the label [mix].

    normalize=0 is critical: amix would otherwise halve the narration.
    """
    if not bgm_wav:
        return "[0:a]anull[mix]"
    fade_start = max(0.0, total - BGM_FADE_OUT)
    return (f"[1:a]volume={vol},afade=t=out:st={fade_start:.3f}:d={BGM_FADE_OUT}[bg];"
            f"[0:a][bg]amix=inputs=2:duration=first:normalize=0[mix]")


def add_music(video: str, bgm_wav: str, out: str, total: float, vol: float):
    """Mix the synthesized bed under the narration. Video stream is copied."""
    sh(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", video, "-i", bgm_wav,
        "-filter_complex", mix_filter(bgm_wav, total, vol),
        "-map", "0:v", "-map", "[mix]", "-c:v", "copy",
        "-c:a", "aac", "-b:a", AUDIO_BR, "-ar", str(AUDIO_SR), "-ac", "2",
        "-movflags", "+faststart", out])
    return out


# ---- loudness ------------------------------------------------------------
# Two passes, not one. Single-pass loudnorm is a dynamic compressor: it rides
# the gain, which pumps the music bed up in the gaps between sentences. Measure
# first, then apply one constant gain (linear=true) and the mix keeps its shape.

def _finite(v) -> bool:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return False
    return f == f and abs(f) != float("inf")


def _loudnorm_opts() -> str:
    return f"loudnorm=I={LOUDNESS_I}:TP={LOUDNESS_TP}:LRA={LOUDNESS_LRA}"


def loudnorm_measure(inputs, graph: str):
    """Measure the mix produced by `graph`, without writing it out first.

    Measuring the *graph* rather than an intermediate file is what keeps the
    master at a single AAC generation: mix and normalize happen in one encode
    instead of mix -> encode -> measure -> encode.

    Returns the stats dict, or None if the probe failed.
    """
    try:
        p = subprocess.run(
            ["ffmpeg", "-hide_banner", "-nostats", *inputs,
             "-filter_complex", f"{graph};[mix]{_loudnorm_opts()}:print_format=json[a]",
             "-map", "[a]", "-f", "null", "-"],
            capture_output=True, text=True, timeout=1800)
    except Exception:
        return None
    err = p.stderr or ""
    start, end = err.rfind("{"), err.rfind("}")
    if start < 0 or end < start:
        return None
    try:
        stats = json.loads(err[start:end + 1])
    except json.JSONDecodeError:
        return None
    need = ("input_i", "input_tp", "input_lra", "input_thresh", "target_offset")
    # silence measures as -inf and cannot be normalized to anything
    if not all(k in stats and _finite(stats[k]) for k in need):
        return None
    return stats


def loudnorm_filter(stats) -> str:
    """The second-pass loudnorm, using measured values when we have them."""
    filt = _loudnorm_opts()
    if stats:
        filt += (f":measured_I={stats['input_i']}"
                 f":measured_TP={stats['input_tp']}"
                 f":measured_LRA={stats['input_lra']}"
                 f":measured_thresh={stats['input_thresh']}"
                 f":offset={stats['target_offset']}:linear=true")
    # loudnorm resamples internally to 192 kHz; put it back before the encoder
    return filt + f",aresample={AUDIO_SR}"


def finalize(video: str, out: str, bgm_wav: str | None = None,
             total: float = 0.0, vol: float = BGM_VOL,
             loudnorm: bool = True) -> str:
    """Mix the music bed in (if any) and land the result on -14 LUFS.

    Mix and normalization happen in one encode: the loudness measurement runs
    over the filtergraph, so the shipped audio is a single AAC generation off
    the scene clips rather than three.
    """
    inputs = ["-i", video] + (["-i", bgm_wav] if bgm_wav else [])
    graph = mix_filter(bgm_wav, total, vol)

    if not loudnorm:
        if not bgm_wav:
            shutil.copyfile(video, out)
            return out
        return add_music(video, bgm_wav, out, total, vol)

    stats = loudnorm_measure(inputs, graph)
    if not stats:
        print("  audio loudness probe failed -- using single-pass fallback")
    sh(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *inputs,
        "-filter_complex", f"{graph};[mix]{loudnorm_filter(stats)}[a]",
        "-map", "0:v", "-map", "[a]", "-c:v", "copy",
        "-c:a", "aac", "-b:a", AUDIO_BR, "-ar", str(AUDIO_SR), "-ac", "2",
        "-movflags", "+faststart", out])
    return out


def short_caption_y(card_h: int, video_w: int = SHORT_W,
                    video_h: int = SHORT_H) -> int:
    """Top edge for a caption card of height `card_h` in a 9:16 frame.

    Sits just under the letterboxed video, and is pulled up only if the card is
    tall enough to reach the Shorts UI. Anchoring by the bottom instead let a
    two-line cue creep back up over the video's own caption banner.
    """
    letterbox_bottom = (video_h + video_w * 9 / 16) / 2
    top = int(letterbox_bottom + SHORT_CAPTION_GAP)
    return max(0, min(top, int(video_h * SHORT_UI_TOP) - card_h))


def burn_captions(video: str, cues, out: str, work_dir: str, video_w: int,
                  video_h: int, prefix: str = "cap_") -> str:
    """Overlay one caption card per cue onto `video`.

    Uses `overlay` + `enable=` rather than the subtitles/drawtext filters, which
    are optional ffmpeg build features -- see engine/captions.py for why.
    """
    from engine import captions as cap

    cards = []
    for i, (a, b, txt) in enumerate(cues):
        if b <= a or not txt.strip():
            continue
        png = os.path.join(work_dir, f"{prefix}{i:03d}.png")
        cards.append((cap.render_card(txt, png, video_w=video_w), a, b))
    if not cards:
        shutil.copyfile(video, out)
        return out

    inputs, chain, cur = [], [], "[0:v]"
    for i, (card, a, b) in enumerate(cards, start=1):
        inputs += ["-i", card.path]
        y = short_caption_y(card.h, video_w, video_h)
        nxt = f"[v{i}]"
        chain.append(f"{cur}[{i}:v]overlay=x=(W-w)/2:y={y}:"
                     f"enable='between(t,{a:.3f},{b:.3f})'{nxt}")
        cur = nxt
    chain.append(f"{cur}format=yuv420p[vout]")

    sh(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", video,
        *inputs, "-filter_complex", ";".join(chain),
        "-map", "[vout]", "-map", "0:a",
        "-c:v", "libx264", "-crf", str(CRF), "-preset", PRESET,
        "-pix_fmt", "yuv420p", "-c:a", "copy",
        "-movflags", "+faststart", out])
    return out


def make_short(clips, out: str, work_dir: str, bgm_wav: str | None = None,
               vol: float = BGM_VOL, cues=None, loudnorm: bool = True,
               tag: str = "final"):
    """Re-frame selected clips to 1080x1920 using the blurred-fill technique.

    `cues` are burned in as caption cards: a Short is usually watched muted, so
    the on-screen text is not a nicety, it is the whole message.

    Every intermediate is keyed by `tag` (the build variant), because the work
    directory is shared between the English build and each --lang build.
    """
    joined = os.path.join(work_dir, f"short_src_{tag}.mp4")
    concat_clips(clips, joined, work_dir, name=f"short_concat_{tag}")
    reframed = os.path.join(work_dir, f"short_reframed_{tag}.mp4")
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
    if cues:
        burned = os.path.join(work_dir, f"short_captioned_{tag}.mp4")
        burn_captions(reframed, cues, burned, work_dir, SHORT_W, SHORT_H,
                      prefix=f"cap_{tag}_")
        reframed = burned
    return finalize(reframed, out, bgm_wav, ffprobe_duration(reframed),
                    vol, loudnorm)


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


def caption_cues(scenes, scene_index: bool = False):
    """Sentence-level cues (start, end, text) on the full episode timeline.

    Each scene's measured speech time is split across its sentences in
    proportion to character count. With `scene_index` the scene number is
    appended, which is what lets the Short re-time only its own scenes.
    """
    cues, t = [], 0.0
    for s in scenes:
        speech = max(0.2, s["duration"] - s.get("pad", SCENE_PAD))
        cur = t + NARRATION_OFFSET
        sents = split_sentences(s["narration"])
        total_chars = sum(max(1, len(x)) for x in sents)
        for sent in sents:
            share = speech * (max(1, len(sent)) / total_chars)
            cues.append((cur, cur + share, sent, s["i"]) if scene_index
                        else (cur, cur + share, sent))
            cur += share
        t += s["duration"]
    return cues


def write_srt(cues, path: str) -> int:
    with open(path, "w", encoding="utf-8") as f:
        for i, cue in enumerate(cues, 1):
            a, b, txt = cue[0], cue[1], cue[2]
            f.write(f"{i}\n{srt_ts(a)} --> {srt_ts(b)}\n{txt}\n\n")
    return len(cues)


def make_srt(scenes, path: str) -> int:
    return write_srt(caption_cues(scenes), path)


def short_cues(scenes, picked):
    """Cues re-timed onto the Short's own timeline.

    The Short is a concatenation of `picked` scenes, in the order given, so a
    cue's new start is its offset inside its scene plus the total duration of
    the scenes placed before it.
    """
    by_scene: dict = {}
    starts, t = {}, 0.0
    for s in scenes:
        starts[s["i"]] = t
        t += s["duration"]
    for cue in caption_cues(scenes, scene_index=True):
        by_scene.setdefault(cue[3], []).append(cue)

    out, base = [], 0.0
    for idx in picked:
        scene = next((s for s in scenes if s["i"] == idx), None)
        if scene is None:
            continue
        for (a, b, txt, _i) in by_scene.get(idx, []):
            out.append((a - starts[idx] + base, b - starts[idx] + base, txt))
        base += scene["duration"]
    return out


def count_chapters(scenes) -> int:
    """Chapters YouTube will show, including the implicit 0:00 Intro."""
    n = sum(1 for s in scenes if s.get("chapter"))
    return n + 1 if n and not scenes[0].get("chapter") else n


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
            n = os.path.getsize(v)
            # the sidecars are a few KB; "0.00 MB" reads like a failed write
            size = f"{n/1e6:.2f} MB" if n >= 1e6 else f"{n/1024:.0f} KB"
            L.append(f"{k:<14} {os.path.basename(v):<22} {size}")
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
        if artifacts.get("short_captions"):
            L.append("    (captions are already burned in; short_captions.srt is")
            L.append("     the same text as a sidecar if you want toggleable subs)")
    L.append("[ ] Check qc_report.txt says PASS before publishing")
    L.append("")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    return len(chapters)


def write_manifest(path: str, cfg: dict, scenes, opts, artifacts: dict,
                   total: float, lang: str | None, project: str,
                   preview: bool = False, extra: dict | None = None):
    man = {
        "factory_version": VERSION,
        "built_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "project": project,
        "mode": "preview" if preview else "full",
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
            "voice": s.get("voice"),
            "narration_sha256": hashlib.sha256(s["narration"].encode("utf-8")).hexdigest(),
            "narration_chars": len(s["narration"]),
        } for s in scenes],
        "artifacts": {k: {"path": os.path.basename(v),
                          "bytes": os.path.getsize(v)}
                      for k, v in artifacts.items() if v and os.path.exists(v)},
    }
    man.update(extra or {})
    with open(path, "w", encoding="utf-8") as f:
        json.dump(man, f, indent=2)
    return path


# ==========================================================================
# The build
# ==========================================================================

def default_jobs() -> int:
    return max(1, min(4, (os.cpu_count() or 2)))


def build(project: str, shorts=False, preview=False, lang=None, voice=None,
          force=False, jobs: int | None = None, loudnorm: bool = True,
          burn_short_captions: bool = True) -> dict:
    proj, cfg = load_project(project)
    jobs = max(1, jobs or default_jobs())
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
    # advisory, never fatal: a scaffolded episode is meant to be buildable
    # before its script is written, so lint findings are printed, not raised
    issues = validate_config(cfg, proj)
    if issues:
        print(f"  lint  {len(issues)} issue(s) -- run --validate for the list")

    # Preview clips must never share a directory with real ones: a 640x360
    # draft sitting in the final cache would be silently shipped on the next
    # build. The key keeps "final"/"<lang>" stable so existing caches survive.
    variant = lang or "final"
    if preview:
        variant = "preview-" + variant
    audio_dir = os.path.join(proj, "audio", lang) if lang else os.path.join(proj, "audio")
    clip_dir = os.path.join(proj, "clips", variant)
    out_dir = os.path.join(proj, "output", lang) if lang else os.path.join(proj, "output")
    work = os.path.join(proj, "clips", "_work")
    for d in (audio_dir, clip_dir, out_dir, work):
        os.makedirs(d, exist_ok=True)

    ensure_frames(proj, cfg, force=force)
    sfx = ensure_sfx(os.path.join(proj, "audio"))

    # ---- narration + durations ------------------------------------------
    scenes = []
    n_tts = 0
    for i, s in enumerate(cfg["scenes"], 1):
        text = s.get(nkey) or s.get("narration")
        if not text:
            raise BuildError(f"scene {i} has no '{nkey}' text")
        mp3 = os.path.join(audio_dir, f"scene_{i:02d}.mp3")
        # A scene may override the voice and rate. That is what lets a
        # two-character dialogue give each character its own voice instead of
        # one narrator reading both parts. The TTS cache key already includes
        # both, so changing one scene's voice re-synthesizes only that scene.
        scene_voice = s.get("voice") or voice
        scene_rate = s.get("rate") or rate
        if narrate(text, scene_voice, scene_rate, mp3, force=force):
            n_tts += 1
            print(f"  tts   scene {i:02d}"
                  + (f"  ({scene_voice})" if scene_voice != voice else ""))
        # quantize to a whole frame: the clip is encoded as exactly this many
        # frames, so captions and chapters line up with the video instead of
        # drifting a few milliseconds per scene
        dur = round((ffprobe_duration(mp3) + SCENE_PAD) * FPS) / FPS
        sfx_name = s.get("sfx", "whoosh")
        if sfx_name not in VALID_SFX:
            raise BuildError(f"scene {i}: unknown sfx {sfx_name!r} (use {VALID_SFX})")
        scenes.append({
            "i": i, "image": s["image"], "narration": text, "chapter": s.get("chapter"),
            "sfx": sfx_name, "mp3": mp3, "duration": dur, "pad": SCENE_PAD,
            "voice": scene_voice,
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
    joined = os.path.join(work, f"joined_{variant}.mp4")
    concat_clips(clips, joined, work, name=f"list_{variant}")
    total = ffprobe_duration(joined)

    artifacts: dict = {}

    if preview:
        final = os.path.join(out_dir, "preview.mp4")
        shutil.copyfile(joined, final)
        artifacts["preview"] = final
        srt = os.path.join(out_dir, "preview_captions.srt")
        make_srt(scenes, srt)
        artifacts["captions"] = srt
        man = os.path.join(out_dir, "preview_manifest.json")
        write_manifest(man, cfg, scenes, opts, artifacts, total, lang, name,
                       preview=True)
        artifacts["manifest"] = man
        print(f"  DONE  preview {fmt_ts(total)} -> {os.path.relpath(final, proj)}")
        return {"total": total, "artifacts": artifacts, "verdict": "PREVIEW",
                "project": proj, "scenes": scenes}

    # ---- music + loudness ------------------------------------------------
    cfg_path = os.path.join(proj, "video.json")
    final = os.path.join(out_dir, "final.mp4")
    loudnorm = loudnorm and bool(cfg.get("loudness", True))
    bgm = None
    if cfg.get("music", True):
        from engine import music
        bgm = os.path.join(proj, "audio", f"bgm_{int(round(total))}s_"
                                          f"{cfg.get('music_seed', 7)}.wav")
        if force or not os.path.exists(bgm):
            print(f"  music synthesizing {fmt_ts(total)} bed "
                  f"(seed {cfg.get('music_seed', 7)})")
            music.render_bgm(bgm, total, seed=int(cfg.get("music_seed", 7)))
    deps = list(clips) + ([bgm] if bgm else []) + [cfg_path]
    if force or not newer(final, *deps):
        finalize(joined, final, bgm, total,
                 float(cfg.get("bgm_vol", BGM_VOL)), loudnorm)
        print(f"  audio {'music + ' if bgm else ''}"
              f"{'loudness -> ' + str(LOUDNESS_I) + ' LUFS' if loudnorm else 'no loudnorm'}")
    else:
        print("  audio cached")
    artifacts["final"] = final

    # ---- short ----------------------------------------------------------
    short_path, scues = None, None
    if shorts:
        idx = [i for i in (cfg.get("shorts_scenes") or []) if 1 <= i <= len(clips)]
        picks = [clips[i - 1] for i in idx]
        if not picks:
            print("  short SKIPPED (no valid shorts_scenes in video.json)")
        else:
            short_path = os.path.join(out_dir, "short.mp4")
            sdur = sum(scenes[i - 1]["duration"] for i in idx)
            sbgm = None
            if cfg.get("music", True):
                from engine import music
                sbgm = os.path.join(proj, "audio", f"bgm_short_{int(round(sdur))}s_"
                                                   f"{cfg.get('music_seed', 7)}.wav")
                if force or not os.path.exists(sbgm):
                    music.render_bgm(sbgm, sdur + 2, seed=int(cfg.get("music_seed", 7)))
            burn = burn_short_captions and bool(cfg.get("short_captions", True))
            scues = short_cues(scenes, idx) if burn else None
            sdeps = picks + ([sbgm] if sbgm else []) + [cfg_path]
            if force or not newer(short_path, *sdeps):
                make_short(picks, short_path, work, sbgm,
                           float(cfg.get("bgm_vol", BGM_VOL)),
                           cues=scues, loudnorm=loudnorm, tag=variant)
                print(f"  short scenes {idx}"
                      f"{f', {len(scues)} burned-in cues' if scues else ''}"
                      f" -> {os.path.relpath(short_path, proj)}")
            else:
                print("  short cached")
            # the same cues as a sidecar, so the Short can also carry real
            # subtitles for viewers who turn them on
            if scues:
                ssrt = os.path.join(out_dir, "short_captions.srt")
                write_srt(scues, ssrt)
                artifacts["short_captions"] = ssrt
            artifacts["short"] = short_path

    # ---- captions -------------------------------------------------------
    srt = os.path.join(out_dir, "captions.srt")
    n_cues = make_srt(scenes, srt)
    artifacts["captions"] = srt

    # ---- thumbnails -----------------------------------------------------
    from engine import thumbnail
    ta = os.path.join(out_dir, "thumbnail_a.jpg")
    tb = os.path.join(out_dir, "thumbnail_b.jpg")
    # a language variant gets its own thumbnail text when video.json supplies
    # one -- an English hook over a Hindi episode helps nobody
    lc = langs.get(lang, {}) if lang else {}
    thumb_text = lc.get("thumbnail_text") or cfg.get("thumbnail_text") or cfg.get("title", "")
    thumb_prop = lc.get("thumbnail_prop") or cfg.get("thumbnail_prop", "rocket")
    thumb_bg = cfg.get("thumbnail_bg", "land")
    thumb_sky = cfg.get("thumbnail_sky", "day")
    if thumb_prop not in thumbnail.PROPS:
        raise BuildError(f"unknown thumbnail_prop {thumb_prop!r} "
                         f"(use one of {sorted(thumbnail.PROPS)})")
    thumbnail.render_pair(thumb_text, ta, tb, sky=thumb_sky, prop=thumb_prop,
                          bg=thumb_bg)
    artifacts["thumbnail_a"] = ta
    artifacts["thumbnail_b"] = tb

    # ---- QC, then metadata, then manifest ------------------------------
    # QC first so metadata and the manifest can both list qc_report.txt; the
    # manifest last so it records every artifact the build produced.
    from engine import qc
    n_chapters = count_chapters(scenes)
    qc_path = os.path.join(out_dir, "qc_report.txt")
    qc_title = cfg.get("title")
    if lang:
        qc_title = langs.get(lang, {}).get("title", qc_title)
    _, verdict = qc.write_report({
        "title": qc_title, "project": name, "video": final, "lang": lang,
        "scenes": scenes, "total": total, "srt": srt,
        "thumbnails": [ta, tb], "chapters": n_chapters, "short": short_path,
        "short_cues": len(scues) if scues else 0,
        "loudnorm": loudnorm, "target_lufs": LOUDNESS_I,
        "format": cfg.get("format", "explainer"),
    }, qc_path)
    artifacts["qc"] = qc_path

    meta = os.path.join(out_dir, "metadata.txt")
    make_metadata(meta, cfg, scenes, total, lang, artifacts)
    artifacts["metadata"] = meta

    manifest = os.path.join(out_dir, "build_manifest.json")
    write_manifest(manifest, cfg, scenes, opts, artifacts, total, lang, name,
                   extra={"loudnorm": loudnorm,
                          "target_lufs": LOUDNESS_I if loudnorm else None,
                          "short_captions_burned": bool(short_path and scues),
                          "lint_issues": issues})
    artifacts["manifest"] = manifest

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
        line("libmp3lame" in enc, "libmp3lame", "needed by tests/smoke.py")
        filt = subprocess.run(["ffmpeg", "-hide_banner", "-filters"],
                              capture_output=True, text=True).stdout
        line("loudnorm" in filt, "loudnorm", f"EBU R128 -> {LOUDNESS_I} LUFS")
        line("overlay" in filt, "overlay", "burns captions into the Short")
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
    # the tally, or "empty" -- the parenthesis matters: without it the leading
    # two spaces made the whole expression truthy and "empty" never printed
    print("  " + ("  ".join(f"{k}: {v}" for k, v in sorted(counts.items())) or "empty"))
    print()
    return eps


def season_targets(include_all: bool = False):
    """Slugs `--all` should act on: the 'ready' episodes, or every project."""
    eps = load_season().get("episodes", [])
    if not eps:
        return list_projects(), False
    if include_all:
        return [e["slug"] for e in eps], True
    return [e["slug"] for e in eps if e.get("status") == "ready"], True


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
                      jobs=args.jobs, loudnorm=not args.no_loudnorm,
                      burn_short_captions=not args.no_short_captions)
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
    ap.add_argument("--validate", action="store_true",
                    help="lint video.json and exit -- no build")
    ap.add_argument("--clean", action="store_true",
                    help="delete rebuildable caches (clips/, music beds); "
                         "keeps narration and output/")
    ap.add_argument("--force", action="store_true", help="ignore caches and rebuild")
    ap.add_argument("--jobs", type=int, metavar="N",
                    help=f"parallel scene encodes (default {default_jobs()})")
    ap.add_argument("--no-loudnorm", action="store_true",
                    help=f"skip EBU R128 normalization to {LOUDNESS_I} LUFS")
    ap.add_argument("--no-short-captions", action="store_true",
                    help="do not burn caption cards into the Short")
    ap.add_argument("--version", action="version", version=f"factory {VERSION}")
    args = ap.parse_args(argv)

    if args.check:
        return preflight()
    if args.season:
        season_table()
        return 0

    def targets():
        if args.project:
            return [args.project]
        slugs, _ = season_targets(include_all=True)
        return [os.path.join(HERE, "projects", s) for s in slugs]

    if args.validate:
        return cmd_validate(targets())
    if args.clean:
        # deleting one episode's clips costs minutes to rebuild; deleting the
        # whole season's costs half an hour, so that one has to be asked for
        if not args.project and not args.all:
            print("  --clean needs a project path, or --all to clean every "
                  "episode in season.json")
            return 2
        return cmd_clean(targets())
    if args.all:
        return build_all(args)
    if not args.project:
        ap.print_help()
        return 2

    t0 = time.time()
    try:
        build(args.project, shorts=args.shorts, preview=args.preview,
              lang=args.lang, voice=args.voice, force=args.force,
              jobs=args.jobs, loudnorm=not args.no_loudnorm,
              burn_short_captions=not args.no_short_captions)
    except BuildError as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        return 1
    print(f"  built in {time.time() - t0:.1f}s\n")
    return 0          # QC is advisory: it reports, the owner decides


if __name__ == "__main__":
    sys.exit(main())
