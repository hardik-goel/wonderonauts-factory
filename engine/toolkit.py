"""
Wonder-o-nauts cartoon component library.

Flat-design, kid-friendly primitives on a 1920x1080 logical canvas. Every
episode's render_scenes.py builds its frames exclusively out of these calls --
new primitives are added HERE, never inline in an episode, so the channel keeps
one visual identity.

Everything is drawn from code with Pillow. Nothing is downloaded, sampled or
traced from existing art.

Coordinates are always given in logical 1920x1080 space. Internally the canvas
is rendered at SS times that size and downsampled on save(), which is what gives
the shapes their clean anti-aliased edges.

Typical use:

    from engine import toolkit as tk

    img, d = tk.canvas("day")
    tk.sun(d, 300, 220, 130)
    tk.kid(d, 960, 700, scale=1.0, arms="up")
    tk.title_text(d, (960, 140), "Why is the sky BLUE?", 110)
    tk.save(img, "frames/scene_01.png")
"""

from __future__ import annotations

import math
import os
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont

# --------------------------------------------------------------------------
# Canvas constants
# --------------------------------------------------------------------------

W, H = 1920, 1080          # logical canvas size (all coordinates use this)
SS = 2                     # supersampling factor for anti-aliasing

# The factory's Ken Burns move zooms in slowly (0.004/sec, capped at 1.25x), so
# by the end of a ~20s scene roughly 4% of each edge has been cropped away.
# Keep every piece of text inside SAFE or it will be shaved off on screen.
SAFE = (120, 80, 1800, 1000)   # x0, y0, x1, y1

_scale = SS                # current canvas scale, set by canvas()

# Bounding boxes of everything "important" drawn on the current canvas (text,
# characters, badges). Backgrounds deliberately do not register. This is what
# lets a scene prove it respects the end-screen safe zone instead of just
# claiming to -- see safe_zone_violations().
_boxes: list = []


# --------------------------------------------------------------------------
# Palette -- the channel's colors. Reuse these; do not invent new ones per
# episode or the look drifts.
# --------------------------------------------------------------------------

PALETTE = {
    "sky_top": (56, 138, 230),
    "sky_bottom": (168, 220, 252),
    "sky_night_top": (12, 18, 58),
    "sky_night_bottom": (52, 66, 130),
    "sunset_top": (58, 92, 176),
    "sunset_mid": (243, 138, 92),
    "sunset_bottom": (253, 205, 118),
    "grass": (108, 196, 108),
    "grass_dark": (78, 166, 88),
    "cloud": (255, 255, 255),
    "cloud_shade": (226, 238, 250),
    "sun": (255, 208, 64),
    "sun_deep": (250, 168, 40),
    "rocket": (240, 244, 250),
    "rocket_red": (238, 82, 83),
    "rocket_dark": (206, 60, 62),
    "window": (126, 214, 244),
    "window_rim": (255, 255, 255),
    "flame": (255, 168, 46),
    "flame_hot": (255, 226, 120),
    "skin": (255, 205, 168),
    "skin_dark": (226, 168, 132),
    "hair": (74, 54, 46),
    "shirt": (108, 92, 231),
    "pants": (52, 90, 160),
    "shoe": (58, 62, 78),
    "ink": (44, 48, 66),
    "white": (255, 255, 255),
    "molecule": (146, 214, 255),
    "molecule_dark": (96, 176, 232),
    "blue_ray": (72, 148, 255),
    "red_ray": (240, 84, 84),
    "star": (255, 244, 196),
    "text": (255, 255, 255),
    "text_dark": (36, 40, 58),
    "banner": (36, 40, 58),
    "accent": (255, 210, 64),
    "prism_glass": (206, 240, 255),
}

RAINBOW = [
    (233, 62, 58),    # red
    (243, 144, 63),   # orange
    (247, 209, 61),   # yellow
    (105, 196, 96),   # green
    (72, 148, 255),   # blue
    (86, 82, 200),    # indigo
    (148, 84, 206),   # violet
]

RAINBOW_NAMES = ["red", "orange", "yellow", "green", "blue", "indigo", "violet"]


# --------------------------------------------------------------------------
# Fonts -- Poppins Bold if the owner drops it in fonts/, DejaVu / system bold
# otherwise. Never downloaded at runtime.
# --------------------------------------------------------------------------

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)

_FONT_CANDIDATES = [
    os.path.join(_REPO, "fonts", "Poppins-Bold.ttf"),
    os.path.join(_REPO, "fonts", "Poppins-SemiBold.ttf"),
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
    "/usr/local/share/fonts/DejaVuSans-Bold.ttf",
    "/Library/Fonts/Poppins-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "C:/Windows/Fonts/poppins-bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/segoeuib.ttf",
]

# Unicode-wide fallbacks, needed for language variants (e.g. Devanagari).
_FONT_UNICODE_CANDIDATES = [
    os.path.join(_REPO, "fonts", "NotoSans-Bold.ttf"),
    "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "C:/Windows/Fonts/arialuni.ttf",
    "C:/Windows/Fonts/mangal.ttf",
]

_font_cache: dict = {}


def font_path(unicode_wide: bool = False) -> str | None:
    """First usable bold font on this machine, or None for Pillow's default."""
    cands = (_FONT_UNICODE_CANDIDATES if unicode_wide else []) + _FONT_CANDIDATES
    for p in cands:
        if os.path.exists(p):
            return p
    return None


