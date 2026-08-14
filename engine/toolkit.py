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


SPRITE_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "sprites")

_sprite_cache: dict = {}


def sprite_path(name: str) -> str:
    """Where a named sprite lives. `name` is a stem, e.g. "goofy/talk"."""
    return os.path.normpath(os.path.join(SPRITE_ROOT, name + ".png"))


def has_sprite(name: str) -> bool:
    return os.path.isfile(sprite_path(name))


def sprite(img: Image.Image, name: str, x: int, y: int, height: int,
           facing: str = "right", anchor: str = "mb"):
    """Composite a transparent character PNG onto the canvas.

    The vector `dog()` primitive can only ever look like stacked ellipses, so
    characters that need to read as drawn artwork come in as sprites instead.
    Everything around them -- backdrops, bubbles, captions -- stays code-drawn.

    `height` is the sprite's target height in LOGICAL units (the same 1920x1080
    space every other primitive speaks); the canvas is supersampled, so the
    paste is scaled by that factor here. Art is authored facing right and
    mirrored for the other side, which halves how many files have to exist.

    anchor: "mb" places (x, y) at the middle of the sprite's bottom edge, which
    matches how dog() treats its paws, so a sprite drops into an existing scene
    without moving anything.
    """
    path = sprite_path(name)
    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"sprite {name!r} not found at {path}. See docs/SPRITES.md for the "
            f"manifest of files this mode expects and how they are authored."
        )
    key = (path, os.path.getmtime(path))
    art = _sprite_cache.get(key)
    if art is None:
        art = Image.open(path).convert("RGBA")
        _sprite_cache[key] = art

    s = _scale
    target_h = max(1, int(round(height * s)))
    target_w = max(1, int(round(art.width * target_h / art.height)))
    out = art.resize((target_w, target_h), Image.LANCZOS)
    if facing != "right":
        out = out.transpose(Image.FLIP_LEFT_RIGHT)

    px = int(round(x * s)) - (target_w // 2 if anchor[0] == "m" else 0)
    py = int(round(y * s)) - (target_h if anchor[1] == "b" else 0)
    img.alpha_composite(out, (px, py)) if img.mode == "RGBA" else img.paste(out, (px, py), out)
    register_box("dog", (x - height * 0.42, y - height, x + height * 0.42, y))
    return (px / s, py / s, (px + target_w) / s, (py + target_h) / s)


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


def sprite_state(speaking: bool, expression: str) -> str:
    """Which sprite file a beat wants.

    The four states exist because they are the ones the dialogue actually needs:
    who is talking, who just landed the punchline, and who is unimpressed.
    """
    if speaking:
        return "laugh" if expression == "laugh" else "talk"
    return "smug" if expression in ("smug", "deadpan") else "idle"


def character(img: Image.Image, d: ScaledDraw, who: str, x: int, y: int,
              scale: float = 1.0, facing: str = "right", speaking: bool = False,
              expression: str = "happy", outfit=None, holding=None, **kw):
    """Draw a lead character, preferring sprite art and falling back to vectors.

    One entry point so a scene never has to know which it got. The lookup walks
    from most specific to least:

        goofy/space-talk   costume art, if it has been drawn
        goofy/talk         plain art, costume dropped
        tk.dog(...)        vector fallback

    That ordering is what makes costumes additive later: drop a
    `<name>/<outfit>-<state>.png` in and it starts being used, with no code
    change. Until any sprite exists at all, every episode renders exactly as it
    did before.

    NOTE: in sprite mode the vector `outfit`/`holding` kit is NOT drawn on top.
    Those shapes are positioned against the vector body's geometry and would sit
    wrong on painted art, so a costume only appears once costume art exists.
    """
    state = sprite_state(speaking, expression)
    names = []
    if outfit:
        names.append(f"{who}/{outfit}-{state}")
    names.append(f"{who}/{state}")

    for name in names:
        if has_sprite(name):
            # Sprites are authored at roughly the vector dog's sitting height,
            # so the same `scale` a scene already passes keeps the two modes
            # interchangeable without every caller being rewritten.
            return sprite(img, name, x, y, int(round(360 * scale)), facing=facing)

    return dog(d, x, y, scale, facing=facing, speaking=speaking,
               expression=expression, outfit=outfit, holding=holding, **kw)


def dog(d: ScaledDraw, x: int, y: int, scale: float = 1.0, facing: str = "right",
        coat=None, ear=None, speaking: bool = False, expression: str = "happy",
        collar=None, tongue: bool = True, outfit=None, holding=None,
        markings=None, name=None):
    """Sitting cartoon dog with its paws at (x, y).

    `speaking` opens the muzzle; the listener in a two-hander should be drawn
    with speaking=False so it is always obvious who has the line. This is a
    per-line mouth state, not phoneme lip-sync -- the pipeline renders one
    still per scene, so there is no frame-by-frame mouth to animate. The open
    jaw is drawn large, with tongue and teeth, because at 1080p a small dark
    oval reads as a smudge rather than a dog mid-sentence.

    Depth comes from a second, darker pass of the same shapes offset behind the
    lit ones -- flat fills alone made these read as blobs rather than animals.

    expression: happy | laugh | surprised | deadpan | smug
    outfit:     None | shades | redshades | helmet | beanie | rainhat |
                partyhat | chef | cap
    holding:    None | beer | mug | marshmallow | ball | spatula | treats
    markings:   None | collie  -- a white blaze, muzzle, chest and tail tip over
                a dark coat, which is what separates the two leads at a glance
                rather than relying on coat colour alone.
    name:       drawn on a bone tag hanging from the collar, so the characters
                are named on screen the way they are in the reference art.
    Give each character a different `coat` so the two never blur together.
    """
    s = scale
    sgn = 1 if facing == "right" else -1
    c = coat or (214, 168, 108)
    ec = ear or tuple(max(0, v - 34) for v in c)
    ink = PALETTE["ink"]
    white = PALETTE["white"]
    cream = (250, 240, 226)
    # One coat, three tones: shade for forms turning away, light for the top
    # planes the sun hits. Everything below picks from these.
    shade = tuple(max(0, int(v * 0.82)) for v in c)
    light = tuple(min(255, int(v + (255 - v) * 0.20)) for v in c)
    belly = (252, 246, 236)
    gum = (232, 120, 134)

    def P(px, py):
        return (x + px * sgn * s, y + py * s)

    def _box(cx, cy, rx, ry):
        a, b = P(cx - rx, cy - ry), P(cx + rx, cy + ry)
        return [min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])]

    def ell(cx, cy, rx, ry, fill):
        d.ellipse(_box(cx, cy, rx, ry), fill=fill)

    def rrect(cx, cy, rx, ry, fill, radius=18):
        d.rounded_rectangle(_box(cx, cy, rx, ry), radius=radius * s, fill=fill)

    def chord(cx, cy, rx, ry, a0, a1, fill, width=None):
        # Angles are screen-space, so a mirrored dog needs them mirrored too or
        # every smile becomes a frown when it faces left.
        if sgn < 0:
            a0, a1 = 180 - a1, 180 - a0
        if width:
            d.arc(_box(cx, cy, rx, ry), a0, a1, fill=fill, width=int(width * s))
        else:
            d.chord(_box(cx, cy, rx, ry), a0, a1, fill=fill)

    collie = markings == "collie"
    # A collie's white is brighter than the soft belly cream a tan dog gets.
    if collie:
        belly = white

    register_box("dog", (x - 180 * s, y - 360 * s, x + 180 * s, y + 20 * s))

    # contact shadow — without it the dog floats above the ground
    d.ellipse([x - 118 * s, y - 20 * s, x + 118 * s, y + 16 * s],
              fill=_blend(ink, white, 0.72))

    # Life-support pack goes on before the body so the dog sits in front of it.
    if outfit == "helmet":
        rrect(-72, -150, 44, 74, (222, 228, 238), radius=20)
        rrect(-72, -150, 34, 62, (198, 206, 220), radius=16)
        rrect(-40, -196, 12, 20, (240, 168, 72), radius=5)

    # ---- tail: a tapering plume sweeping up behind the haunch. The old single
    # polygon jutted up beside the head and read as a raised arm; equal-sized
    # tufts read as a caterpillar, so this starts thick inside the hip and
    # narrows to a tip.
    for tx, ty, tr in ((-74, -88, 31), (-92, -104, 28), (-110, -124, 25),
                       (-124, -148, 21), (-134, -172, 17), (-139, -194, 13),
                       (-140, -212, 10)):
        ell(tx, ty, tr, tr, shade)
    if collie:
        # A collie's tail ends in a white flash — cheap, and it reads instantly.
        for tx, ty, tr in ((-134, -172, 17), (-139, -194, 13), (-140, -212, 10)):
            ell(tx, ty, tr, tr, white)
    else:
        ell(-140, -212, 10, 10, light)

    # ---- body: haunch behind, chest in front, belly patch for the near side
    ell(-48, -74, 64, 72, shade)
    ell(-52, -84, 46, 52, c)                                  # hip highlight
    ell(6, -130, 72, 80, c)
    ell(14, -112, 44, 56, belly)                              # chest fur
    ell(2, -178, 46, 30, light)                               # shoulder top light

    # ---- front legs with toes
    for lx in (26, 78):
        rrect(lx, -38, 23, 40, c, radius=22)
        ell(lx, -8, 27, 17, belly)
        for t in (-9, 0, 9):
            d.line([P(lx + t, -14), P(lx + t, -2)], fill=_blend(ink, belly, 0.55),
                   width=max(1, int(3 * s)))

    _dog_suit(d, P, ell, rrect, s, sgn, outfit, ink, white)

    # A sealed suit covers the collar; leaving the tag floating over the neck
    # ring made it look stuck to the outside of the spacesuit.
    if collar and outfit != "helmet":
        rrect(6, -186, 54, 13, collar, radius=12)
        rrect(6, -184, 54, 5, _blend(collar, white, 0.22), radius=4)   # highlight
        if name:
            # A bone-shaped tag, like the reference art: two lobes and a bar,
            # with the name across it. Drawn in screen space rather than dog
            # space so the lettering never comes out mirrored on a left-facing
            # dog.
            tag_x, tag_y = x + 26 * sgn * s, y - 156 * s
            bw, bh = 46 * s, 21 * s
            for lobe in (-bw * 0.52, bw * 0.52):
                d._d.ellipse([(tag_x + lobe - bh * 0.62) * d.s, (tag_y - bh * 0.62) * d.s,
                              (tag_x + lobe + bh * 0.62) * d.s, (tag_y + bh * 0.62) * d.s],
                             fill=(252, 246, 232))
            d._d.rounded_rectangle([(tag_x - bw * 0.60) * d.s, (tag_y - bh * 0.40) * d.s,
                                    (tag_x + bw * 0.60) * d.s, (tag_y + bh * 0.40) * d.s],
                                   radius=int(6 * s * d.s), fill=(252, 246, 232))
            f = font(max(7, int(13 * s)))
            d._d.text((tag_x * d.s, tag_y * d.s), name.upper()[:6], font=f,
                      fill=(96, 78, 58), anchor="mm")
        else:
            ell(46, -172, 13, 13, (250, 206, 92))              # plain disc tag
            ell(46, -172, 6, 6, _blend((250, 206, 92), ink, 0.35))

    # ---- head
    hx, hy = 16, -252
    # A helmet bubble is drawn BEHIND the head; only its rim and glint go on
    # top later. Filling glass over the face would hide the whole performance.
    if outfit == "helmet":
        ell(hx + 2, hy - 8, 110, 106, (214, 230, 244))
        ell(hx + 2, hy - 8, 100, 96, (186, 218, 242))
    # ears go behind the skull so the head reads as in front of them
    for off, tone in ((-74, tuple(max(0, int(v * 0.86)) for v in ec)), (76, ec)):
        ell(hx + off, hy + 22, 27, 58, tone)
        ell(hx + off, hy + 34, 15, 34, _blend(tone, ink, 0.18))   # inner shadow
    ell(hx, hy, 76, 70, c)
    # A soft crown highlight only. A second, brighter brow ridge on top of this
    # merged with the brows into one grey slab across the eyes.
    ell(hx - 6, hy - 40, 48, 22, _blend(c, white, 0.09))
    if collie:
        # The blaze: a white wedge running from between the ears down over the
        # bridge of the nose. It has to sit between the eyes, not across them,
        # so it is narrow at the top and widens only once past the brow.
        d.polygon([P(hx - 19, hy - 64), P(hx - 7, hy - 64),
                   P(hx + 2, hy + 16), P(hx - 26, hy + 16)], fill=white)
        ell(hx - 13, hy - 60, 8, 9, white)

    # ---- snout: raised muzzle in front of the face, then the nose on top
    ell(hx + 34, hy + 32, 48, 36, _blend(cream, c, 0.10))
    ell(hx + 30, hy + 24, 42, 26, cream)
    ell(hx + 58, hy + 14, 15, 12, ink)                        # nose
    ell(hx + 54, hy + 10, 5, 4, _blend(ink, white, 0.55))     # nose shine

    # ---- eyes: sclera, iris, pupil, catchlight. The catchlight is what makes
    # the difference between "two dots" and something that looks alive.
    def eye(ex, ey, rx, ry):
        ell(ex, ey, rx, ry, white)
        ell(ex + 1, ey + 1, rx * 0.72, ry * 0.72, _blend(ink, (90, 140, 190), 0.45))
        ell(ex + 1, ey + 1, rx * 0.42, ry * 0.42, ink)
        ell(ex - rx * 0.34, ey - ry * 0.38, rx * 0.26, ry * 0.26, white)

    if expression == "laugh":
        for ex in (hx + 10, hx - 42):                          # happy closed arcs
            chord(ex, hy - 14, 15, 13, 200, 340, ink, width=6)
    elif expression == "surprised":
        eye(hx + 10, hy - 14, 17, 19)
        eye(hx - 42, hy - 12, 14, 16)
    else:
        eye(hx + 10, hy - 14, 14, 16)
        eye(hx - 42, hy - 12, 12, 14)

    brow = _blend(ec, ink, 0.35)
    if expression == "smug":
        d.line([P(hx - 16, hy - 42), P(hx + 24, hy - 34)], fill=brow, width=int(8 * s))
        d.line([P(hx - 58, hy - 34), P(hx - 30, hy - 40)], fill=brow, width=int(7 * s))
    elif expression == "surprised":
        chord(hx + 10, hy - 44, 20, 14, 190, 350, brow, width=7)
        chord(hx - 42, hy - 42, 17, 12, 190, 350, brow, width=6)
    elif expression == "deadpan":
        d.line([P(hx - 4, hy - 40), P(hx + 26, hy - 40)], fill=brow, width=int(7 * s))
        d.line([P(hx - 56, hy - 38), P(hx - 30, hy - 38)], fill=brow, width=int(6 * s))

    # ---- mouth
    if speaking:
        # Open jaw: a wide dark cavity, a tongue filling the lower half, and a
        # strip of teeth along the top so it reads as a mouth, not a hole.
        mh = 34 if expression == "laugh" else 26
        ell(hx + 34, hy + 50, 34, mh, _blend(ink, gum, 0.30))
        d.chord(_box(hx + 34, hy + 50, 34, mh), 0, 180, fill=gum)
        if tongue:
            ell(hx + 34, hy + 50 + mh * 0.40, 21, mh * 0.52, (240, 146, 158))
            d.line([P(hx + 34, hy + 50 + mh * 0.10), P(hx + 34, hy + 50 + mh * 0.80)],
                   fill=_blend((240, 146, 158), ink, 0.22), width=max(1, int(3 * s)))
        rrect(hx + 34, hy + 50 - mh * 0.78, 26, mh * 0.16, white, radius=6)
        # little sound arcs, so the speaker is obvious even in a thumbnail crop
        for i, r in enumerate((22, 38, 54)):
            chord(hx + 96, hy + 34, r, r, 300, 60, _blend(ink, white, 0.45 + i * 0.14),
                  width=5)
    else:
        chord(hx + 32, hy + 30, 30, 24, 20, 160, ink, width=7)

    for cx in (hx - 38, hx + 66):                              # cheeks
        ell(cx, hy + 24, 15, 10, (252, 176, 176))

    _dog_headgear(d, P, ell, rrect, chord, s, sgn, hx, hy, outfit, ink, white)
    if holding:
        _dog_prop(d, P, ell, rrect, chord, s, sgn, holding, ink, white)


