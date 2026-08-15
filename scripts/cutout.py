#!/usr/bin/env python3
"""Turn a flat-background character image into a trimmed transparent sprite.

Chat image tools will happily draw a character on a plain background but rarely
hand back real transparency, and the good matting libraries (rembg and friends)
drag in a compiler toolchain that does not build here. This does the job with
nothing but Pillow, which is already a dependency.

    python3 scripts/cutout.py in.png assets/sprites/goofy/talk.png

The background is removed by flooding inward from the edges, NOT by deleting
every pixel that matches the background colour. That distinction is the whole
point: Woofy has a white blaze and a white chest, and a plain colour-match would
punch holes straight through him. Flooding only reaches white that is connected
to the border.

Options:
  --thresh N   colour tolerance, 0-255 (default 32). Raise it for a gradient or
               a slightly noisy background; lower it if edges of the character
               are being eaten.
  --pad N      transparent margin left around the trimmed result (default 8).
  --max-height N
               downscale so the result is at most N pixels tall (default 1000).
               Sprites are drawn at 360 logical units times the scene's scale on
               a canvas supersampled by 2, so ~830px is the largest they ever
               render at; storing much more than that in git buys nothing.
  --check      report the result instead of writing: size, and how much of the
               frame survived. A cutout that keeps ~100% means the flood found
               no background and nothing was removed.
"""
import argparse
import os
import sys

from PIL import Image, ImageDraw

SENTINEL = (1, 2, 3)


def cutout(src: Image.Image, thresh: int = 32, pad: int = 8,
           max_height: int = 0):
    """Returns (sprite, kept) where `kept` is the fraction of the original frame
    the subject occupied. Measured before any downscale or padding, so the
    number means "how much survived the key" and nothing else."""
    rgb = src.convert("RGB")
    w, h = rgb.size

    # Seed from a ring of points along every edge rather than the four corners
    # alone: a character that touches one side still leaves the other three
    # reachable, and a vignetted backdrop needs more than one seed to clear.
    seeds = []
    for i in range(0, w, max(1, w // 24)):
        seeds += [(i, 0), (i, h - 1)]
    for j in range(0, h, max(1, h // 24)):
        seeds += [(0, j), (w - 1, j)]

    work = rgb.copy()
    for xy in seeds:
        if work.getpixel(xy) == SENTINEL:
            continue                       # already flooded from another seed
        ImageDraw.floodfill(work, xy, SENTINEL, thresh=thresh)

    flooded = work.load()
    out = src.convert("RGBA")
    px = out.load()
    for y in range(h):
        for x in range(w):
            if flooded[x, y] == SENTINEL:
                px[x, y] = (0, 0, 0, 0)

    # Histogram of the alpha channel: same answer as walking every pixel,
    # without the deprecated getdata() and much faster.
    alpha_hist = out.getchannel("A").histogram()
    kept = sum(alpha_hist[9:]) / float(w * h)

    box = out.getbbox()                    # tight crop around what survived
    if box:
        out = out.crop(box)
    if max_height and out.height > max_height:
        w = max(1, round(out.width * max_height / out.height))
        out = out.resize((w, max_height), Image.LANCZOS)
    if pad:
        padded = Image.new("RGBA", (out.width + pad * 2, out.height + pad * 2), (0, 0, 0, 0))
        padded.alpha_composite(out, (pad, pad))
        out = padded
    return out, kept


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src")
    ap.add_argument("dst", nargs="?")
    ap.add_argument("--thresh", type=int, default=32)
    ap.add_argument("--pad", type=int, default=8)
    ap.add_argument("--max-height", type=int, default=1000)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()

    src = Image.open(a.src)
    out, kept_frac = cutout(src, thresh=a.thresh, pad=a.pad, max_height=a.max_height)
    kept = 100.0 * kept_frac
    print(f"{os.path.basename(a.src)}: {src.size} -> {out.size}, {kept:.1f}% of the frame kept")
    if kept > 95:
        print("  WARNING: almost nothing was removed. The background is probably not "
              "flat enough — try a higher --thresh, or regenerate on a plain colour.")
    if kept < 5:
        print("  WARNING: almost everything was removed. --thresh is likely too high.")

    if a.check:
        return 0
    if not a.dst:
        ap.error("give a destination path, or pass --check")
    os.makedirs(os.path.dirname(os.path.abspath(a.dst)), exist_ok=True)
    out.save(a.dst, "PNG", optimize=True)
    print(f"  wrote {a.dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
