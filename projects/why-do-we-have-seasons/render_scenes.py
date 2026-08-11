#!/usr/bin/env python3
"""
Episode 3 -- "Why Do We Have SEASONS?"

Draws frames/scene_01.png .. scene_10.png at 1920x1080 using only
engine/toolkit.py primitives. This episode contributed `planet`, `orbit_ring`
and `light_beam` to the toolkit; everything else is reused from episodes 1-2.

    python3 render_scenes.py            # all scenes
    python3 render_scenes.py 5 6        # only scenes 5 and 6
    python3 render_scenes.py --sheet    # also write frames/contact_sheet.jpg
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from engine import toolkit as tk  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FRAMES = os.path.join(HERE, "frames")

P = tk.PALETTE
SUNBEAM = (255, 214, 92)
WARM = (240, 150, 70)
COOL = (120, 176, 232)


def out(n):
    return os.path.join(FRAMES, f"scene_{n:02d}.png")


def space(stars=120, seed=6):
    """Every space scene shares one backdrop -- consistency is the identity."""
    img, d = tk.canvas("night")
    tk.stars(d, n=stars, seed=seed, area=(0, 0, 1920, 1080))
    return img, d


# --------------------------------------------------------------------------
# Scene 1 -- title card
# --------------------------------------------------------------------------
def scene_01():
    img, d = space(130, 6)
    tk.orbit_ring(d, 1420, 620, 430, 190, color=(120, 140, 200), width=6)
    tk.sun(d, 1420, 620, 118, ray_len=0.42)
    tk.planet(d, 1790, 560, 108, tilt=23.5)
    tk.rocket(d, 1150, 900, scale=0.5, face=True)

    tk.title_text(d, (700, 152), "WONDER-O-NAUTS", 74, fill=P["accent"], stroke=11)
    tk.title_text(d, (700, 450), "Why do we have\nSEASONS?", 140,
                  fill=P["white"], stroke=15)
    tk.speech_pop(d, 600, 736, "Science for kids!", 54, fill=P["white"])
    return tk.vignette(img)


# --------------------------------------------------------------------------
# Scene 2 -- the big question
# --------------------------------------------------------------------------
def scene_02():
    img, d = tk.canvas("day")
    tk.sun(d, 1700, 190, 100, rotate=16)
    tk.cloud(d, 360, 250, 0.78)
    tk.ground(d, 890)
    tk.kid(d, 470, 1020, scale=1.05, arms="down", mouth="o", looking="up")
    tk.thought_bubble(d, 1200, 500, w=980, h=400, tail_to=(660, 650),
                      text="Hot in summer...\nCOLD in winter?", text_size=88)
    return tk.vignette(img)


# --------------------------------------------------------------------------
# Scene 3 -- it is NOT the distance
# --------------------------------------------------------------------------
def scene_03():
    img, d = space(110, 11)
    tk.orbit_ring(d, 960, 620, 720, 250, color=(120, 140, 200), width=6)
    tk.sun(d, 960, 620, 120, ray_len=0.4)
    tk.planet(d, 268, 596, 104, tilt=23.5, night="left", seed=5)
    tk.planet(d, 1660, 606, 96, tilt=23.5, night="right", seed=8)
    tk.badge(d, (280, 400), "January: CLOSER", 44)
    tk.badge(d, (1650, 396), "July: farther", 44)
    tk.title_text(d, (960, 130), "It is NOT about being closer!", 76,
                  fill=P["white"], stroke=12)
    tk.speech_pop(d, 960, 906, "January is winter up north", 50,
                  fill=P["rocket_red"], text_fill=P["white"])
    return tk.vignette(img)


# --------------------------------------------------------------------------
# Scene 4 -- Earth leans
# --------------------------------------------------------------------------
def scene_04():
    img, d = space(100, 3)
    tk.light_beam(d, (120, 470), (620, 470), n=5, spacing=96, color=SUNBEAM,
                  width=13, arrow_head=34)
    tk.planet(d, 1080, 540, 300, tilt=23.5, night="right", seed=4)
    tk.title_text(d, (960, 130), "Earth LEANS over", 88, fill=P["white"], stroke=13)
    tk.speech_pop(d, 1620, 300, "about 23 degrees", 46, fill=P["accent"])
    tk.caption(d, "And the lean always points the same way, all year", 50, y=950)
    return tk.vignette(img)


# --------------------------------------------------------------------------
# Scene 5 -- straight light vs slanted light
# --------------------------------------------------------------------------
def scene_05():
    img, d = tk.canvas("night")
    tk.stars(d, n=70, seed=13, area=(0, 0, 1920, 620))
    # left: straight down -> small bright patch
    tk.light_beam(d, (470, 250), (470, 700), n=4, spacing=64, color=SUNBEAM,
                  width=13, arrow_head=32)
    d.rounded_rectangle([320, 740, 620, 800], radius=30, fill=SUNBEAM)
    tk.title_text(d, (470, 880), "straight down\n= small + BRIGHT", 52,
                  fill=P["white"], stroke=10)
    # right: slanted -> the same light smeared over a bigger, weaker patch
    tk.light_beam(d, (1120, 230), (1520, 700), n=4, spacing=64, color=(214, 186, 128),
                  width=13, arrow_head=32)
    d.rounded_rectangle([1230, 740, 1860, 800], radius=30, fill=(196, 176, 132))
    tk.title_text(d, (1540, 880), "slanted\n= spread out + weaker", 52,
                  fill=P["white"], stroke=10)
    tk.title_text(d, (960, 128), "Same light, different angle", 74,
                  fill=P["accent"], stroke=12)
    return tk.vignette(img)


# --------------------------------------------------------------------------
# Scene 6 -- summer: leaning toward the Sun
# --------------------------------------------------------------------------
def scene_06():
    img, d = space(90, 21)
    tk.sun(d, 210, 540, 130, ray_len=0.4)
    tk.light_beam(d, (400, 470), (880, 470), n=5, spacing=88, color=SUNBEAM,
                  width=13, arrow_head=34)
    tk.planet(d, 1300, 540, 270, tilt=-23.5, night="right", seed=4)
    tk.speech_pop(d, 1300, 210, "SUMMER up here", 56, fill=WARM,
                  text_fill=P["white"])
    tk.title_text(d, (700, 140), "Leaning TOWARD the Sun", 70,
                  fill=P["white"], stroke=12)
    tk.caption(d, "Steep sunlight + long days = warm", 52, y=950)
    return tk.vignette(img)


# --------------------------------------------------------------------------
# Scene 7 -- winter: leaning away
# --------------------------------------------------------------------------
def scene_07():
    img, d = space(90, 22)
    # same lean as scene 6 (-23.5), but now Earth sits on the far side of its
    # orbit, so the Sun is on the right and the north leans away from it
    tk.sun(d, 1710, 540, 130, ray_len=0.4)
    tk.light_beam(d, (1520, 470), (1040, 470), n=5, spacing=88,
                  color=(214, 186, 128), width=13, arrow_head=34)
    tk.planet(d, 620, 540, 270, tilt=-23.5, night="left", seed=4)
    tk.speech_pop(d, 620, 210, "WINTER up here", 56, fill=COOL,
                  text_fill=P["text_dark"])
    tk.title_text(d, (1260, 140), "Leaning AWAY from the Sun", 68,
                  fill=P["white"], stroke=12)
    tk.caption(d, "Slanted sunlight + short days = cold", 52, y=950)
    return tk.vignette(img)


# --------------------------------------------------------------------------
# Scene 8 -- opposite seasons at the same moment
# --------------------------------------------------------------------------
def scene_08():
    img, d = space(90, 31)
    tk.light_beam(d, (110, 520), (560, 520), n=5, spacing=92, color=SUNBEAM,
                  width=13, arrow_head=34)
    tk.planet(d, 1080, 560, 300, tilt=23.5, night="right", seed=4)
    tk.speech_pop(d, 1080, 190, "snowmen up here", 50, fill=COOL,
                  text_fill=P["text_dark"])
    tk.speech_pop(d, 1080, 936, "beach down here", 50, fill=WARM,
                  text_fill=P["white"])
    tk.title_text(d, (520, 190), "Two seasons\nat ONCE", 76, fill=P["accent"],
                  stroke=12)
    return tk.vignette(img)


# --------------------------------------------------------------------------
# Scene 9 -- bonus: the poles
# --------------------------------------------------------------------------
def scene_09():
    img, d = space(120, 41)
    tk.planet(d, 700, 600, 280, tilt=23.5, night="left", seed=4)
    tk.sun(d, 1520, 330, 110, ray_len=0.42)
    tk.light_beam(d, (1330, 430), (980, 470), n=3, spacing=90, color=SUNBEAM,
                  width=12, arrow_head=32)
    tk.speech_pop(d, 620, 190, "Sun never sets!", 54, fill=P["accent"])
    tk.title_text(d, (1420, 700), "At the poles\nit gets extreme", 64,
                  fill=P["white"], stroke=11)
    tk.caption(d, "Daylight all night in summer, darkness all day in winter",
               48, y=950)
    return tk.vignette(img)


# --------------------------------------------------------------------------
# Scene 10 -- outro (bottom-right 40% stays clear for end cards)
# --------------------------------------------------------------------------
def scene_10():
    img, d = space(130, 9)
    zones = tk.end_screen_guides(d)   # safe-zone contract for this frame
    tk.planet(d, 300, 620, 190, tilt=23.5, seed=4)
    tk.rocket(d, 520, 250, scale=0.5, face=True)
    tk.title_text(d, (1090, 160), "Mission complete!", 100, fill=P["accent"], stroke=15)
    tk.title_text(d, (1020, 380), "Seasons come from the lean,\nnot from the distance",
                  58, fill=P["white"], stroke=11)
    tk.speech_pop(d, 760, 590, "LIKE + SUBSCRIBE", 58, fill=P["rocket_red"],
                  text_fill=P["white"])
    tk.title_text(d, (640, 800), "What should we explore next?", 48,
                  fill=P["white"], stroke=10)
    assert not tk.safe_zone_violations(zones["end_cards"]), \
        tk.safe_zone_violations(zones["end_cards"])
    return tk.vignette(img)


SCENES = [scene_01, scene_02, scene_03, scene_04, scene_05,
          scene_06, scene_07, scene_08, scene_09, scene_10]


def render(only=None):
    os.makedirs(FRAMES, exist_ok=True)
    written = []
    for i, fn in enumerate(SCENES, 1):
        if only and i not in only:
            continue
        path = tk.save(fn(), out(i))
        written.append(path)
        print(f"  scene {i:02d} -> {os.path.relpath(path, HERE)}")
    return written


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--sheet"]
    render({int(a) for a in args} if args else None)
    if "--sheet" in sys.argv[1:]:
        sheet = tk.contact_sheet([out(i) for i in range(1, len(SCENES) + 1)],
                                 os.path.join(FRAMES, "contact_sheet.jpg"))
        print(f"  contact sheet -> {os.path.relpath(sheet, HERE)}")