def _blend(a, b, t: float):
    """Mix two RGB colours. Used everywhere the dog needs a tone between two
    palette entries without inventing a new constant for each one."""
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def _dog_suit(d, P, ell, rrect, s, sgn, outfit, ink, white):
    """Body-worn kit, drawn over the torso before the head goes on."""
    if outfit == "helmet":
        # A proper EVA suit, not a bib. The first version was one white
        # rounded rectangle on the chest, which read as an apron: the haunch
        # and legs stayed bare fur, so the dog looked undressed from behind.
        suit = (240, 243, 249)
        seam = (206, 214, 228)
        ell(-48, -74, 66, 74, suit)                            # haunch cover
        ell(-52, -84, 46, 50, (250, 252, 255))
        ell(6, -130, 74, 82, suit)                             # torso
        ell(14, -112, 42, 52, (250, 252, 255))
        for lx in (26, 78):                                    # sleeves
            rrect(lx, -44, 24, 36, suit, radius=22)
            rrect(lx, -30, 24, 7, (240, 168, 72), radius=4)    # cuff stripe
        rrect(6, -178, 52, 15, seam, radius=8)                 # neck ring
        rrect(-2, -152, 62, 9, seam, radius=5)                 # shoulder seam
        # chest control panel
        rrect(2, -120, 32, 24, (74, 92, 128), radius=7)
        rrect(2, -128, 26, 6, (150, 172, 206), radius=3)
        for i, col in enumerate(((234, 96, 96), (250, 206, 92), (126, 214, 244))):
            ell(-10 + i * 11, -114, 4, 4, col)
        rrect(52, -140, 9, 34, (240, 168, 72), radius=5)       # air hose
        rrect(-34, -168, 26, 10, (234, 96, 96), radius=4)      # mission flash
    elif outfit == "rainhat":
        rrect(6, -132, 70, 72, (250, 206, 92), radius=32)      # yellow slicker
        rrect(6, -176, 40, 14, (232, 186, 72), radius=7)
        for by in (-150, -120):
            ell(6, by, 6, 6, (232, 186, 72))
    elif outfit == "beanie":
        rrect(6, -140, 62, 40, (206, 92, 108), radius=26)      # knitted jumper
        for sy in (-152, -134):
            d.line([P(-52, sy), P(64, sy)], fill=(186, 76, 94), width=int(5 * s))
    elif outfit == "chef":
        # Blue gingham apron, as in the reference. The check is drawn as a
        # coarse grid rather than a texture — at 1080p a finer weave turns to
        # mush once the frame is scaled down for the Short.
        ax0, ax1, ay0, ay1 = -46, 66, -184, -60
        rrect(10, -122, 58, 64, (238, 244, 252), radius=14)
        # Grid segments are clamped to the apron's own box; drawn full-width
        # they ran straight off the cloth and striped the dog's legs.
        for gx in range(ax0 + 8, ax1, 22):
            d.line([P(gx, ay0), P(gx, ay1)], fill=(126, 168, 218), width=int(9 * s))
        for gy in range(ay0 + 8, ay1, 22):
            d.line([P(ax0, gy), P(ax1, gy)], fill=(126, 168, 218), width=int(9 * s))
        for tie in (-26, 46):                                  # neck ties
            d.line([P(tie, -190), P(10, -156)], fill=(238, 244, 252), width=int(8 * s))