def font(size: int, unicode_wide: bool = False):
    """Bold display font at a *logical* size (scaled to the canvas internally)."""
    px = max(6, int(round(size * _scale)))
    key = (px, unicode_wide)
    if key in _font_cache:
        return _font_cache[key]
    path = font_path(unicode_wide)
    f = None
    if path:
        try:
            f = ImageFont.truetype(path, px)
        except Exception:
            f = None
    if f is None:
        try:
            f = ImageFont.load_default(size=px)   # Pillow >= 10.1: scalable
        except TypeError:
            f = ImageFont.load_default()
    _font_cache[key] = f
    return f


# --------------------------------------------------------------------------
# Scaled draw proxy -- primitives speak logical coordinates, pixels happen here
# --------------------------------------------------------------------------

_SCALED_KW = ("width", "radius", "stroke_width", "outline_width")


class ScaledDraw:
    """ImageDraw wrapper that multiplies logical coordinates by the SS factor."""

    def __init__(self, draw: ImageDraw.ImageDraw, scale: int):
        self._d = draw
        self.s = scale

    # -- helpers ---------------------------------------------------------
    def _pt(self, xy):
        s = self.s
        if isinstance(xy, (int, float)):
            return xy * s
        if len(xy) and isinstance(xy[0], (list, tuple)):
            return [(x * s, y * s) for (x, y) in xy]
        return [v * s for v in xy]

    def _kw(self, kw):
        out = dict(kw)
        for k in _SCALED_KW:
            if k in out and isinstance(out[k], (int, float)):
                out[k] = max(1, int(round(out[k] * self.s))) if out[k] else out[k]
        return out

    def _fwd(self, name, xy, kw):
        getattr(self._d, name)(self._pt(xy), **self._kw(kw))

    # -- shapes ----------------------------------------------------------
    def ellipse(self, xy, **kw):
        self._fwd("ellipse", xy, kw)

    def rectangle(self, xy, **kw):
        self._fwd("rectangle", xy, kw)

    def rounded_rectangle(self, xy, **kw):
        self._fwd("rounded_rectangle", xy, kw)

    def polygon(self, xy, **kw):
        self._fwd("polygon", xy, kw)

    def line(self, xy, **kw):
        self._fwd("line", xy, kw)

    def arc(self, xy, start, end, **kw):
        self._d.arc(self._pt(xy), start, end, **self._kw(kw))

    def chord(self, xy, start, end, **kw):
        self._d.chord(self._pt(xy), start, end, **self._kw(kw))

    def pieslice(self, xy, start, end, **kw):
        self._d.pieslice(self._pt(xy), start, end, **self._kw(kw))

    # -- text ------------------------------------------------------------
    def text(self, xy, txt, **kw):
        self._d.text(self._pt(xy), txt, **self._kw(kw))

    def multiline_text(self, xy, txt, **kw):
        self._d.multiline_text(self._pt(xy), txt, **self._kw(kw))

    def textbbox(self, xy, txt, **kw):
        bb = self._d.textbbox(self._pt(xy), txt, **self._kw(kw))
        return tuple(v / self.s for v in bb)

    def multiline_textbbox(self, xy, txt, **kw):
        bb = self._d.multiline_textbbox(self._pt(xy), txt, **self._kw(kw))
        return tuple(v / self.s for v in bb)


# --------------------------------------------------------------------------
# Canvas lifecycle
# --------------------------------------------------------------------------

def register_box(kind: str, box):
    """Record a drawn element's bbox (x0, y0, x1, y1) for safe-zone checking."""
    x0, y0, x1, y1 = box
    _boxes.append((kind, (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))))


def content_boxes():
    """Every registered element on the current canvas: [(kind, bbox), ...]."""
    return list(_boxes)


def safe_zone_violations(zone, kinds=None):
    """Registered elements overlapping `zone` -- empty list means compliant."""
    zx0, zy0, zx1, zy1 = zone
    out = []
    for kind, (x0, y0, x1, y1) in _boxes:
        if kinds and kind not in kinds:
            continue
        if x0 < zx1 and x1 > zx0 and y0 < zy1 and y1 > zy0:
            out.append((kind, (x0, y0, x1, y1)))
    return out


def canvas(sky_mode: str = "day", scale: int = SS):
    """Fresh 1920x1080 canvas with a sky already painted.

    Returns (image, ScaledDraw). sky_mode: day | sunset | night | plain.
    """
    global _scale
    _scale = scale
    _font_cache.clear()
    _boxes.clear()
    img = Image.new("RGB", (W * scale, H * scale), PALETTE["sky_bottom"])
    d = ScaledDraw(ImageDraw.Draw(img), scale)
    if sky_mode != "plain":
        sky(img, sky_mode)
    return img, d


def save(img: Image.Image, path: str) -> str:
    """Downsample to exactly 1920x1080 and write a PNG."""
    d = os.path.dirname(os.path.abspath(path))
    if d:
        os.makedirs(d, exist_ok=True)
    out = img if img.size == (W, H) else img.resize((W, H), Image.LANCZOS)
    out.save(path, "PNG", optimize=True)
    return path


# --------------------------------------------------------------------------
# Backgrounds
# --------------------------------------------------------------------------

