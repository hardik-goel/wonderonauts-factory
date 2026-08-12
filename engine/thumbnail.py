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


def _fit(d, text: str, size: int, max_w: float) -> int:
    """Largest size <= `size` whose widest line fits in max_w."""
    while size > 40:
        f = tk.font(size, unicode_wide=any(ord(c) > 0x2FF for c in text))
        bb = d.multiline_textbbox((0, 0), text, font=f)
        if bb[2] - bb[0] <= max_w:
            break
        size = int(size * 0.94)
    return size


def _lines(text: str):
    return [ln for ln in (text or "WONDER\nO-NAUTS").split("\n") if ln.strip()]


# The mascot is the rocket, but a thumbnail sells better when it shows the
# episode's actual subject. `thumbnail_prop` in video.json picks the hero.
#
# Every drawable hero lives in PROPS. factory.py validates `thumbnail_prop`
# against it, because the old `else: rocket` fallback meant a typo -- or a prop
# the toolkit had grown but this module had not -- shipped a rocket on a rain
# episode and nobody noticed until the thumbnail was already live.
PROPS = {
    "rocket":      lambda d, x, y, s: tk.rocket(d, x, y, s, face=True),
    "plane":       lambda d, x, y, s: tk.plane(d, x, y - 120 * s, 0.66 * s),
    "paper_plane": lambda d, x, y, s: tk.paper_plane(d, x, y - 130 * s, 1.5 * s),
    "sun":         lambda d, x, y, s: tk.sun(d, x, y - 150 * s, 150 * s),
    "molecule":    lambda d, x, y, s: tk.molecule(d, x, y - 150 * s, 130 * s),
    "planet":      lambda d, x, y, s: tk.planet(d, x, y - 150 * s, 155 * s, face=True),
    "raindrop":    lambda d, x, y, s: tk.raindrop(d, x, y - 150 * s, 150 * s),
    "prism":       lambda d, x, y, s: tk.prism(d, x, y - 150 * s, 320 * s),
    "cloud":       lambda d, x, y, s: tk.cloud(d, x, y - 170 * s, 1.3 * s),
    "airfoil":     lambda d, x, y, s: tk.airfoil(d, x, y - 150 * s, 1.1 * s),
    "kid":         lambda d, x, y, s: tk.kid(d, x, y + 150 * s, 1.15 * s,
                                             arms="one_up", mouth="o"),
    "salt_crystal": lambda d, x, y, s: tk.salt_crystal(d, x, y - 160 * s, 240 * s),
    "wave":        lambda d, x, y, s: tk.wave(d, x, y - 60 * s, 620 * s, 1.0 * s),
    "mountain":    lambda d, x, y, s: tk.mountain(d, x, y + 60 * s, 520 * s, 420 * s),
    # story cast: a fable thumbnail with a rocket on it is the wrong video
    "hare":        lambda d, x, y, s: tk.hare(d, x, y + 150 * s, 1.15 * s,
                                              running=True, ears="back"),
    "tortoise":    lambda d, x, y, s: tk.tortoise(d, x, y + 150 * s, 1.25 * s),
    "dog":         lambda d, x, y, s: tk.dog(d, x, y + 150 * s, 1.15 * s,
                                             expression="laugh", speaking=True),
}


def _prop(d, kind: str, x: int, y: int, scale: float):
    PROPS.get(kind, PROPS["rocket"])(d, x, y, scale)


# The lower third of the thumbnail. Green hills under an ocean episode reads as
# the wrong video before anyone has read the title, and the thumbnail is the
# single biggest click-through lever there is.
BACKDROPS = ("land", "sea", "none")


def _backdrop(d, kind: str, y: int):
    if kind == "sea":
        tk.sea(d, y)
    elif kind != "none":
        tk.ground(d, y)


def variant_a(text: str, sky: str = "day", prop: str = "rocket",
              bg: str = "land") -> Image.Image:
    """Text dominant: the title fills the frame, mascot stays small."""
    img, d = tk.canvas(sky)
    tk.sun(d, 190, 165, 118, rotate=8)
    tk.cloud(d, 1660, 200, 0.72)
    tk.cloud(d, 300, 640, 0.55)
    _backdrop(d, bg, 900)

    lines = _lines(text)
    lead, punch = lines[:-1], lines[-1].strip()
    tk.title_text(d, (900, 128), "WONDER-O-NAUTS", 76, fill=P["accent"], stroke=12)
    if lead:
        lead_txt = "\n".join(lead)
        tk.title_text(d, (900, 360), lead_txt, _fit(d, lead_txt, 116, 1560),
                      fill=P["white"], stroke=15)
    # the last line is the hook -- it gets the size and the accent color
    tk.title_text(d, (900, 620), punch,
                  _fit(d, punch, 230 if len(punch) <= 8 else 170, 1500),
                  fill=P["accent"], stroke=22)
    _prop(d, prop, 1660, 760, 0.85)
    return tk.vignette(img, 0.20)


def variant_b(text: str, sky: str = "day", prop: str = "rocket",
              bg: str = "land") -> Image.Image:
    """Character dominant: big kid + the episode's prop, one short line."""
    img, d = tk.canvas(sky)
    tk.sun(d, 1740, 160, 110, rotate=20)
    tk.cloud(d, 520, 190, 0.85)
    _backdrop(d, bg, 860)

    lines = _lines(text)
    punch = lines[-1].strip().upper()
    lead = " ".join(lines[:-1]).strip() or "WONDER-O-NAUTS"

    tk.kid(d, 470, 1070, scale=1.5, arms="up", mouth="o", looking="up")
    _prop(d, prop, 1660, 780, 1.05)
    tk.title_text(d, (1080, 150), lead, _fit(d, lead, 76, 1180),
                  fill=P["white"], stroke=13)
    tk.speech_pop(d, 1140, 420, punch, _fit(d, punch, 170, 1080),
                  fill=P["accent"], text_fill=P["text_dark"])
    return tk.vignette(img, 0.20)


def render_pair(text: str, out_a: str, out_b: str, sky: str = "day",
                prop: str = "rocket", bg: str = "land"):
    """Write both variants; returns (path_a, path_b)."""
    return (_finish(variant_a(text, sky, prop, bg), out_a),
            _finish(variant_b(text, sky, prop, bg), out_b))


if __name__ == "__main__":
    import sys

    txt = sys.argv[1] if len(sys.argv) > 1 else "Why is the sky\nBLUE?"
    a, b = render_pair(txt, "thumbnail_a.jpg", "thumbnail_b.jpg")
    for p in (a, b):
        print(f"  {p}  {os.path.getsize(p)/1024:.0f} KB")
