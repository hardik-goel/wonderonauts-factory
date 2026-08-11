"""
Post-build QC report.

The owner's "review" step should take two minutes, not ten. After every full
build factory.py hands this module the facts it already measured; the report
turns them into a PASS / WARN verdict with reasons at the very top.

Nothing here re-renders anything -- it only measures and judges.
"""

from __future__ import annotations

import os
import re
import subprocess

# Thresholds. Kids' narration sits comfortably around 130-150 wpm.
# These are calibrated for English; for other languages the pacing is reported
# but not flagged, because a word count means something different per language.
WPM_MIN, WPM_MAX = 110, 175
WPM_LANGS = ("en",)
RUNTIME_MIN, RUNTIME_MAX = 120, 900          # seconds
MEAN_DB_MIN = -30.0
MAX_DB_MAX = -1.0

# EBU R128 integrated loudness. YouTube plays back at about -14 LUFS and only
# ever turns loud uploads DOWN, so anything materially quieter than this just
# sounds quiet to the viewer forever. The window is deliberately loose: the
# point is to catch a build that skipped normalization, not to police 0.3 LU.
LUFS_TARGET = -14.0
LUFS_TOLERANCE = 2.0


def measure_lufs(path: str):
    """(integrated LUFS, true peak dBTP) via ebur128; (None, None) if it fails."""
    try:
        p = subprocess.run(
            ["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-vn",
             "-af", "ebur128=peak=true", "-f", "null", "-"],
            capture_output=True, text=True, timeout=1800)
    except Exception:
        return None, None
    err = p.stderr or ""
    # the Summary block at the end is the integrated figure for the whole file
    tail = err[err.rfind("Summary:"):] if "Summary:" in err else ""
    i = re.search(r"I:\s*(-?\d+(?:\.\d+)?)\s*LUFS", tail)
    tp = re.search(r"Peak:\s*(-?\d+(?:\.\d+)?)\s*dBFS", tail)
    return (float(i.group(1)) if i else None,
            float(tp.group(1)) if tp else None)


def measure_loudness(path: str):
    """(mean_db, max_db) via ffmpeg volumedetect; (None, None) if unavailable."""
    try:
        p = subprocess.run(
            ["ffmpeg", "-hide_banner", "-nostats", "-i", path,
             "-af", "volumedetect", "-f", "null", "-"],
            capture_output=True, text=True, timeout=600)
    except Exception:
        return None, None
    err = p.stderr or ""
    mean = re.search(r"mean_volume:\s*(-?\d+(?:\.\d+)?) dB", err)
    peak = re.search(r"max_volume:\s*(-?\d+(?:\.\d+)?) dB", err)
    return (float(mean.group(1)) if mean else None,
            float(peak.group(1)) if peak else None)


def has_streams(path: str):
    """(has_video, has_audio) -- a silent render is the one defect a human
    reviewer is most likely to miss until it is already published."""
    try:
        p = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type",
             "-of", "default=nw=1:nk=1", path],
            capture_output=True, text=True, timeout=120)
    except Exception:
        return None, None
    kinds = p.stdout.split()
    return "video" in kinds, "audio" in kinds


def _srt_cue_scenes(srt_path: str, scene_bounds):
    """How many scenes have at least one caption cue inside them."""
    if not os.path.exists(srt_path):
        return 0
    with open(srt_path, encoding="utf-8") as f:
        body = f.read()
    starts = []
    for m in re.finditer(r"(\d\d):(\d\d):(\d\d),(\d\d\d) -->", body):
        h, mi, s, ms = (int(g) for g in m.groups())
        starts.append(h * 3600 + mi * 60 + s + ms / 1000.0)
    covered = 0
    for a, b in scene_bounds:
        if any(a - 0.05 <= t < b + 0.05 for t in starts):
            covered += 1
    return covered


def _fmt_ts(sec: float) -> str:
    return f"{int(sec // 60)}:{int(sec % 60):02d}"