def _vgradient(img: Image.Image, stops):
    """Paint a vertical gradient in place. stops = [(pos 0..1, (r,g,b)), ...]."""
    import numpy as np

    w, h = img.size
    stops = sorted(stops, key=lambda s: s[0])
    ts = np.array([s[0] for s in stops], dtype=np.float64)
    cs = np.array([s[1] for s in stops], dtype=np.float64)
    y = np.linspace(0.0, 1.0, h)
    col = np.stack([np.interp(y, ts, cs[:, c]) for c in range(3)], axis=1)
    band = np.repeat(col[:, None, :], w, axis=1).round().astype(np.uint8)
    img.paste(Image.fromarray(band, "RGB"), (0, 0))


def sky(img: Image.Image, mode: str = "day"):
    """Full-frame sky gradient: day | sunset | night."""
    if mode == "night":
        stops = [(0.0, PALETTE["sky_night_top"]), (1.0, PALETTE["sky_night_bottom"])]
    elif mode == "sunset":
        stops = [
            (0.0, PALETTE["sunset_top"]),
            (0.45, (206, 118, 132)),
            (0.72, PALETTE["sunset_mid"]),
            (1.0, PALETTE["sunset_bottom"]),
        ]
    else:
        stops = [(0.0, PALETTE["sky_top"]), (1.0, PALETTE["sky_bottom"])]
    _vgradient(img, stops)


def ground(d: ScaledDraw, y: int = 880, color=None, dark=None, hills: bool = True):
    """Rolling grass ground filling everything below y."""
    color = color or PALETTE["grass"]
    dark = dark or PALETTE["grass_dark"]
    if hills:
        d.ellipse([-260, y - 130, 760, y + 320], fill=dark)
        d.ellipse([1180, y - 165, 2200, y + 320], fill=dark)
    d.rectangle([0, y, W, H], fill=color)
    d.ellipse([-200, y - 70, 900, y + 130], fill=color)
    d.ellipse([1050, y - 92, 2120, y + 130], fill=color)


def cloud(d: ScaledDraw, x: int, y: int, scale: float = 1.0, color=None, shade=True):
    """Puffy flat cloud centered on (x, y)."""
    c = color or PALETTE["cloud"]
    s = scale
    puffs = [(-96, 6, 74), (-24, -26, 96), (58, 2, 78), (120, 20, 56)]
    if shade:
        for dx, dy, r in puffs:
            d.ellipse([x + (dx - r) * s, y + (dy - r) * s + 14 * s,
                       x + (dx + r) * s, y + (dy + r) * s + 14 * s],
                      fill=PALETTE["cloud_shade"])
    for dx, dy, r in puffs:
        d.ellipse([x + (dx - r) * s, y + (dy - r) * s,
                   x + (dx + r) * s, y + (dy + r) * s], fill=c)
    d.rounded_rectangle([x - 150 * s, y - 4 * s, x + 150 * s, y + 44 * s],
                        radius=44 * s, fill=c)


def sun(d: ScaledDraw, x: int, y: int, r: int = 120, rays: bool = True,
        face: bool = True, color=None, ray_color=None, n_rays: int = 12,
        ray_len: float = 0.55, rotate: float = 0.0):
    """The channel's smiling sun."""
    col = color or PALETTE["sun"]
    rc = ray_color or PALETTE["sun_deep"]
    if rays:
        for i in range(n_rays):
            a = math.radians(rotate + i * 360.0 / n_rays)
            x1, y1 = x + math.cos(a) * r * 1.12, y + math.sin(a) * r * 1.12
            x2, y2 = x + math.cos(a) * r * (1.12 + ray_len), y + math.sin(a) * r * (1.12 + ray_len)
            d.line([(x1, y1), (x2, y2)], fill=rc, width=max(6, int(r * 0.14)))
    d.ellipse([x - r, y - r, x + r, y + r], fill=rc)
    d.ellipse([x - r * 0.92, y - r * 0.92, x + r * 0.92, y + r * 0.92], fill=col)
    if face:
        er = r * 0.11
        for sx in (-0.34, 0.34):
            d.ellipse([x + r * sx - er, y - r * 0.22 - er * 1.35,
                       x + r * sx + er, y - r * 0.22 + er * 1.35],
                      fill=PALETTE["ink"])
        d.arc([x - r * 0.46, y - r * 0.18, x + r * 0.46, y + r * 0.56],
              15, 165, fill=PALETTE["ink"], width=max(4, int(r * 0.075)))
        for sx in (-0.62, 0.62):
            d.ellipse([x + r * sx - r * 0.13, y + r * 0.06,
                       x + r * sx + r * 0.13, y + r * 0.26],
                      fill=(255, 150, 150))


def stars(d: ScaledDraw, n: int = 70, seed: int = 3, area=(0, 0, W, 760),
          color=None, twinkle: bool = True):
    """Deterministic star field for night scenes."""
    col = color or PALETTE["star"]
    rnd = random.Random(seed)
    x0, y0, x1, y1 = area
    for _ in range(n):
        x = rnd.uniform(x0, x1)
        y = rnd.uniform(y0, y1)
        r = rnd.uniform(2.2, 6.0)
        d.ellipse([x - r, y - r, x + r, y + r], fill=col)
        if twinkle and rnd.random() < 0.28:
            L = r * 4.4
            d.line([(x - L, y), (x + L, y)], fill=col, width=2)
            d.line([(x, y - L), (x, y + L)], fill=col, width=2)


# --------------------------------------------------------------------------
# Characters
# --------------------------------------------------------------------------