def _dog_headgear(d, P, ell, rrect, chord, s, sgn, hx, hy, outfit, ink, white):
    """Head-worn kit, drawn last so it sits on top of the face."""
    if outfit in ("shades", "redshades"):
        # Goofy wears black frames, Woofy red — the reference gives them
        # different glasses, and it is one more way to tell them apart.
        frame = (196, 62, 58) if outfit == "redshades" else ink
        rrect(hx - 8, hy - 14, 66, 20, frame, radius=10)
        ell(hx + 12, hy - 14, 24, 18, (36, 40, 58))
        ell(hx - 44, hy - 12, 21, 16, (36, 40, 58))
        d.line([P(hx + 6, hy - 20), P(hx + 20, hy - 26)], fill=white, width=int(5 * s))
    elif outfit == "chef":
        # Toque: a tall pleated puff on a band.
        rrect(hx - 2, hy - 74, 54, 16, (250, 250, 248), radius=8)      # band
        for px_, r in ((-38, 30), (-2, 34), (34, 29)):
            ell(hx + px_, hy - 108, r, r, (252, 252, 250))
        rrect(hx - 2, hy - 108, 52, 30, (252, 252, 250), radius=16)
    elif outfit == "cap":
        # Worn backwards, like the driving panel in the reference.
        chord(hx - 2, hy - 40, 72, 56, 180, 360, (58, 106, 174))
        rrect(hx - 2, hy - 44, 72, 12, (48, 92, 156), radius=6)
        rrect(hx - 62, hy - 46, 26, 10, (58, 106, 174), radius=5)     # rear peak
        ell(hx - 2, hy - 82, 9, 9, (48, 92, 156))                     # button
    elif outfit == "helmet":
        # The glass itself went in behind the head; up here only the rim and a
        # glint, which is what sells "inside a bubble" without hiding the face.
        chord(hx + 2, hy - 8, 110, 106, 0, 360, (236, 244, 252), width=8)
        chord(hx + 2, hy - 8, 100, 96, 168, 252, white, width=10)  # glass glint
        chord(hx + 2, hy - 8, 88, 84, 200, 232, white, width=5)
        rrect(hx + 2, hy + 78, 76, 15, (214, 222, 234), radius=7)  # neck seal
    elif outfit == "beanie":
        chord(hx - 2, hy - 40, 78, 62, 180, 360, (206, 92, 108))
        rrect(hx - 2, hy - 48, 78, 13, (232, 122, 138), radius=7)
        ell(hx - 2, hy - 100, 20, 20, (248, 236, 226))              # bobble
    elif outfit == "rainhat":
        # Crown and brim both ride high: at the old height the brim cut across
        # the eyes and the dog lost its face entirely.
        chord(hx - 2, hy - 44, 74, 58, 180, 360, (250, 206, 92))
        rrect(hx + 6, hy - 46, 92, 11, (232, 186, 72), radius=6)    # brim
    elif outfit == "partyhat":
        d.polygon([P(hx - 2, hy - 150), P(hx - 44, hy - 56), P(hx + 40, hy - 56)],
                  fill=(126, 200, 240))
        ell(hx - 2, hy - 152, 14, 14, (250, 206, 92))


def _dog_prop(d, P, ell, rrect, chord, s, sgn, holding, ink, white):
    """Something in the near front paw, at (78, -38)-ish in dog space."""
    px, py = 96, -58
    if holding == "beer":
        # Mug: amber body, foam head, handle. Held clear of the chest so it
        # does not merge into the coat.
        rrect(px, py, 30, 40, (246, 178, 52), radius=8)
        rrect(px, py + 12, 30, 26, (232, 152, 36), radius=8)
        ell(px, py - 34, 32, 16, (255, 252, 244))              # foam
        ell(px - 14, py - 42, 13, 11, (255, 252, 244))
        ell(px + 16, py - 40, 11, 9, (255, 252, 244))
        chord(px + 40, py, 20, 22, 270, 90, (232, 152, 36), width=9)   # handle
        rrect(px - 10, py - 6, 6, 22, (255, 226, 150), radius=3)   # glass shine
    elif holding == "marshmallow":
        d.line([P(px - 30, py + 46), P(px + 34, py - 48)], fill=(146, 108, 72),
               width=int(7 * s))
        rrect(px + 36, py - 54, 16, 18, (255, 250, 240), radius=7)
        ell(px + 36, py - 54, 16, 8, (244, 214, 178))
    elif holding == "ball":
        ell(px, py + 10, 34, 34, (238, 92, 92))
        ell(px - 10, py, 12, 10, (250, 158, 158))
        d.line([P(px - 30, py + 10), P(px + 30, py + 10)], fill=(206, 62, 62),
               width=int(5 * s))
    elif holding == "mug":
        # The diner mug from the reference: straight sides, a band for the
        # slogan, steam curling off the top.
        rrect(px, py + 4, 30, 34, (66, 126, 190), radius=7)
        rrect(px, py + 6, 30, 14, (246, 250, 254), radius=4)   # slogan band
        ell(px, py - 30, 30, 11, (250, 252, 255))              # rim
        ell(px, py - 30, 22, 7, (72, 52, 38))                  # coffee
        chord(px + 38, py + 2, 18, 20, 270, 90, (54, 108, 168), width=9)
        for i, sx in enumerate((-12, 4, 18)):                  # steam
            chord(px + sx, py - 62 - i * 6, 11, 16, 200, 340,
                  _blend((255, 255, 255), (200, 214, 230), 0.4), width=5)
    elif holding == "spatula":
        d.line([P(px - 6, py + 48), P(px + 16, py - 30)], fill=(64, 68, 84),
               width=int(9 * s))
        rrect(px + 20, py - 46, 20, 16, (98, 104, 122), radius=5)
        for slot in (-9, 0, 9):                                # slots
            d.line([P(px + 20 + slot, py - 56), P(px + 20 + slot, py - 36)],
                   fill=(70, 74, 90), width=int(4 * s))
    elif holding == "treats":
        # A bowl of biscuits, plus two bones spilled in front of it.
        chord(px, py + 24, 44, 34, 0, 180, (58, 116, 180))
        ell(px, py + 24, 44, 12, (78, 140, 206))
        for bx, by in ((-16, 18), (2, 14), (18, 20)):
            ell(px + bx, py + by, 11, 9, (214, 158, 92))
        for bone_x in (-58, -30):
            ell(px + bone_x, py + 52, 7, 6, (238, 206, 150))
            ell(px + bone_x + 18, py + 52, 7, 6, (238, 206, 150))
            rrect(px + bone_x + 9, py + 52, 11, 4, (238, 206, 150), radius=2)


