"""
A/B thumbnail generator.

Two compositions per episode, both 1280x720 and well under 2MB:

    variant A -- text dominant:      huge title, small mascot
    variant B -- character dominant: big kid + rocket, short punchy text

Both are drawn with the same toolkit primitives as the episode itself, so the
thumbnail always looks like the video it belongs to. Test them against each
other with YouTube's built-in "Test & Compare".
"""

from __future__ import annotations

import os

from PIL import Image

from . import toolkit as tk

TW, TH = 1280, 720
P = tk.PALETTE


def _finish(img: Image.Image, path: str, quality: int = 90) -> str:
    d = os.path.dirname(os.path.abspath(path))
    if d:
        os.makedirs(d, exist_ok=True)
    out = img.resize((TW, TH), Image.LANCZOS)
    out.save(path, "JPEG", quality=quality, optimize=True, progressive=True)
    # 2MB ceiling is a hard YouTube limit -- step the quality down if needed
    q = quality
    while os.path.getsize(path) > 2_000_000 and q > 55:
        q -= 8
        out.save(path, "JPEG", quality=q, optimize=True, progressive=True)
    return path


def _lines(text: str):
    return [ln for ln in (text or "WONDER\nO-NAUTS").split("\n") if ln.strip()]


# The mascot is the rocket, but a thumbnail sells better when it shows the
# episode's actual subject. `thumbnail_prop` in video.json picks the hero.
def _prop(d, kind: str, x: int, y: int, scale: float):
    if kind == "plane":
        tk.plane(d, x, y - 120 * scale, 0.66 * scale)
    elif kind == "paper_plane":
        tk.paper_plane(d, x, y - 130 * scale, 1.5 * scale)
    elif kind == "sun":
        tk.sun(d, x, y - 150 * scale, 150 * scale)
    elif kind == "molecule":
        tk.molecule(d, x, y - 150 * scale, 130 * scale)
    else:
        tk.rocket(d, x, y, scale, face=True)


def variant_a(text: str, sky: str = "day", prop: str = "rocket") -> Image.Image:
    """Text dominant: the title fills the frame, mascot stays small."""
    img, d = tk.canvas(sky)
    tk.sun(d, 190, 165, 118, rotate=8)
    tk.cloud(d, 1660, 200, 0.72)
    tk.cloud(d, 300, 640, 0.55)
    tk.ground(d, 900)

    lines = _lines(text)
    lead, punch = lines[:-1], lines[-1].strip()
    tk.title_text(d, (900, 128), "WONDER-O-NAUTS", 76, fill=P["accent"], stroke=12)
    if lead:
        tk.title_text(d, (900, 360), "\n".join(lead), 116, fill=P["white"], stroke=15)
    # the last line is the hook -- it gets the size and the accent color
    tk.title_text(d, (900, 620), punch,
                  230 if len(punch) <= 8 else 160, fill=P["accent"], stroke=22)
    _prop(d, prop, 1660, 760, 0.85)
    return tk.vignette(img, 0.20)


def variant_b(text: str, sky: str = "day", prop: str = "rocket") -> Image.Image:
    """Character dominant: big kid + the episode's prop, one short line."""
    img, d = tk.canvas(sky)
    tk.sun(d, 1740, 160, 110, rotate=20)
    tk.cloud(d, 520, 190, 0.85)
    tk.ground(d, 860)

    lines = _lines(text)
    punch = lines[-1].strip().upper()
    lead = " ".join(lines[:-1]).strip() or "WONDER-O-NAUTS"

    tk.kid(d, 470, 1070, scale=1.5, arms="up", mouth="o", looking="up")
    _prop(d, prop, 1660, 780, 1.05)
    tk.title_text(d, (1080, 150), lead, 76, fill=P["white"], stroke=13)
    tk.speech_pop(d, 1140, 420, punch, 170, fill=P["accent"], text_fill=P["text_dark"])
    return tk.vignette(img, 0.20)


def render_pair(text: str, out_a: str, out_b: str, sky: str = "day",
                prop: str = "rocket"):
    """Write both variants; returns (path_a, path_b)."""
    return (_finish(variant_a(text, sky, prop), out_a),
            _finish(variant_b(text, sky, prop), out_b))


if __name__ == "__main__":
    import sys

    txt = sys.argv[1] if len(sys.argv) > 1 else "Why is the sky\nBLUE?"
    a, b = render_pair(txt, "thumbnail_a.jpg", "thumbnail_b.jpg")
    for p in (a, b):
        print(f"  {p}  {os.path.getsize(p)/1024:.0f} KB")