def kid(d: ScaledDraw, x: int, y: int, scale: float = 1.0, skin=None, shirt=None,
        hair=None, arms: str = "down", mouth: str = "smile", looking: str = "up"):
    """Kid mascot standing with feet at (x, y).

    arms: down | up | one_up | point_up   mouth: smile | o | line
    looking: up | front  (shifts the pupils)
    """
    s = scale
    sk = skin or PALETTE["skin"]
    sh = shirt or PALETTE["shirt"]
    hr = hair or PALETTE["hair"]
    ink = PALETTE["ink"]

    hip_y = y - 150 * s
    sho_y = y - 300 * s
    head_y = y - 388 * s
    head_r = 88 * s

    register_box("kid", (x - 150 * s, head_y - head_r - 20 * s,
                         x + 150 * s, y + 10 * s))
    # legs
    for dx in (-34, 34):
        d.rounded_rectangle([x + dx * s - 26 * s, hip_y, x + dx * s + 26 * s, y - 18 * s],
                            radius=26 * s, fill=PALETTE["pants"])
        d.rounded_rectangle([x + dx * s - 34 * s, y - 40 * s, x + dx * s + 40 * s, y],
                            radius=18 * s, fill=PALETTE["shoe"])
    # body
    d.rounded_rectangle([x - 82 * s, sho_y, x + 82 * s, hip_y + 16 * s],
                        radius=48 * s, fill=sh)
    # arms
    aw = 30 * s
    if arms == "up":
        for sx in (-1, 1):
            d.line([(x + sx * 74 * s, sho_y + 26 * s), (x + sx * 150 * s, sho_y - 120 * s)],
                   fill=sh, width=aw)
            d.ellipse([x + sx * 150 * s - 24 * s, sho_y - 144 * s,
                       x + sx * 150 * s + 24 * s, sho_y - 96 * s], fill=sk)
    elif arms in ("one_up", "point_up"):
        d.line([(x + 74 * s, sho_y + 26 * s), (x + 148 * s, sho_y - 130 * s)],
               fill=sh, width=aw)
        d.ellipse([x + 148 * s - 24 * s, sho_y - 154 * s,
                   x + 148 * s + 24 * s, sho_y - 106 * s], fill=sk)
        d.line([(x - 74 * s, sho_y + 26 * s), (x - 104 * s, sho_y + 150 * s)],
               fill=sh, width=aw)
        d.ellipse([x - 104 * s - 24 * s, sho_y + 132 * s,
                   x - 104 * s + 24 * s, sho_y + 180 * s], fill=sk)
    else:
        for sx in (-1, 1):
            d.line([(x + sx * 74 * s, sho_y + 26 * s), (x + sx * 108 * s, sho_y + 156 * s)],
                   fill=sh, width=aw)
            d.ellipse([x + sx * 108 * s - 24 * s, sho_y + 138 * s,
                       x + sx * 108 * s + 24 * s, sho_y + 186 * s], fill=sk)
    # neck + head
    d.rectangle([x - 22 * s, head_y + head_r * 0.65, x + 22 * s, sho_y + 8 * s], fill=sk)
    d.ellipse([x - head_r, head_y - head_r, x + head_r, head_y + head_r], fill=sk)
    # hair cap
    d.pieslice([x - head_r - 4 * s, head_y - head_r - 10 * s,
                x + head_r + 4 * s, head_y + head_r - 24 * s], 180, 360, fill=hr)
    d.ellipse([x - head_r - 6 * s, head_y - head_r - 6 * s,
               x - head_r + 34 * s, head_y - 6 * s], fill=hr)
    d.ellipse([x + head_r - 34 * s, head_y - head_r - 6 * s,
               x + head_r + 6 * s, head_y - 6 * s], fill=hr)
    # eyes
    pupil_dy = -12 * s if looking == "up" else 0
    for sx in (-1, 1):
        ex = x + sx * 32 * s
        ey = head_y + 4 * s
        d.ellipse([ex - 17 * s, ey - 20 * s, ex + 17 * s, ey + 20 * s], fill=PALETTE["white"])
        d.ellipse([ex - 9 * s, ey - 10 * s + pupil_dy, ex + 9 * s, ey + 10 * s + pupil_dy],
                  fill=ink)
    # cheeks
    for sx in (-1, 1):
        d.ellipse([x + sx * 62 * s - 16 * s, head_y + 30 * s,
                   x + sx * 62 * s + 16 * s, head_y + 52 * s], fill=(255, 158, 158))
    # mouth
    if mouth == "o":
        d.ellipse([x - 20 * s, head_y + 38 * s, x + 20 * s, head_y + 76 * s], fill=ink)
    elif mouth == "line":
        d.line([(x - 22 * s, head_y + 54 * s), (x + 22 * s, head_y + 54 * s)],
               fill=ink, width=6 * s)
    else:
        d.chord([x - 36 * s, head_y + 20 * s, x + 36 * s, head_y + 74 * s],
                20, 160, fill=ink)


