"""
Burned-in caption cards.

Shorts are watched muted more often than not, so a Short without on-screen text
loses most of its audience in the first second. YouTube's own auto-captions are
not a substitute: they are off by default and they mangle words like
"scattering".

This module renders one transparent PNG per caption cue. factory.py overlays
them onto the Short with ffmpeg's `overlay` filter and an `enable=` time range.

Why PNGs instead of the obvious `subtitles=` / `drawtext` filters: both are
optional ffmpeg build features (libass / libfreetype), and plenty of ffmpeg
builds ship without them -- the Homebrew build this was developed against has
neither. Pillow is already a hard dependency, `overlay` is always present, and
drawing the card ourselves means the captions use the channel's own font,
palette and rounded-banner look instead of a generic subtitle style.

    from engine import captions
    card = captions.render_card("Air is mostly nothing at all!", "cap_003.png",
                                video_w=1080)
    # -> CaptionCard(path=..., w=..., h=..., text=...)
"""

from __future__ import annotations

import os
from typing import NamedTuple

from PIL import Image, ImageDraw, ImageFont

from . import toolkit as tk

SS = 2                       # supersample factor, same trick the toolkit uses
BAND_ALPHA = 232             # banner opacity 0-255
PAD_X, PAD_Y = 42, 26        # padding inside the banner, logical px
LINE_SPACING = 1.16


class CaptionCard(NamedTuple):
    path: str
    w: int
    h: int
    text: str


def _font(px: int, unicode_wide: bool = False):
    """Truetype face at an explicit pixel size.

    Deliberately does not go through toolkit.font(): that one multiplies by the
    toolkit's current canvas scale, which is global state this module has no
    business depending on.
    """
    p = tk.font_path(unicode_wide)
    if p:
        try:
            return ImageFont.truetype(p, px)
        except Exception:
            pass
    try:
        return ImageFont.load_default(size=px)     # Pillow >= 10.1
    except TypeError:
        return ImageFont.load_default()


def wrap_lines(draw, text: str, font, max_w: float):
    """Greedy word wrap. A single word longer than max_w gets its own line."""
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if not cur or draw.textlength(trial, font=font) <= max_w:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines or [text]


def render_card(text: str, out_path: str, video_w: int = 1080,
                width_frac: float = 0.88, size: int = 52, max_lines: int = 3,
                stroke: int = 5, bg=None, fg=None) -> CaptionCard:
    """One caption cue -> one RGBA PNG sized to its own text.

    The font shrinks until the text fits `max_lines`, so a long sentence never
    grows a fourth line off the bottom of the card.
    """
    text = " ".join(text.split())
    wide = any(ord(c) > 0x2FF for c in text)
    inner_w = video_w * width_frac - 2 * PAD_X

    probe = ImageDraw.Draw(Image.new("RGBA", (8, 8)))
    px = max(12, int(size * SS))
    while True:
        f = _font(px, wide)
        lines = wrap_lines(probe, text, f, inner_w * SS)
        text_w = max(probe.textlength(ln, font=f) for ln in lines)
        # shrink for BOTH failure modes: too many lines, and a single word too
        # long to wrap at all (a URL, or a script that does not use spaces),
        # which would otherwise paint straight through the side of the card
        if (len(lines) <= max_lines and text_w <= inner_w * SS) or px <= 22 * SS:
            break
        px = int(px * 0.92)

    line_h = max(1, int(px * LINE_SPACING))
    box_w = int(min(video_w * width_frac, text_w / SS + 2 * PAD_X) * SS)
    box_h = int(line_h * len(lines) + 2 * PAD_Y * SS)
    # the stroke sticks out past the glyph box on every side
    pad_out = int(stroke * SS) + 4

    img = Image.new("RGBA", (box_w + pad_out * 2, box_h + pad_out * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    band = tuple(bg or tk.PALETTE["banner"]) + (BAND_ALPHA,)
    d.rounded_rectangle([pad_out, pad_out, pad_out + box_w, pad_out + box_h],
                        radius=box_h * 0.34, fill=band)

    y = pad_out + PAD_Y * SS
    for ln in lines:
        w = probe.textlength(ln, font=f)
        d.text((pad_out + box_w / 2 - w / 2, y), ln, font=f,
               fill=tuple(fg or tk.PALETTE["white"]),
               stroke_width=int(stroke * SS), stroke_fill=tk.PALETTE["ink"])
        y += line_h

    out = img.resize((img.width // SS, img.height // SS), Image.LANCZOS)
    dirn = os.path.dirname(os.path.abspath(out_path))
    if dirn:
        os.makedirs(dirn, exist_ok=True)
    out.save(out_path, "PNG", optimize=True)
    return CaptionCard(out_path, out.width, out.height, text)


def shift_cues(cues, offsets):
    """Re-time cues for a clip built from a subset of scenes.

    `offsets` maps a scene's original start time to its start in the new
    timeline; anything outside the kept range is dropped.
    """
    out = []
    for (a, b, txt) in cues:
        for (lo, hi, delta) in offsets:
            if lo - 1e-6 <= a < hi:
                out.append((a + delta, min(b, hi) + delta, txt))
                break
    return out


if __name__ == "__main__":     # quick visual check
    import sys

    txt = sys.argv[1] if len(sys.argv) > 1 else \
        "Sunlight is made of every colour mixed together!"
    c = render_card(txt, "caption_demo.png")
    print(f"  {c.path}  {c.w}x{c.h}")