def hare(d: ScaledDraw, x: int, y: int, scale: float = 1.0, facing: str = "right",
         fur=None, running: bool = False, ears: str = "up", mouth: str = "smile"):
    """Cartoon hare with its feet at (x, y). ears: up | back | one_down.

    `running` leans the body forward and stretches the legs -- the pose the
    fable needs for "shot away in a cloud of dust". `ears="back"` reads as
    speed; a sleeping hare wants ears="one_down".
    """
    s = scale
    sgn = 1 if facing == "right" else -1
    f = fur or (216, 206, 196)
    dk = (188, 176, 166)
    ink = PALETTE["ink"]

    def P(px, py):
        return (x + px * sgn * s, y + py * s)

    def ell(cx, cy, rx, ry, fill):
        a, b = P(cx - rx, cy - ry), P(cx + rx, cy + ry)
        d.ellipse([min(a[0], b[0]), min(a[1], b[1]),
                   max(a[0], b[0]), max(a[1], b[1])], fill=fill)

    lean = -18 if running else 0
    register_box("hare", (x - 150 * s, y - 300 * s, x + 150 * s, y + 10 * s))

    # tail
    ell(-78 + lean, -78, 24, 24, (238, 232, 226))
    # hind leg
    if running:
        d.polygon([P(-58, -22), P(-126, 2), P(-118, 22), P(-40, 6)], fill=dk)
        ell(-122, 12, 20, 14, dk)
    else:
        ell(-52, -24, 38, 28, dk)
    # body, leaning forward when running
    ell(lean * 0.5, -74, 76, 58, f)
    # front leg
    if running:
        d.polygon([P(34, -44), P(104, -18), P(96, 2), P(24, -22)], fill=dk)
        ell(100, -8, 20, 14, dk)
    else:
        ell(46, -20, 26, 24, dk)
    # head
    hx, hy = 58 + lean, -142
    ell(hx, hy, 46, 42, f)
    # Ears: tall ellipses, not polygon slivers -- a thin quad reads as a stick.
    pink = (246, 196, 200)
    for i, off in enumerate((-18, 20)):
        if ears == "back":
            # laid flat along the back: reads as speed
            ell(hx - 52 - i * 16, hy - 34 + i * 22, 62, 19, f)
            ell(hx - 52 - i * 16, hy - 34 + i * 22, 46, 10, pink)
        elif ears == "one_down" and i == 1:
            ell(hx + off + 24, hy + 22, 20, 50, f)
            ell(hx + off + 24, hy + 22, 11, 36, pink)
        else:
            ell(hx + off, hy - 78, 22, 62, f)
            ell(hx + off, hy - 78, 12, 46, pink)
    # face
    ell(hx + 20, hy - 6, 8, 10, ink)
    ell(hx + 40, hy + 6, 8, 7, (240, 150, 160))          # nose
    if mouth == "smile":
        a, b = P(hx + 20, hy + 10), P(hx + 46, hy + 30)
        d.chord([min(a[0], b[0]), min(a[1], b[1]),
                 max(a[0], b[0]), max(a[1], b[1])], 20, 160, fill=ink)
    ell(hx - 2, hy + 16, 12, 8, (250, 178, 178))          # cheek


def tortoise(d: ScaledDraw, x: int, y: int, scale: float = 1.0, facing: str = "right",
             shell=None, skin=None, tucked: bool = False, mouth: str = "smile"):
    """Cartoon tortoise with its feet at (x, y).

    `tucked` pulls the head into the shell. The shell is a dome with visible
    scutes because a plain half-ellipse reads as a rock.
    """
    s = scale
    sgn = 1 if facing == "right" else -1
    sh = shell or (166, 124, 74)
    sh_dk = (138, 100, 58)
    sk = skin or (126, 176, 118)
    sk_dk = (104, 152, 98)
    ink = PALETTE["ink"]

    def P(px, py):
        return (x + px * sgn * s, y + py * s)

    def ell(cx, cy, rx, ry, fill):
        a, b = P(cx - rx, cy - ry), P(cx + rx, cy + ry)
        d.ellipse([min(a[0], b[0]), min(a[1], b[1]),
                   max(a[0], b[0]), max(a[1], b[1])], fill=fill)

    register_box("tortoise", (x - 170 * s, y - 190 * s, x + 170 * s, y + 10 * s))

    # legs first, so the shell overlaps their tops
    for lx in (-70, 40):
        a, b = P(lx - 30, -56), P(lx + 30, 0)
        d.rounded_rectangle([min(a[0], b[0]), min(a[1], b[1]),
                             max(a[0], b[0]), max(a[1], b[1])],
                            radius=26 * s, fill=sk_dk)
    # tail
    d.polygon([P(-100, -62), P(-152, -40), P(-100, -30)], fill=sk)
    # head and neck
    if not tucked:
        a, b = P(70, -104), P(132, -50)
        d.rounded_rectangle([min(a[0], b[0]), min(a[1], b[1]),
                             max(a[0], b[0]), max(a[1], b[1])],
                            radius=26 * s, fill=sk)
        ell(136, -102, 46, 42, sk)
        ell(152, -114, 8, 10, ink)
        ell(120, -84, 13, 9, (150, 198, 140))
        if mouth == "smile":
            a, b = P(134, -104), P(170, -78)
            d.chord([min(a[0], b[0]), min(a[1], b[1]),
                     max(a[0], b[0]), max(a[1], b[1])], 20, 160, fill=ink)
    # shell: dome, then a slim rim. A deep rim reads as a table, not a shell.
    a, b = P(-118, -186), P(118, -34)
    d.pieslice([min(a[0], b[0]), min(a[1], b[1]),
                max(a[0], b[0]), max(a[1], b[1])], 180, 360, fill=sh)
    a, b = P(-124, -48), P(124, -26)
    d.rounded_rectangle([min(a[0], b[0]), min(a[1], b[1]),
                         max(a[0], b[0]), max(a[1], b[1])],
                        radius=11 * s, fill=sh_dk)
    # scutes -- what makes it read as a shell rather than a rock
    for cx, cy, r in ((0, -132, 34), (-62, -104, 27), (62, -104, 27),
                      (-102, -78, 18), (102, -78, 18)):
        d.polygon([P(cx + r * math.cos(math.radians(a2)),
                     cy + r * math.sin(math.radians(a2))) for a2 in range(0, 360, 60)],
                  fill=sh_dk)


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


def planet(d: ScaledDraw, x: int, y: int, r: float = 200, tilt: float = 23.5,
           axis: bool = True, land: bool = True, night: str | None = None,
           seed: int = 3, ocean=None, land_color=None, face: bool = False):
    """Tilted Earth. `night` shades the half facing away: 'left' or 'right'.

    tilt is the axial tilt in degrees -- the whole reason seasons exist, so it
    is a first-class parameter rather than a decoration.
    """
    oc = ocean or (74, 148, 216)
    lc = land_color or (108, 196, 108)
    d.ellipse([x - r, y - r, x + r, y + r], fill=oc)

    if land:      # deterministic continent blobs, not a map -- just readable land
        rnd = random.Random(seed)
        for _ in range(7):
            a = rnd.uniform(0, 2 * math.pi)
            dist = rnd.uniform(0.1, 0.62) * r
            bx, by = x + math.cos(a) * dist, y + math.sin(a) * dist
            bw, bh = rnd.uniform(0.22, 0.40) * r, rnd.uniform(0.16, 0.30) * r
            d.ellipse([bx - bw, by - bh, bx + bw, by + bh], fill=lc)
            d.ellipse([bx - bw * 0.5, by - bh * 1.3, bx + bw * 0.9, by + bh * 0.5],
                      fill=lc)

    a = math.radians(tilt)
    # ice caps sit on the tilted poles, which is what makes the tilt legible
    for sgn in (-1, 1):
        px = x + math.sin(a) * r * 0.82 * sgn
        py = y - math.cos(a) * r * 0.82 * sgn
        cap = r * 0.3
        d.ellipse([px - cap, py - cap * 0.72, px + cap, py + cap * 0.72],
                  fill=(238, 246, 255))

    if night in ("left", "right"):
        start, end = (90, 270) if night == "left" else (270, 90)
        d.pieslice([x - r, y - r, x + r, y + r], start, end, fill=(28, 42, 92))
        d.pieslice([x - r * 0.99, y - r * 0.99, x + r * 0.99, y + r * 0.99],
                   start, end, fill=(38, 56, 112))

    if axis:
        ax = math.sin(a) * r * 1.28
        ay = math.cos(a) * r * 1.28
        d.line([(x - ax, y + ay), (x + ax, y - ay)], fill=PALETTE["ink"], width=8)
        for sgn in (-1, 1):
            tipx, tipy = x + ax * sgn, y - ay * sgn
            d.ellipse([tipx - 12, tipy - 12, tipx + 12, tipy + 12], fill=PALETTE["ink"])

    if face:
        for sx in (-0.28, 0.28):
            d.ellipse([x + r * sx - r * 0.07, y - r * 0.14,
                       x + r * sx + r * 0.07, y - r * 0.02], fill=PALETTE["ink"])
        d.chord([x - r * 0.3, y - r * 0.02, x + r * 0.3, y + r * 0.34],
                20, 160, fill=PALETTE["ink"])
    register_box("planet", (x - r * 1.3, y - r * 1.3, x + r * 1.3, y + r * 1.3))