def rocket(d: ScaledDraw, x: int, y: int, scale: float = 1.0, flame: bool = True,
           body=None, accent=None, tilt: str = "up", face: bool = False):
    """Rocket mascot, centered on (x, y). tilt: up | right."""
    s = scale
    bd = body or PALETTE["rocket"]
    ac = accent or PALETTE["rocket_red"]

    def P(px, py):
        # rotate 90deg clockwise for the "right" pose
        return (x + py * s, y - px * s) if tilt == "right" else (x + px * s, y + py * s)

    def box(a, b):
        """Axis-aligned bbox spanning two posed points (pose-independent)."""
        (ax, ay), (bx, by) = P(*a), P(*b)
        return [min(ax, bx), min(ay, by), max(ax, bx), max(ay, by)]

    corners = [P(-146, -158), P(146, -158), P(-146, 306 if flame else 168),
               P(146, 306 if flame else 168)]
    register_box("rocket", (min(c[0] for c in corners), min(c[1] for c in corners),
                            max(c[0] for c in corners), max(c[1] for c in corners)))
    if flame:
        d.polygon([P(-46, 158), P(0, 306), P(46, 158)], fill=PALETTE["flame"])
        d.polygon([P(-24, 158), P(0, 240), P(24, 158)], fill=PALETTE["flame_hot"])
    # fins
    d.polygon([P(-56, 56), P(-146, 168), P(-56, 152)], fill=ac)
    d.polygon([P(56, 56), P(146, 168), P(56, 152)], fill=ac)
    d.polygon([P(-24, 132), P(0, 196), P(24, 132)], fill=PALETTE["rocket_dark"])
    # body
    d.polygon([P(-58, -26), P(-58, 150), P(58, 150), P(58, -26)], fill=bd)
    d.ellipse(box((-58, 104), (58, 168)), fill=bd)
    # nose cone
    d.polygon([P(-58, -16), P(0, -158), P(58, -16)], fill=ac)
    # window
    wc = P(0, 26)
    wr = 44 * s
    d.ellipse([wc[0] - wr, wc[1] - wr, wc[0] + wr, wc[1] + wr], fill=PALETTE["window_rim"])
    d.ellipse([wc[0] - wr * 0.8, wc[1] - wr * 0.8, wc[0] + wr * 0.8, wc[1] + wr * 0.8],
              fill=PALETTE["window"])
    if face:
        for sx in (-1, 1):
            e = P(sx * 15, 18)
            d.ellipse([e[0] - 7 * s, e[1] - 9 * s, e[0] + 7 * s, e[1] + 9 * s],
                      fill=PALETTE["ink"])
        m = P(0, 26)
        d.chord([m[0] - 20 * s, m[1] - 2 * s, m[0] + 20 * s, m[1] + 30 * s],
                20, 160, fill=PALETTE["ink"])
    # stripe
    d.rectangle(box((-58, 106), (58, 126)), fill=ac)


def molecule(d: ScaledDraw, x: int, y: int, r: float = 34, face: bool = True,
             color=None, wobble: float = 0.0):
    """One smiling air molecule (a friendly O2-ish blob)."""
    c = color or PALETTE["molecule"]
    dk = PALETTE["molecule_dark"]
    off = r * 0.62
    d.ellipse([x - off - r * 0.72, y + wobble - r * 0.72,
               x - off + r * 0.72, y + wobble + r * 0.72], fill=dk)
    d.ellipse([x + off - r * 0.72, y - wobble - r * 0.72,
               x + off + r * 0.72, y - wobble + r * 0.72], fill=dk)
    d.ellipse([x - r, y - r, x + r, y + r], fill=c)
    if face and r >= 16:
        er = max(2.0, r * 0.13)
        for sx in (-0.34, 0.34):
            d.ellipse([x + r * sx - er, y - r * 0.18 - er * 1.3,
                       x + r * sx + er, y - r * 0.18 + er * 1.3], fill=PALETTE["ink"])
        d.chord([x - r * 0.44, y - r * 0.06, x + r * 0.44, y + r * 0.56],
                20, 160, fill=PALETTE["ink"])


def molecule_field(d: ScaledDraw, n: int = 60, seed: int = 5,
                   area=(120, 140, 1800, 820), r_range=(20, 40), face: bool = True,
                   color=None):
    """Scatter n non-overlapping molecules; returns their (x, y, r) list."""
    rnd = random.Random(seed)
    x0, y0, x1, y1 = area
    placed = []
    tries = 0
    while len(placed) < n and tries < n * 400:
        tries += 1
        r = rnd.uniform(*r_range)
        x = rnd.uniform(x0 + r * 2, x1 - r * 2)
        y = rnd.uniform(y0 + r * 2, y1 - r * 2)
        if all((x - px) ** 2 + (y - py) ** 2 > (r + pr + 26) ** 2 for px, py, pr in placed):
            placed.append((x, y, r))
    for x, y, r in placed:
        molecule(d, x, y, r, face=face and r > 24, color=color)
    return placed


# --------------------------------------------------------------------------
# Light + physics props
# --------------------------------------------------------------------------

def zig_ray(d: ScaledDraw, p1, p2, color=None, amplitude: float = 22,
            wavelength: float = 110, width: int = 9, phase: float = 0.0,
            taper: bool = False):
    """Wavy light ray from p1 to p2. Short wavelength = 'blue' light."""
    col = color or PALETTE["blue_ray"]
    (x1, y1), (x2, y2) = p1, p2
    dx, dy = x2 - x1, y2 - y1
    L = math.hypot(dx, dy)
    if L < 1:
        return
    ux, uy = dx / L, dy / L
    nx, ny = -uy, ux
    steps = max(24, int(L / 5))
    pts = []
    for i in range(steps + 1):
        t = i / steps
        a = amplitude * (1.0 - t * 0.55 if taper else 1.0)
        off = math.sin(phase + t * L / max(8.0, wavelength) * 2 * math.pi) * a
        pts.append((x1 + ux * L * t + nx * off, y1 + uy * L * t + ny * off))
    d.line(pts, fill=col, width=width, joint="curve")