def build_report(ctx: dict) -> tuple[str, str]:
    """Render the report text. ctx keys:

    title, project, video (path), scenes [{i, duration, narration, chapter}],
    total, srt, thumbnails [paths], chapters (int), short (path or None),
    manifest (path)

    Returns (report_text, verdict) where verdict is "PASS" or "WARN".
    """
    warns: list[str] = []
    scenes = ctx["scenes"]
    total = float(ctx["total"])
    lang = (ctx.get("lang") or "en").split("-")[0]
    judge_wpm = lang in WPM_LANGS

    rows = []
    for s in scenes:
        words = len(re.findall(r"[\w'’\-]+", s["narration"]))
        speech = max(0.01, s["duration"] - s.get("pad", 0.7))
        wpm = words / speech * 60.0
        flag = ""
        if wpm < WPM_MIN:
            flag = "SLOW"
        elif wpm > WPM_MAX:
            flag = "FAST"
        if flag and judge_wpm:
            warns.append(f"scene {s['i']:02d} narration is "
                         f"{'slow' if flag == 'SLOW' else 'fast'} ({wpm:.0f} wpm)")
        elif flag:
            flag = flag.lower()          # reported, not enforced
        rows.append((s["i"], s["duration"], words, wpm, flag, s.get("chapter", "")))

    if total < RUNTIME_MIN:
        warns.append(f"runtime {_fmt_ts(total)} is under {RUNTIME_MIN//60} min")
    if total > RUNTIME_MAX:
        warns.append(f"runtime {_fmt_ts(total)} is over {RUNTIME_MAX//60} min")

    has_v, has_a = has_streams(ctx["video"])
    if has_v is False:
        warns.append("final video has no video stream")
    if has_a is False:
        warns.append("final video has NO AUDIO STREAM")

    mean_db, max_db = measure_loudness(ctx["video"])
    if mean_db is None:
        warns.append("could not measure loudness (ffmpeg volumedetect failed)")
    else:
        if mean_db < MEAN_DB_MIN:
            warns.append(f"mean volume {mean_db:.1f} dB is quiet (below {MEAN_DB_MIN} dB)")
        if max_db is not None and max_db > MAX_DB_MAX:
            warns.append(f"peak volume {max_db:.1f} dB risks clipping (above {MAX_DB_MAX} dB)")

    # the loudness that actually decides how loud this sounds on YouTube
    target = float(ctx.get("target_lufs", LUFS_TARGET))
    lufs, true_peak = (measure_lufs(ctx["video"]) if ctx.get("loudnorm")
                       else (None, None))
    if ctx.get("loudnorm"):
        if lufs is None:
            warns.append("could not measure integrated loudness (ebur128 unavailable)")
        elif abs(lufs - target) > LUFS_TOLERANCE:
            warns.append(f"integrated loudness {lufs:.1f} LUFS is more than "
                         f"{LUFS_TOLERANCE} LU from the {target} LUFS target")
        if true_peak is not None and true_peak > 0.0:
            warns.append(f"true peak {true_peak:.1f} dBTP is above 0 -- will clip "
                         "after transcoding")

    bounds, t = [], 0.0
    for s in scenes:
        bounds.append((t, t + s["duration"]))
        t += s["duration"]
    covered = _srt_cue_scenes(ctx["srt"], bounds)
    if covered < len(scenes):
        warns.append(f"caption coverage {covered}/{len(scenes)} scenes")

    thumbs = [p for p in ctx.get("thumbnails", []) if os.path.exists(p)]
    if len(thumbs) < 2:
        warns.append(f"only {len(thumbs)}/2 thumbnail variants written")
    for p in thumbs:
        if os.path.getsize(p) > 2_000_000:
            warns.append(f"{os.path.basename(p)} exceeds YouTube's 2MB limit")
        try:
            from PIL import Image
            with Image.open(p) as im:
                if im.size != (1280, 720):
                    warns.append(f"{os.path.basename(p)} is {im.size[0]}x{im.size[1]}, "
                                 "not 1280x720")
        except Exception:
            warns.append(f"could not read {os.path.basename(p)}")

    if ctx.get("chapters", 0) and ctx["chapters"] < 3:
        warns.append("fewer than 3 chapters -- YouTube needs 3+ to show them")

    verdict = "PASS" if not warns else "WARN"

    L = []
    L.append("=" * 68)
    L.append(f"  QC {verdict}   {ctx.get('title', ctx.get('project', ''))}")
    L.append("=" * 68)
    if warns:
        for w in warns:
            L.append(f"  ! {w}")
    else:
        L.append("  No issues found. Ready to upload.")
    L.append("")
    L.append(f"project      {ctx.get('project', '')}")
    L.append(f"video        {os.path.basename(ctx['video'])}"
             f"  ({os.path.getsize(ctx['video'])/1e6:.1f} MB)"
             if os.path.exists(ctx["video"]) else "video        MISSING")
    L.append(f"runtime      {_fmt_ts(total)}  ({total:.1f}s)")
    def yn(v):
        return "yes" if v else ("?" if v is None else "NO")

    L.append(f"streams      video={yn(has_v)}  audio={yn(has_a)}")
    if mean_db is not None:
        L.append(f"loudness     mean {mean_db:.1f} dB / peak {max_db:.1f} dB")
    if lufs is not None:
        L.append(f"programme    {lufs:.1f} LUFS integrated"
                 + (f" / {true_peak:.1f} dBTP true peak" if true_peak is not None else "")
                 + f"   (target {target} LUFS)")
    elif not ctx.get("loudnorm"):
        L.append("programme    loudness normalization was disabled for this build")
    L.append(f"captions     {covered}/{len(scenes)} scenes covered  "
             f"({os.path.basename(ctx['srt'])})")
    L.append(f"chapters     {ctx.get('chapters', 0)}")
    L.append(f"thumbnails   {len(thumbs)}/2  " +
             ", ".join(f"{os.path.basename(p)} {os.path.getsize(p)//1024}KB" for p in thumbs))
    if ctx.get("short"):
        L.append(f"short        {os.path.basename(ctx['short'])}"
                 + (f"  ({os.path.getsize(ctx['short'])/1e6:.1f} MB)"
                    if os.path.exists(ctx["short"]) else "  MISSING")
                 + (f", {ctx['short_cues']} burned-in caption cues"
                    if ctx.get("short_cues") else ", NO burned-in captions"))
    L.append("")
    L.append(f"{'#':>3}  {'dur':>7}  {'words':>6}  {'wpm':>6}  {'flag':<5} chapter")
    L.append("-" * 68)
    for i, dur, words, wpm, flag, chap in rows:
        L.append(f"{i:>3}  {dur:>6.2f}s  {words:>6}  {wpm:>6.0f}  {flag:<5} {chap}")
    L.append("-" * 68)
    L.append(f"     {total:>6.2f}s  {sum(r[2] for r in rows):>6}"
             f"  {sum(r[2] for r in rows) / max(0.01, total) * 60:>6.0f}")
    L.append("")
    if not judge_wpm:
        L.append(f"note: the {WPM_MIN}-{WPM_MAX} wpm window is calibrated for "
                 f"English, so it is reported but not enforced for '{lang}'")
        L.append("")
    L.append("Reminders:")
    L.append("  * set 'Made for Kids' = YES on upload (COPPA)")
    L.append("  * A/B the two thumbnails with YouTube Test & Compare")
    L.append("  * paste chapter timestamps from metadata.txt into the description")
    L.append("")
    return "\n".join(L), verdict


def write_report(ctx: dict, path: str) -> tuple[str, str]:
    text, verdict = build_report(ctx)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path, verdict