def orbit_ring(d: ScaledDraw, cx: int, cy: int, rx: float, ry: float,
               color=None, width: int = 7, dashes: int = 56):
    """Dashed orbit path. Nearly circular, because Earth's orbit nearly is."""
    col = color or (255, 255, 255)
    for i in range(dashes):
        a0 = 2 * math.pi * i / dashes
        a1 = a0 + math.pi / dashes
        d.line([(cx + math.cos(a0) * rx, cy + math.sin(a0) * ry),
                (cx + math.cos(a1) * rx, cy + math.sin(a1) * ry)],
               fill=col, width=width)


def light_beam(d: ScaledDraw, start, end, n: int = 5, spacing: float = 74,
               color=None, width: int = 11, arrow_head: float = 30):
    """n parallel light rays, all pointing start -> end.

    Slant the pair and the same rays cover more ground: that is the entire
    seasons explanation in one primitive.
    """
    col = color or PALETTE["accent"]
    (x1, y1), (x2, y2) = start, end
    dx, dy = x2 - x1, y2 - y1
    L = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / L, dx / L          # unit normal to the beam
    for i in range(n):
        off = (i - (n - 1) / 2.0) * spacing
        arrow(d, (x1 + nx * off, y1 + ny * off), (x2 + nx * off, y2 + ny * off),
              color=col, width=width, head=arrow_head)


def raindrop(d: ScaledDraw, x: int, y: int, size: float = 44, color=None,
             shine: bool = True):
    """Classic teardrop: round belly, pointed top."""
    c = color or (108, 186, 244)
    w = size * 0.72
    d.ellipse([x - w, y - w * 0.86, x + w, y + w * 1.06], fill=c)
    d.polygon([(x, y - size * 1.55), (x - w * 0.94, y + size * 0.08),
               (x + w * 0.94, y + size * 0.08)], fill=c)
    if shine and size >= 24:
        d.ellipse([x - w * 0.52, y - w * 0.42, x - w * 0.12, y + w * 0.18],
                  fill=(206, 236, 255))


def rainfall(d: ScaledDraw, area, n: int = 40, seed: int = 7, size=(16, 30),
             color=None, streaks: bool = True):
    """Scatter of falling drops. Convenience wrapper over raindrop()."""
    rnd = random.Random(seed)
    x0, y0, x1, y1 = area
    for _ in range(n):
        x = rnd.uniform(x0, x1)
        y = rnd.uniform(y0, y1)
        sz = rnd.uniform(*size)
        if streaks and rnd.random() < 0.45:
            d.line([(x, y - sz * 2.6), (x, y - sz * 1.4)],
                   fill=color or (150, 208, 250), width=max(3, int(sz * 0.22)))
        raindrop(d, x, y, sz, color=color, shine=sz > 22)


def puddle(d: ScaledDraw, x: int, y: int, w: float = 300, h: float = 70,
           color=None, shine: bool = True):
    """Shallow pool of water, seen from a low angle."""
    c = color or (92, 170, 232)
    d.ellipse([x - w, y - h, x + w, y + h], fill=c)
    d.ellipse([x - w * 0.94, y - h * 0.9, x + w * 0.94, y + h * 0.62],
              fill=(120, 194, 246))
    if shine:
        d.ellipse([x - w * 0.52, y - h * 0.42, x - w * 0.06, y - h * 0.06],
                  fill=(206, 236, 255))


def cycle_arrow(d: ScaledDraw, cx: int, cy: int, rx: float, ry: float,
                start_deg: float, end_deg: float, color=None, width: int = 14,
                head: float = 46, dashed: bool = False):
    """Curved arrow following an ellipse -- the water cycle's connective tissue."""
    col = color or PALETTE["white"]
    steps = max(12, int(abs(end_deg - start_deg) / 3))
    pts = []
    for i in range(steps + 1):
        t = start_deg + (end_deg - start_deg) * i / steps
        a = math.radians(t)
        pts.append((cx + math.cos(a) * rx, cy + math.sin(a) * ry))
    if dashed:
        for i in range(0, len(pts) - 1, 2):
            d.line([pts[i], pts[i + 1]], fill=col, width=width)
    else:
        d.line(pts, fill=col, width=width, joint="curve")
    # head aligned with the tangent at the end of the arc
    (px, py), (qx, qy) = pts[-2], pts[-1]
    a = math.atan2(qy - py, qx - px)
    d.polygon([(qx, qy),
               (qx - math.cos(a - 0.42) * head, qy - math.sin(a - 0.42) * head),
               (qx - math.cos(a + 0.42) * head, qy - math.sin(a + 0.42) * head)],
              fill=col)


def sea(d: ScaledDraw, y: int = 760, color=None, deep=None, amp: float = 16,
        wavelength: float = 300, phase: float = 0.0, foam: bool = True):
    """Ocean filling everything below `y`, with a rolling surface.

    The surface is a real sine, not a straight line with squiggles on top, so
    two scenes at different phases read as the same sea moving.
    """
    c = color or (72, 156, 214)
    dp = deep or (44, 116, 176)
    pts = []
    for px in range(-20, W + 21, 12):
        pts.append((px, y + math.sin(phase + px / max(20.0, wavelength) * 2 * math.pi) * amp))
    d.polygon(pts + [(W + 20, H + 20), (-20, H + 20)], fill=c)
    # a darker band a little further down gives the water depth
    deep_pts = [(px, py + 78) for px, py in pts]
    d.polygon(deep_pts + [(W + 20, H + 20), (-20, H + 20)], fill=dp)
    if foam:
        d.line(pts, fill=(226, 244, 255), width=9, joint="curve")


def wave(d: ScaledDraw, x: int, y: int, width: float = 520, scale: float = 1.0,
         color=None, deep=None, foam: bool = True):
    """One breaking swell centered on (x, y) -- the 'sea' icon, not a whole ocean.

    The crest sits left of centre and the face is steeper on the right, which is
    what stops a wave reading as a symmetrical hill (a triangle with a white cap
    is a mountain, and the first version of this primitive was exactly that).
    """
    c = color or (72, 156, 214)
    dp = deep or (44, 116, 176)
    s = scale
    w = width / 2.0
    h = 172 * s
    crest_u = -0.16                     # crest offset across the width, -1..1

    def profile(u):
        """Height of the swell at u in -1..1: one hump, leaning forward."""
        skew = 1.5 if u > crest_u else 2.4      # gentle back, steep face
        return h * math.exp(-((u - crest_u) * skew) ** 2)

    # the swell sits ON a water line: a deep slab under it reads as a block, so
    # the skirt is only just enough to overlap whatever sea() drew
    base = y + 34 * s
    top = [(x + w * (i / 40.0 * 2 - 1), y - profile(i / 40.0 * 2 - 1))
           for i in range(41)]
    d.polygon(top + [(x + w, base), (x - w, base)], fill=c)
    # a soft shadow down the face gives the curl its depth
    d.polygon([(x + w * crest_u, y - h * 0.96),
               (x + w * (crest_u + 0.44), y - h * 0.34),
               (x + w * (crest_u + 0.26), base),
               (x + w * (crest_u - 0.06), base)], fill=dp)

    if foam:
        # a crescent of foam spilling forward off the crest
        cap = []
        for i in range(25):
            u = crest_u - 0.42 + (i / 24.0) * 0.92
            cap.append((x + w * u, y - profile(u)))
        for i in range(24, -1, -1):
            u = crest_u - 0.42 + (i / 24.0) * 0.92
            drop = 26 * s + 34 * s * max(0.0, (u - crest_u) / 0.5)
            cap.append((x + w * u, y - profile(u) + drop))
        d.polygon(cap, fill=(226, 244, 255))
        for i, k in enumerate((0.56, 0.74, 0.90)):
            r = (17 - i * 4) * s
            fx, fy = x + w * k, y - profile(k) + 24 * s
            d.ellipse([fx - r, fy - r, fx + r, fy + r], fill=(226, 244, 255))