def arrow(d: ScaledDraw, p1, p2, color=None, width: int = 12, head: float = 34):
    """Straight arrow with a solid triangular head."""
    col = color or PALETTE["ink"]
    (x1, y1), (x2, y2) = p1, p2
    a = math.atan2(y2 - y1, x2 - x1)
    bx, by = x2 - math.cos(a) * head * 0.9, y2 - math.sin(a) * head * 0.9
    d.line([(x1, y1), (bx, by)], fill=col, width=width)
    d.polygon([
        (x2, y2),
        (x2 - math.cos(a - 0.42) * head, y2 - math.sin(a - 0.42) * head),
        (x2 - math.cos(a + 0.42) * head, y2 - math.sin(a + 0.42) * head),
    ], fill=col)


def plane(d: ScaledDraw, x: int, y: int, scale: float = 1.0, body=None,
          accent=None, facing: str = "right", pitch: float = 0.0,
          windows: bool = True):
    """Cartoon airliner, centered on (x, y), flying `facing` (right | left).

    pitch tilts the nose up in degrees -- use a few degrees for climb shots.
    """
    s = scale
    bd = body or PALETTE["white"]
    ac = accent or PALETTE["rocket_red"]
    sgn = 1 if facing == "right" else -1
    a = math.radians(-pitch * sgn)
    ca, sa = math.cos(a), math.sin(a)

    def P(px, py):
        px *= sgn
        return (x + (px * ca - py * sa) * s, y + (px * sa + py * ca) * s)

    def poly(pts, fill):
        d.polygon([P(*p) for p in pts], fill=fill)

    register_box("plane", (x - 300 * s, y - 190 * s, x + 300 * s, y + 190 * s))

    # far wing + far stabilizer sit behind the fuselage
    poly([(30, -12), (-64, -92), (-12, -100), (66, -8)], PALETTE["cloud_shade"])
    poly([(-186, -16), (-258, -68), (-206, -74), (-160, -10)], PALETTE["cloud_shade"])
    # tail fin, swept back
    poly([(-206, -24), (-288, -150), (-216, -150), (-152, -24)], ac)
    # fuselage -- polygon + end caps, because a rounded rect cannot rotate and
    # pitch would otherwise tilt every part of the plane except its body
    poly([(-206, -46), (186, -46), (186, 46), (-206, 46)], bd)
    for cap in ((-206, 0), (186, 0)):
        c = P(*cap)
        d.ellipse([c[0] - 46 * s, c[1] - 46 * s, c[0] + 46 * s, c[1] + 46 * s],
                  fill=bd)
    poly([(178, -44), (258, 4), (178, 44)], bd)          # nose
    nose = P(224, 2)
    d.ellipse([nose[0] - 30 * s, nose[1] - 30 * s, nose[0] + 30 * s, nose[1] + 30 * s],
              fill=bd)
    # cockpit glass
    cw = P(196, -14)
    d.ellipse([cw[0] - 30 * s, cw[1] - 24 * s, cw[0] + 30 * s, cw[1] + 24 * s],
              fill=PALETTE["window"])
    # cabin windows
    if windows:
        for i in range(7):
            w = P(126 - i * 46, -8)
            d.ellipse([w[0] - 13 * s, w[1] - 13 * s, w[0] + 13 * s, w[1] + 13 * s],
                      fill=PALETTE["window"])
    # near wing (sweeps back and down) + engine slung under it
    poly([(6, 12), (-140, 126), (-68, 138), (44, 22)], ac)
    eng = P(-74, 102)
    d.rounded_rectangle([eng[0] - 42 * s, eng[1] - 24 * s,
                         eng[0] + 42 * s, eng[1] + 24 * s],
                        radius=24 * s, fill=PALETTE["ink"])
    d.ellipse([eng[0] + 22 * s, eng[1] - 22 * s, eng[0] + 62 * s, eng[1] + 22 * s],
              fill=PALETTE["window"])
    # near stabilizer
    poly([(-176, 6), (-262, 62), (-206, 70), (-150, 12)], ac)
    # belly stripe ties it to the channel palette (yellow, so the red wing reads)
    poly([(-190, 22), (150, 22), (150, 38), (-190, 38)], PALETTE["accent"])


def paper_plane(d: ScaledDraw, x: int, y: int, scale: float = 1.0, color=None,
                facing: str = "right"):
    """Folded paper dart -- the 'try it yourself' prop."""
    s = scale
    c = color or PALETTE["white"]
    sgn = 1 if facing == "right" else -1

    def P(px, py):
        return (x + px * sgn * s, y + py * s)

    d.polygon([P(120, 0), P(-110, -76), P(-52, 6)], fill=c)
    d.polygon([P(120, 0), P(-110, 76), P(-52, 6)], fill=PALETTE["cloud_shade"])
    d.line([P(120, 0), P(-52, 6)], fill=PALETTE["molecule_dark"], width=5)


def airfoil(d: ScaledDraw, x: int, y: int, scale: float = 1.0, angle: float = 8.0,
            color=None, outline=None, outline_w: int = 7):
    """Wing cross-section: flat-ish underside, curved top, tilted by `angle`."""
    s = scale
    c = color or PALETTE["white"]
    a = math.radians(-angle)
    ca, sa = math.cos(a), math.sin(a)
    def thickness(u):        # NACA-style: blunt at the nose, sharp at the tail
        return 300 * 5 * 0.16 * (0.2969 * math.sqrt(u) - 0.1260 * u
                                 - 0.3516 * u ** 2 + 0.2843 * u ** 3
                                 - 0.1015 * u ** 4)

    def camber(u):           # gentle arch: this is the curve, not a myth about it
        return -300 * 0.10 * 4 * u * (1 - u)

    pts = []
    for t in range(0, 61):   # upper surface, nose -> tail
        u = t / 60.0
        pts.append((-150 + 300 * u, camber(u) - thickness(u)))
    for t in range(60, -1, -1):   # lower surface, tail -> nose
        u = t / 60.0
        pts.append((-150 + 300 * u, camber(u) + thickness(u)))
    poly = [(x + (px * ca - py * sa) * s, y + (px * sa + py * ca) * s)
            for px, py in pts]
    d.polygon(poly, fill=c)
    # an outline is what makes a pale wing read against a pale sky
    d.line(poly + [poly[0]], fill=outline or PALETTE["ink"], width=outline_w,
           joint="curve")



def wind_streaks(d: ScaledDraw, x: int, y: int, n: int = 5, length: float = 260,
                 spread: float = 150, color=None, width: int = 10,
                 facing: str = "right", curve: float = 0.0, seed: int = 2):
    """Airflow / speed lines. curve bends the tails downward (deflected air)."""
    c = color or (235, 244, 255)
    rnd = random.Random(seed)
    sgn = 1 if facing == "right" else -1
    for i in range(n):
        oy = y - spread / 2 + spread * (i / max(1, n - 1))
        L = length * rnd.uniform(0.72, 1.0)
        pts = []
        for k in range(11):
            t = k / 10.0
            pts.append((x + sgn * L * t, oy + curve * (t ** 2)))
        d.line(pts, fill=c, width=width, joint="curve")


def force_arrow(d: ScaledDraw, p1, p2, label: str, color=None, width: int = 16,
                label_size: int = 46, label_at: float = 1.0, label_off=(0, -46)):
    """Labeled force vector -- lift, weight, thrust, drag."""
    col = color or PALETTE["ink"]
    arrow(d, p1, p2, color=col, width=width, head=42)
    lx = p1[0] + (p2[0] - p1[0]) * label_at + label_off[0]
    ly = p1[1] + (p2[1] - p1[1]) * label_at + label_off[1]
    speech_pop(d, lx, ly, label, size=label_size, fill=col, text_fill=PALETTE["white"],
               pad=22)


def prism(d: ScaledDraw, x: int, y: int, size: float = 260, color=None):
    """Glass triangle used for the rainbow-splitting demo."""
    c = color or PALETTE["prism_glass"]
    h = size * 0.87
    pts = [(x, y - h * 0.62), (x - size * 0.5, y + h * 0.38), (x + size * 0.5, y + h * 0.38)]
    d.polygon(pts, fill=c, outline=PALETTE["white"], width=8)
    d.line([pts[0], pts[1]], fill=(255, 255, 255), width=10)


def thought_bubble(d: ScaledDraw, x: int, y: int, w: int = 620, h: int = 300,
                   tail_to=None, text: str = "", text_size: int = 62,
                   fill=None, text_fill=None):
    """Rounded thought cloud centered on (x, y) with optional trailing dots."""
    bg = fill or PALETTE["white"]
    d.rounded_rectangle([x - w / 2, y - h / 2, x + w / 2, y + h / 2],
                        radius=min(w, h) * 0.42, fill=bg)
    for cx, cy, r in [(-w * 0.34, -h * 0.42, h * 0.26), (w * 0.16, -h * 0.48, h * 0.3),
                      (w * 0.36, -h * 0.2, h * 0.24), (-w * 0.42, h * 0.16, h * 0.24)]:
        d.ellipse([x + cx - r, y + cy - r, x + cx + r, y + cy + r], fill=bg)
    if tail_to:
        tx, ty = tail_to
        for i, k in enumerate((0.42, 0.68, 0.88)):
            bx = x + (tx - x) * k
            by = y + (ty - y) * k
            r = 30 - i * 9
            d.ellipse([bx - r, by - r, bx + r, by + r], fill=bg)
    if text:
        title_text(d, (x, y), text, text_size, fill=text_fill or PALETTE["text_dark"],
                   stroke=0)


def speech_pop(d: ScaledDraw, x: int, y: int, text: str, size: int = 64,
               fill=None, text_fill=None, pad: int = 34):
    """Word-bubble badge ('BOING!', 'SCATTERING!') sized to its text."""
    bg = fill or PALETTE["accent"]
    f = font(size)
    bb = d.textbbox((0, 0), text, font=f)
    w, h = bb[2] - bb[0], bb[3] - bb[1]
    d.rounded_rectangle([x - w / 2 - pad, y - h / 2 - pad * 0.7,
                         x + w / 2 + pad, y + h / 2 + pad * 0.7],
                        radius=(h + pad) * 0.6, fill=bg)
    register_box("badge", (x - w / 2 - pad, y - h / 2 - pad * 0.7,
                           x + w / 2 + pad, y + h / 2 + pad * 0.7))
    title_text(d, (x, y), text, size, fill=text_fill or PALETTE["text_dark"], stroke=0)


# --------------------------------------------------------------------------
# Text
# --------------------------------------------------------------------------