def salt_crystal(d: ScaledDraw, x: int, y: int, size: float = 90, color=None,
                 sparkle: bool = True, rotate: float = 0.0):
    """A grain of salt, drawn as the cube it actually is.

    Salt crystals really are cubic -- teaching the shape costs nothing and it is
    the detail children repeat back.
    """
    s = size / 2.0
    top = color or (250, 252, 255)
    left = (214, 228, 244)
    right = (232, 240, 250)
    a = math.radians(rotate)

    def P(px, py):
        return (x + px * math.cos(a) - py * math.sin(a),
                y + px * math.sin(a) + py * math.cos(a))

    # isometric cube: top rhombus, then the two visible side faces
    d.polygon([P(0, -s), P(s, -s * 0.5), P(0, 0), P(-s, -s * 0.5)], fill=top)
    d.polygon([P(-s, -s * 0.5), P(0, 0), P(0, s), P(-s, s * 0.5)], fill=left)
    d.polygon([P(s, -s * 0.5), P(0, 0), P(0, s), P(s, s * 0.5)], fill=right)
    if sparkle and size >= 40:
        for dx, dy, r in ((-0.72, -0.72, 0.13), (0.78, -0.46, 0.09)):
            sx, sy = x + s * dx * 1.5, y + s * dy * 1.5
            rr = size * r
            d.line([(sx - rr, sy), (sx + rr, sy)], fill=PALETTE["white"], width=5)
            d.line([(sx, sy - rr), (sx, sy + rr)], fill=PALETTE["white"], width=5)


def mountain(d: ScaledDraw, x: int, y: int, w: float = 520, h: float = 420,
             color=None, shade=None, snow: bool = True):
    """Rocky peak with its feet on `y` and its summit at `y - h`."""
    rock = color or (128, 122, 148)
    dark = shade or (98, 94, 120)
    d.polygon([(x - w / 2, y), (x, y - h), (x + w / 2, y)], fill=rock)
    # the shaded face makes it read as a solid, not a triangle
    d.polygon([(x, y - h), (x + w / 2, y), (x, y)], fill=dark)
    if snow:
        cap = h * 0.30
        k = cap / h
        d.polygon([(x, y - h),
                   (x + w / 2 * k, y - h + cap),
                   (x + w * 0.10 * k, y - h + cap * 0.72),
                   (x - w * 0.08 * k, y - h + cap),
                   (x - w / 2 * k, y - h + cap)], fill=(240, 248, 255))


def river(d: ScaledDraw, points, width: float = 70, color=None, taper: float = 1.0,
          shine: bool = True):
    """Water running along `points`, optionally widening toward the sea."""
    c = color or (96, 178, 232)
    raw = list(points)
    if len(raw) < 2:
        return
    # subdivide before walking the path: drawing one segment per control point
    # made the width jump in visible steps wherever the river widened
    pts = []
    for i in range(len(raw) - 1):
        (ax, ay), (bx, by) = raw[i], raw[i + 1]
        for k in range(8):
            t = k / 8.0
            pts.append((ax + (bx - ax) * t, ay + (by - ay) * t))
    pts.append(raw[-1])

    for i in range(len(pts) - 1):
        t = i / max(1, len(pts) - 2)
        wdt = max(4, width * (1.0 + (taper - 1.0) * t))
        d.line([pts[i], pts[i + 1]], fill=c, width=int(wdt), joint="curve")
        r = wdt / 2.0
        px, py = pts[i + 1]
        d.ellipse([px - r, py - r, px + r, py + r], fill=c)
    if shine:
        # a highlight running along the water, offset along the path's own
        # normal -- offsetting in y alone left it hanging off a steep stretch
        hi = []
        for i, (px, py) in enumerate(pts):
            ax, ay = pts[max(0, i - 1)]
            bx, by = pts[min(len(pts) - 1, i + 1)]
            L = math.hypot(bx - ax, by - ay) or 1.0
            nx, ny = -(by - ay) / L, (bx - ax) / L
            t = i / max(1, len(pts) - 1)
            wdt = width * (1.0 + (taper - 1.0) * t)
            hi.append((px + nx * wdt * 0.22, py + ny * wdt * 0.22))
        d.line(hi, fill=(206, 236, 255), width=max(3, int(width * 0.22)),
               joint="curve")


def prism(d: ScaledDraw, x: int, y: int, size: float = 260, color=None):
    """Glass triangle used for the rainbow-splitting demo."""
    c = color or PALETTE["prism_glass"]
    h = size * 0.87
    pts = [(x, y - h * 0.62), (x - size * 0.5, y + h * 0.38), (x + size * 0.5, y + h * 0.38)]
    d.polygon(pts, fill=c, outline=PALETTE["white"], width=8)
    d.line([pts[0], pts[1]], fill=(255, 255, 255), width=10)


# --------------------------------------------------------------------------
# Interiors and set dressing
#
# The dad-jokes cast spends most of its time indoors, and every setting the
# reference art suggests -- a couch, a kitchen, a car -- needs a room rather
# than a sky. These are deliberately blunt: a few large flat shapes that read
# instantly at Short size, with the detail carried by two or three props rather
# than by texture.
# --------------------------------------------------------------------------

def room(d: ScaledDraw, floor_y: int = 880, wall=None, floor=None,
         skirting: bool = True):
    """Interior wall and floor. Use with canvas("plain")."""
    w = wall or (238, 226, 208)
    f = floor or (196, 162, 126)
    d.rectangle([0, 0, W, floor_y], fill=w)
    d.rectangle([0, floor_y, W, H], fill=f)
    d.rectangle([0, floor_y, W, floor_y + 10], fill=_blend(f, PALETTE["ink"], 0.22))
    if skirting:
        d.rectangle([0, floor_y - 34, W, floor_y], fill=_blend(w, PALETTE["white"], 0.55))
        d.rectangle([0, floor_y - 38, W, floor_y - 30], fill=_blend(w, PALETTE["ink"], 0.12))