def title_text(d: ScaledDraw, xy, text: str, size: int = 96, fill=None,
               stroke: int = 10, stroke_fill=None, anchor: str = "mm",
               align: str = "center", spacing: float = 1.12, unicode_wide=None):
    """Stroked display text -- the kid-video 'outlined' look.

    anchor uses the two-letter Pillow convention (mm, ma, lm, ...) but is
    computed manually so it also works with Pillow's bitmap fallback font.
    Returns the drawn bounding box in logical coordinates.
    """
    if unicode_wide is None:
        unicode_wide = any(ord(ch) > 0x2FF for ch in text)
    f = font(size, unicode_wide=unicode_wide)
    col = fill or PALETTE["text"]
    sf = stroke_fill or PALETTE["ink"]
    line_gap = int(size * (spacing - 1.0) * 4)
    bb = d.multiline_textbbox((0, 0), text, font=f, spacing=line_gap,
                              align=align, stroke_width=stroke)
    w, h = bb[2] - bb[0], bb[3] - bb[1]
    x, y = xy
    hx = {"l": 0, "m": -w / 2, "r": -w}[anchor[0] if anchor[0] in "lmr" else "m"]
    vy = {"a": 0, "m": -h / 2, "d": -h, "s": -h, "t": 0, "b": -h}.get(anchor[1], -h / 2)
    px = x + hx - bb[0]
    py = y + vy - bb[1]
    d.multiline_text((px, py), text, font=f, fill=col, spacing=line_gap,
                     align=align, stroke_width=stroke, stroke_fill=sf)
    box = (x + hx, y + vy, x + hx + w, y + vy + h)
    register_box("text", box)
    return box


def caption(d: ScaledDraw, text: str, size: int = 58, y: int = 950,
            bg=None, fg=None, pad: int = 30, width_frac: float = 0.86):
    """Bottom banner caption strip (burned-in, kept out of the end-screen zone)."""
    f = font(size, unicode_wide=any(ord(ch) > 0x2FF for ch in text))
    bb = d.textbbox((0, 0), text, font=f)
    w = min(bb[2] - bb[0] + pad * 3, W * width_frac)
    h = (bb[3] - bb[1]) + pad * 1.6
    d.rounded_rectangle([W / 2 - w / 2, y - h / 2, W / 2 + w / 2, y + h / 2],
                        radius=h * 0.5, fill=bg or PALETTE["banner"])
    title_text(d, (W / 2, y), text, size, fill=fg or PALETTE["white"], stroke=0)


def badge(d: ScaledDraw, xy, text: str, size: int = 54, fill=None, text_fill=None):
    """Small rounded label used for chapter titles / scene tags."""
    speech_pop(d, xy[0], xy[1], text, size=size, fill=fill or PALETTE["white"],
               text_fill=text_fill or PALETTE["text_dark"], pad=26)


# --------------------------------------------------------------------------
# Layout guides
# --------------------------------------------------------------------------

def end_screen_guides(d: ScaledDraw, show: bool = False):
    """YouTube end-card safe zones for outro scenes.

    Returns the rectangles that must stay visually empty. Pass show=True only
    while designing -- production frames never draw the guides.

    Pair it with safe_zone_violations(zones["end_cards"]) to *prove* an outro
    complies; tests/unit.py does exactly that for every episode's last scene.
    """
    zones = {
        # bottom-right 40% of the frame: end cards / subscribe button live here
        "end_cards": (int(W * 0.60), int(H * 0.60), W, H),
        # what the Ken Burns zoom will still be showing at the end of the scene
        "kenburns_safe": SAFE,
        # YouTube's own controls overlay the bottom strip
        "player_ui": (0, int(H * 0.90), W, H),
        "title_safe": (int(W * 0.05), int(H * 0.05), int(W * 0.95), int(H * 0.95)),
    }
    if show:
        for name, (x0, y0, x1, y1) in zones.items():
            d.rectangle([x0, y0, x1 - 1, y1 - 1], outline=(255, 0, 128), width=6)
            title_text(d, (x0 + 20, y0 + 20), name, 34, fill=(255, 0, 128),
                       stroke=0, anchor="la")
    return zones


def vignette(img: Image.Image, strength: float = 0.16):
    """Soft corner darkening; keeps flat art from feeling washed out."""
    w, h = img.size
    mask = Image.new("L", (w, h), 0)
    md = ImageDraw.Draw(mask)
    md.ellipse([-w * 0.22, -h * 0.30, w * 1.22, h * 1.30], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(radius=w * 0.05))
    dark = Image.new("RGB", (w, h), (0, 0, 0))
    return Image.composite(img, Image.blend(img, dark, strength), mask)


def contact_sheet(paths, out_path: str, cols: int = 5, cell_w: int = 480):
    """Grid of rendered frames -- quick visual check of a whole episode."""
    paths = [p for p in paths if os.path.exists(p)]
    if not paths:
        raise ValueError("no frames to sheet")
    cell_h = int(cell_w * H / W)
    rows = (len(paths) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell_w, rows * (cell_h + 34)), (24, 26, 38))
    sd = ImageDraw.Draw(sheet)
    try:
        f = ImageFont.truetype(font_path() or "", 24)
    except Exception:
        f = ImageFont.load_default()
    for i, p in enumerate(paths):
        im = Image.open(p).convert("RGB").resize((cell_w, cell_h), Image.LANCZOS)
        cx, cy = (i % cols) * cell_w, (i // cols) * (cell_h + 34)
        sheet.paste(im, (cx, cy))
        sd.text((cx + 8, cy + cell_h + 6), os.path.basename(p), font=f, fill=(230, 230, 240))
    sheet.save(out_path)
    return out_path