def wallpaper_stripes(d: ScaledDraw, floor_y: int = 880, color=None, step: int = 120):
    """Faint vertical stripes, so a big flat wall is not a dead rectangle."""
    c = color or (228, 214, 194)
    for x in range(0, W, step):
        d.rectangle([x, 0, x + step // 2, floor_y], fill=c)


def couch(d: ScaledDraw, x: int, y: int, w: float = 900, h: float = 260,
          color=None, cushions: int = 3):
    """Sofa seen head-on, its seat at y. The characters sit in front of it."""
    c = color or (150, 160, 186)
    dark = _blend(c, PALETTE["ink"], 0.22)
    light = _blend(c, PALETTE["white"], 0.16)
    back_h = h * 1.15
    d.rounded_rectangle([x - w / 2, y - h - back_h, x + w / 2, y - h * 0.2],
                        radius=46, fill=c)
    for i in range(cushions):                       # back cushions
        cw = w / cushions
        cx = x - w / 2 + cw * (i + 0.5)
        d.rounded_rectangle([cx - cw * 0.42, y - h - back_h * 0.86,
                             cx + cw * 0.42, y - h * 0.5], radius=34, fill=light)
    d.rounded_rectangle([x - w / 2, y - h, x + w / 2, y], radius=38, fill=dark)
    for arm in (-1, 1):                             # arms
        d.rounded_rectangle([x + arm * w / 2 - 52, y - h - back_h * 0.55,
                             x + arm * w / 2 + 52, y], radius=40, fill=dark)


def rug(d: ScaledDraw, x: int, y: int, w: float = 900, h: float = 120, color=None):
    c = color or (204, 122, 108)
    d.ellipse([x - w / 2, y - h / 2, x + w / 2, y + h / 2], fill=c)
    d.ellipse([x - w * 0.36, y - h * 0.30, x + w * 0.36, y + h * 0.30],
              fill=_blend(c, PALETTE["white"], 0.22))


def framed_art(d: ScaledDraw, x: int, y: int, w: float = 200, h: float = 160,
               frame=None, mat=None, motif: str = "paw"):
    """A picture on the wall. `motif`: paw | heart | bone | none."""
    fr = frame or (140, 104, 72)
    d.rectangle([x - w / 2, y - h / 2, x + w / 2, y + h / 2], fill=fr)
    d.rectangle([x - w / 2 + 12, y - h / 2 + 12, x + w / 2 - 12, y + h / 2 - 12],
                fill=mat or (250, 244, 232))
    ink = PALETTE["ink"]
    if motif == "paw":
        d.ellipse([x - 26, y - 10, x + 26, y + 34], fill=_blend(ink, (255, 255, 255), 0.45))
        for tx in (-30, -10, 12, 32):
            d.ellipse([x + tx - 11, y - 40, x + tx + 11, y - 16],
                      fill=_blend(ink, (255, 255, 255), 0.45))
    elif motif == "heart":
        d.ellipse([x - 30, y - 26, x + 2, y + 6], fill=(214, 96, 104))
        d.ellipse([x - 2, y - 26, x + 30, y + 6], fill=(214, 96, 104))
        d.polygon([(x - 28, y - 6), (x + 28, y - 6), (x, y + 36)], fill=(214, 96, 104))
    elif motif == "bone":
        for bx in (-30, 30):
            d.ellipse([x + bx - 18, y - 18, x + bx + 18, y + 18], fill=(238, 226, 200))
        d.rounded_rectangle([x - 32, y - 11, x + 32, y + 11], radius=8, fill=(238, 226, 200))


def shelf(d: ScaledDraw, x: int, y: int, w: float = 340, books: bool = True,
          plant: bool = True):
    """Wall shelf with a row of books and a pot plant."""
    d.rounded_rectangle([x - w / 2, y, x + w / 2, y + 16], radius=6, fill=(150, 112, 78))
    if books:
        bx = x - w / 2 + 24
        for i, col in enumerate(((198, 86, 86), (86, 132, 196), (222, 176, 74),
                                 (110, 178, 128), (168, 116, 196))):
            bw = 22 + (i % 3) * 6
            bh = 70 + (i % 2) * 18
            d.rounded_rectangle([bx, y - bh, bx + bw, y], radius=5, fill=col)
            bx += bw + 6
    if plant:
        px = x + w / 2 - 54
        d.rounded_rectangle([px - 26, y - 40, px + 26, y], radius=8, fill=(196, 122, 92))
        for a, r in ((-34, 44), (0, 56), (34, 44)):
            d.ellipse([px + a - 20, y - 40 - r, px + a + 20, y - 40], fill=(96, 168, 110))


def lamp(d: ScaledDraw, x: int, y: int, scale: float = 1.0, shade=None, glow: bool = True):
    """Table lamp with its pool of light. `y` is the base."""
    s = scale
    sh = shade or (246, 216, 150)
    if glow:
        for r, t in ((260, 0.10), (190, 0.16), (130, 0.24)):
            d.ellipse([x - r * s, y - 300 * s - r * s * 0.7,
                       x + r * s, y - 300 * s + r * s * 0.7],
                      fill=_blend((238, 226, 208), (255, 244, 206), t + 0.35))
    d.rounded_rectangle([x - 14 * s, y - 190 * s, x + 14 * s, y], radius=8 * s,
                        fill=(120, 96, 74))
    d.ellipse([x - 54 * s, y - 26 * s, x + 54 * s, y + 10 * s], fill=(120, 96, 74))
    d.polygon([(x - 86 * s, y - 190 * s), (x + 86 * s, y - 190 * s),
               (x + 58 * s, y - 300 * s), (x - 58 * s, y - 300 * s)], fill=sh)
    d.polygon([(x - 86 * s, y - 190 * s), (x - 40 * s, y - 190 * s),
               (x - 24 * s, y - 300 * s), (x - 58 * s, y - 300 * s)],
              fill=_blend(sh, PALETTE["white"], 0.35))


def counter(d: ScaledDraw, y: int, x0: int = 0, x1: int = W, top=None, body=None,
            doors: int = 4):
    """Kitchen run: cupboard doors with a worktop across the top."""
    b = body or (128, 158, 132)
    t = top or (226, 216, 200)
    d.rectangle([x0, y, x1, H], fill=b)
    d.rectangle([x0, y - 26, x1, y], fill=t)
    d.rectangle([x0, y - 30, x1, y - 24], fill=_blend(t, PALETTE["ink"], 0.18))
    span = (x1 - x0) / max(1, doors)
    for i in range(doors):
        dx = x0 + span * i
        d.rounded_rectangle([dx + 16, y + 22, dx + span - 16, H], radius=10,
                            fill=_blend(b, PALETTE["white"], 0.10))
        d.rounded_rectangle([dx + span / 2 - 26, y + 46, dx + span / 2 + 26, y + 56],
                            radius=5, fill=_blend(b, PALETTE["ink"], 0.35))


def fridge(d: ScaledDraw, x: int, y: int, scale: float = 1.0, color=None):
    """Fridge with its door seam and a couple of magnets. `y` is the floor."""
    s = scale
    c = color or (232, 236, 240)
    d.rounded_rectangle([x - 130 * s, y - 560 * s, x + 130 * s, y], radius=22 * s, fill=c)
    d.rectangle([x - 130 * s, y - 372 * s, x + 130 * s, y - 362 * s],
                fill=_blend(c, PALETTE["ink"], 0.16))
    for hy in (-330, -400):
        d.rounded_rectangle([x + 88 * s, y + hy * s, x + 106 * s, y + (hy + 120) * s],
                            radius=8 * s, fill=_blend(c, PALETTE["ink"], 0.30))
    d.rounded_rectangle([x - 92 * s, y - 520 * s, x - 30 * s, y - 462 * s],
                        radius=6 * s, fill=(250, 214, 108))
    d.ellipse([x + 6 * s, y - 512 * s, x + 54 * s, y - 464 * s], fill=(214, 96, 104))


def window_view(d: ScaledDraw, x: int, y: int, w: float = 380, h: float = 300,
                mode: str = "day", frame=None):
    """A window onto something. `mode`: day | night | snow."""
    fr = frame or (250, 246, 238)
    sky_c = {"day": (150, 206, 246), "night": (28, 38, 84), "snow": (206, 218, 234)}[mode]
    d.rectangle([x - w / 2 - 16, y - h / 2 - 16, x + w / 2 + 16, y + h / 2 + 16], fill=fr)
    d.rectangle([x - w / 2, y - h / 2, x + w / 2, y + h / 2], fill=sky_c)
    if mode == "night":
        rnd = random.Random(9)
        for _ in range(26):
            sx = x - w / 2 + rnd.random() * w
            sy = y - h / 2 + rnd.random() * h
            d.ellipse([sx - 3, sy - 3, sx + 3, sy + 3], fill=(255, 250, 220))
    else:
        d.ellipse([x - w * 0.46, y + h * 0.10, x + w * 0.10, y + h / 2],
                  fill=(120, 182, 122) if mode == "day" else (238, 244, 250))
        d.ellipse([x - w * 0.05, y + h * 0.18, x + w * 0.50, y + h / 2],
                  fill=(96, 164, 108) if mode == "day" else (228, 236, 246))
    d.rectangle([x - 7, y - h / 2, x + 7, y + h / 2], fill=fr)
    d.rectangle([x - w / 2, y - 7, x + w / 2, y + 7], fill=fr)


def car_interior(d: ScaledDraw, dash_y: int = 900, body=None, view: str = "day"):
    """Front seats, seen from the bonnet: windscreen, dashboard, wheel, mirror.

    Drawn in two halves -- everything behind the characters here, and
    car_foreground() for the dashboard and wheel that must sit in front of them.
    """
    c = body or (188, 72, 66)
    d.rectangle([0, 0, W, H], fill=_blend(c, PALETTE["ink"], 0.35))
    sky_c = (150, 206, 246) if view == "day" else (30, 40, 88)
    x0, x1, y0, y1 = 120, W - 120, 90, dash_y - 40
    d.rounded_rectangle([x0, y0, x1, y1], radius=60, fill=sky_c)

    # A road running to a vanishing point, not two green ellipses. The verge,
    # the tarmac and the dashes all converge on the same point, which is what
    # makes the view read as movement rather than as scenery pasted behind glass.
    horizon = y0 + (y1 - y0) * 0.52
    vp_x = W / 2
    if view == "day":
        cloud(d, 620, 220, 0.9)
        cloud(d, 1340, 190, 0.7)
        for hx, hw, hh in ((420, 760, 150), (1180, 900, 190), (1700, 620, 120)):
            d.ellipse([hx - hw / 2, horizon - hh, hx + hw / 2, horizon + 40],
                      fill=(120, 168, 128))
    else:
        stars(d, n=60, seed=17, area=(x0 + 40, y0 + 30, x1 - 40, horizon - 20))
    d.rectangle([x0, horizon, x1, y1], fill=(122, 174, 128) if view == "day"
                else (44, 58, 78))                                    # verge
    d.polygon([(vp_x - 26, horizon), (vp_x + 26, horizon),
               (x1 + 260, y1), (x0 - 260, y1)],
              fill=(96, 100, 112) if view == "day" else (58, 62, 76))  # tarmac
    for i in range(5):                                                # centre line
        t0 = 0.16 + i * 0.19
        t1 = t0 + 0.10
        w0, w1_ = 4 + t0 * 46, 4 + t1 * 46
        d.polygon([(vp_x - w0 / 2, horizon + t0 * (y1 - horizon)),
                   (vp_x + w0 / 2, horizon + t0 * (y1 - horizon)),
                   (vp_x + w1_ / 2, horizon + t1 * (y1 - horizon)),
                   (vp_x - w1_ / 2, horizon + t1 * (y1 - horizon))],
                  fill=(246, 240, 214))


def car_foreground(d: ScaledDraw, dash_y: int = 900, body=None, wheel_x: int = 1450):
    """Dashboard and steering wheel — drawn after the characters."""
    c = body or (188, 72, 66)
    dark = _blend(c, PALETTE["ink"], 0.45)
    d.rounded_rectangle([-40, dash_y, W + 40, H + 60], radius=40, fill=dark)
    d.rounded_rectangle([-40, dash_y, W + 40, dash_y + 30], radius=12,
                        fill=_blend(dark, PALETTE["white"], 0.16))
    # instrument binnacle, so the dash is not one flat slab
    d.rounded_rectangle([wheel_x - 150, dash_y + 44, wheel_x + 150, dash_y + 150],
                        radius=22, fill=_blend(dark, PALETTE["ink"], 0.22))
    for gx in (-78, 0, 78):
        d.ellipse([wheel_x + gx - 40, dash_y + 56, wheel_x + gx + 40, dash_y + 136],
                  fill=_blend(dark, PALETTE["ink"], 0.45))
        d.ellipse([wheel_x + gx - 30, dash_y + 66, wheel_x + gx + 30, dash_y + 126],
                  fill=(126, 152, 176))

    # The wheel is a RING -- an ellipse over an ellipse left a dark disc that
    # read as a hole in the dashboard rather than as something being held.
    rim = _blend(dark, PALETTE["ink"], 0.40)
    d.ellipse([wheel_x - 168, dash_y - 130, wheel_x + 168, dash_y + 206], fill=rim)
    d.ellipse([wheel_x - 132, dash_y - 94, wheel_x + 132, dash_y + 170], fill=dark)
    d.rounded_rectangle([wheel_x - 138, dash_y + 20, wheel_x + 138, dash_y + 56],
                        radius=16, fill=rim)                          # spokes
    d.rounded_rectangle([wheel_x - 20, dash_y + 30, wheel_x + 20, dash_y + 170],
                        radius=14, fill=rim)
    d.ellipse([wheel_x - 46, dash_y + 6, wheel_x + 46, dash_y + 82],
              fill=_blend(rim, PALETTE["white"], 0.12))                # boss

    for pillar in (0, W):                                             # A-pillars
        d.rounded_rectangle([pillar - 74, -40, pillar + 74, dash_y + 40],
                            radius=40, fill=dark)
    d.rounded_rectangle([W / 2 - 110, 40, W / 2 + 110, 132], radius=22, fill=dark)
    d.rounded_rectangle([W / 2 - 96, 52, W / 2 + 96, 120], radius=16, fill=(120, 146, 170))


def desk(d: ScaledDraw, y: int, color=None):
    """Desk seen head-on: surface band plus a front panel down to the frame edge.

    The panel is not decoration. Stopping at a thin strip let the characters'
    contact shadows show underneath, which made them look afloat rather than
    seated behind the desk.
    """
    c = color or (168, 126, 90)
    d.rectangle([-40, y + 40, W + 40, H + 40], fill=_blend(c, PALETTE["ink"], 0.34))
    d.rounded_rectangle([-40, y, W + 40, y + 52], radius=14, fill=c)
    d.rectangle([-40, y + 44, W + 40, y + 58], fill=_blend(c, PALETTE["ink"], 0.20))


def monitor(d: ScaledDraw, x: int, y: int, scale: float = 1.0, screen=None):
    """Desktop monitor standing on a surface at y."""
    s = scale
    d.rounded_rectangle([x - 20 * s, y - 70 * s, x + 20 * s, y], radius=8 * s,
                        fill=(96, 102, 118))
    d.ellipse([x - 70 * s, y - 18 * s, x + 70 * s, y + 10 * s], fill=(96, 102, 118))
    d.rounded_rectangle([x - 190 * s, y - 320 * s, x + 190 * s, y - 66 * s],
                        radius=14 * s, fill=(70, 76, 92))
    d.rounded_rectangle([x - 174 * s, y - 304 * s, x + 174 * s, y - 82 * s],
                        radius=8 * s, fill=screen or (126, 178, 222))


def skyline(d: ScaledDraw, y: int, seed: int = 4, color=None, lit: bool = True):
    """A row of blocky buildings along y."""
    c = color or (58, 64, 96)
    rnd = random.Random(seed)
    x = -40
    while x < W + 40:
        bw = rnd.randint(110, 210)
        bh = rnd.randint(160, 420)
        d.rectangle([x, y - bh, x + bw, y], fill=c)
        if lit:
            for wy in range(int(y - bh + 26), int(y - 20), 46):
                for wx in range(int(x + 18), int(x + bw - 22), 40):
                    if rnd.random() < 0.55:
                        d.rectangle([wx, wy, wx + 18, wy + 24], fill=(250, 222, 138))
        x += bw + rnd.randint(6, 26)


def string_lights(d: ScaledDraw, y: int, sag: float = 70, n: int = 14, seed: int = 2):
    """A drooping run of bulbs across the top of the frame."""
    rnd = random.Random(seed)
    pts = []
    for i in range(n + 1):
        t = i / n
        px = t * W
        py = y + math.sin(t * math.pi) * sag
        pts.append((px, py))
    d.line(pts, fill=(72, 68, 62), width=6)
    for i, (px, py) in enumerate(pts):
        col = ((250, 214, 108), (246, 152, 120), (154, 214, 236))[i % 3]
        d.ellipse([px - 15, py, px + 15, py + 34], fill=col)
        d.ellipse([px - 7, py + 6, px + 3, py + 18], fill=_blend(col, PALETTE["white"], 0.55))


def snowfall(d: ScaledDraw, area=(0, 0, W, H), n: int = 90, seed: int = 5,
             size=(6, 16)):
    rnd = random.Random(seed)
    x0, y0, x1, y1 = area
    for _ in range(n):
        x = x0 + rnd.random() * (x1 - x0)
        y = y0 + rnd.random() * (y1 - y0)
        r = rnd.uniform(*size) / 2
        d.ellipse([x - r, y - r, x + r, y + r], fill=(250, 252, 255))


def snow_ground(d: ScaledDraw, y: int, color=None, drifts: bool = True):
    c = color or (244, 248, 253)
    d.rectangle([0, y, W, H], fill=c)
    if drifts:
        for cx, w_, h_ in ((260, 620, 90), (1080, 760, 76), (1740, 520, 96)):
            d.ellipse([cx - w_ / 2, y - h_ / 2, cx + w_ / 2, y + h_ / 2],
                      fill=_blend(c, PALETTE["white"], 0.6))
    d.rectangle([0, y, W, y + 8], fill=_blend(c, (168, 190, 220), 0.5))


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
    wide = any(ord(ch) > 0x2FF for ch in text)
    # shrink rather than overflow: a caption wider than the banner used to run
    # off both ends of the pill
    f = font(size, unicode_wide=wide)
    bb = d.textbbox((0, 0), text, font=f)
    while bb[2] - bb[0] + pad * 3 > W * width_frac and size > 24:
        size = int(size * 0.94)
        f = font(size, unicode_wide=wide)
        bb = d.textbbox((0, 0), text, font=f)
    w = min(bb[2] - bb[0] + pad * 3, W * width_frac)
    h = (bb[3] - bb[1]) + pad * 1.6
    d.rounded_rectangle([W / 2 - w / 2, y - h / 2, W / 2 + w / 2, y + h / 2],
                        radius=h * 0.5, fill=bg or PALETTE["banner"])
    register_box("caption", (W / 2 - w / 2, y - h / 2, W / 2 + w / 2, y + h / 2))
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
