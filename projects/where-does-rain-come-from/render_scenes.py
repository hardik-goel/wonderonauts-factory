#!/usr/bin/env python3
"""
Episode 4 -- "Where Does RAIN Come From?"

Draws frames/scene_01.png .. scene_10.png at 1920x1080 using only
engine/toolkit.py primitives. This episode contributed `raindrop`, `rainfall`,
`puddle` and `cycle_arrow`; everything else is reused from episodes 1-3.

    python3 render_scenes.py            # all scenes
    python3 render_scenes.py 6 7        # only scenes 6 and 7
    python3 render_scenes.py --sheet    # also write frames/contact_sheet.jpg
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from engine import toolkit as tk  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FRAMES = os.path.join(HERE, "frames")

P = tk.PALETTE
SEA = (74, 156, 214)
SEA_DARK = (56, 130, 190)
GREY_CLOUD = (196, 206, 224)
DROP = (108, 186, 244)


def out(n):
    return os.path.join(FRAMES, f"scene_{n:02d}.png")


def vapour(d, x, y, n=4, height=300, color=(236, 248, 255), spread=70):
    """Rising invisible-water squiggles, drawn from the zig_ray primitive.

    Near-white and thick: thin pale squiggles vanish against a pale sky.
    """
    for i in range(n):
        ox = x + (i - (n - 1) / 2) * spread
        tk.zig_ray(d, (ox, y), (ox, y - height), color=color,
                   amplitude=18, wavelength=76, width=12, phase=i * 0.8)


# --------------------------------------------------------------------------
# Scene 1 -- title card
# --------------------------------------------------------------------------
def scene_01():
    img, d = tk.canvas("day")
    tk.cloud(d, 1480, 300, 1.25, color=GREY_CLOUD)
    tk.rainfall(d, (1200, 430, 1780, 880), n=26, seed=5)
    tk.ground(d, 920)
    tk.puddle(d, 1480, 960, 300, 62)
    tk.rocket(d, 300, 830, scale=0.45, face=True)

    tk.title_text(d, (760, 152), "WONDER-O-NAUTS", 74, fill=P["accent"], stroke=11)
    tk.title_text(d, (700, 450), "Where does rain\nCOME FROM?", 132,
                  fill=P["white"], stroke=15)
    tk.speech_pop(d, 640, 720, "Science for kids!", 54, fill=P["white"])
    return tk.vignette(img)


# --------------------------------------------------------------------------
# Scene 2 -- the big question
# --------------------------------------------------------------------------
def scene_02():
    img, d = tk.canvas("day")
    tk.cloud(d, 1180, 250, 1.1, color=GREY_CLOUD)
    tk.rainfall(d, (900, 380, 1520, 860), n=30, seed=9)
    tk.ground(d, 900)
    tk.puddle(d, 1180, 950, 280, 58)
    tk.kid(d, 430, 1020, scale=1.05, arms="down", mouth="o", looking="up")
    tk.thought_bubble(d, 900, 470, w=880, h=360, tail_to=(600, 650),
                      text="Where does all\nthat water come from?", text_size=72)
    return tk.vignette(img)


# --------------------------------------------------------------------------
# Scene 3 -- the Sun lifts water
# --------------------------------------------------------------------------
def scene_03():
    img, d = tk.canvas("day")
    tk.sun(d, 300, 210, 130, rotate=10)
    tk.ground(d, 820, color=SEA, dark=SEA_DARK, hills=False)
    for x in (620, 1080, 1540):
        vapour(d, x, 800, n=4, height=340)
    tk.puddle(d, 1750, 1000, 220, 48)
    tk.title_text(d, (1120, 140), "The Sun is a giant water lifter", 72,
                  fill=P["white"], stroke=12)
    tk.caption(d, "Seas, lakes, rivers -- even the puddle outside", 50, y=950)
    return tk.vignette(img)


# --------------------------------------------------------------------------
# Scene 4 -- evaporation: water turns invisible
# --------------------------------------------------------------------------
def scene_04():
    img, d = tk.canvas("day")
    tk.sun(d, 1700, 200, 96, rotate=22)
    tk.ground(d, 900)
    tk.puddle(d, 620, 960, 240, 54)
    vapour(d, 620, 900, n=4, height=430)
    tk.molecule_field(d, n=16, seed=12, area=(980, 250, 1820, 760),
                      r_range=(22, 38), color=(178, 216, 244))
    tk.title_text(d, (860, 140), "The water goes INVISIBLE", 78,
                  fill=P["white"], stroke=12)
    tk.speech_pop(d, 1380, 866, "evaporation", 52, fill=P["accent"])
    return tk.vignette(img)


# --------------------------------------------------------------------------
# Scene 5 -- up high it is freezing, so droplets form again
# --------------------------------------------------------------------------
def scene_05():
    img, d = tk.canvas("day")
    tk.ground(d, 1020)
    vapour(d, 480, 980, n=5, height=420, spread=110)
    for x, y, sz in [(1060, 340, 66), (1270, 250, 58), (1490, 370, 72),
                     (1680, 262, 54), (1180, 500, 62), (1540, 552, 60)]:
        tk.raindrop(d, x, y, sz)
    tk.speech_pop(d, 1340, 130, "BRRR -- it is freezing up here!", 52, fill=(150, 205, 245))
    tk.title_text(d, (560, 250), "Cold air turns it\nback into droplets", 62,
                  fill=P["white"], stroke=11)
    tk.caption(d, "Invisible water + cold = tiny drops you can see", 50, y=950)
    return tk.vignette(img)


# --------------------------------------------------------------------------
# Scene 6 -- a cloud is billions of tiny droplets
# --------------------------------------------------------------------------
def scene_06():
    img, d = tk.canvas("day")
    tk.ground(d, 1010)
    tk.cloud(d, 900, 470, 3.0, color=GREY_CLOUD)
    tk.rainfall(d, (520, 380, 1290, 560), n=40, seed=3, size=(14, 24),
                streaks=False)
    tk.title_text(d, (960, 140), "A cloud IS water", 84, fill=P["white"], stroke=13)
    tk.speech_pop(d, 1560, 760, "not cotton\nnot smoke", 52, fill=P["rocket_red"],
                  text_fill=P["white"])
    tk.caption(d, "Billions of drops, light enough for the air to hold up", 50, y=950)
    return tk.vignette(img)


# --------------------------------------------------------------------------
# Scene 7 -- droplets bump and join up
# --------------------------------------------------------------------------
def scene_07():
    img, d = tk.canvas("day")
    tk.ground(d, 1020)
    tk.cloud(d, 960, 300, 2.4, color=GREY_CLOUD)
    # small -> medium -> large, with arrows showing them merging
    for x in (300, 460):
        tk.raindrop(d, x, 660, 46)
    tk.arrow(d, (600, 660), (760, 660), color=P["white"], width=14, head=36)
    tk.raindrop(d, 940, 660, 74)
    tk.arrow(d, (1090, 660), (1250, 660), color=P["white"], width=14, head=36)
    tk.raindrop(d, 1480, 660, 118)
    tk.speech_pop(d, 960, 860, "bump, join, BIGGER!", 56, fill=P["accent"])
    tk.title_text(d, (700, 150), "Droplets join up", 80, fill=P["white"], stroke=13)
    return tk.vignette(img)


# --------------------------------------------------------------------------
# Scene 8 -- too heavy to float: rain
# --------------------------------------------------------------------------
def scene_08():
    img, d = tk.canvas("day")
    tk.cloud(d, 900, 280, 2.2, color=(176, 188, 210))
    tk.rainfall(d, (420, 460, 1420, 900), n=52, seed=8, size=(20, 34))
    tk.ground(d, 900)
    tk.puddle(d, 780, 980, 340, 66)
    tk.puddle(d, 1420, 1010, 240, 50)
    tk.kid(d, 1700, 1020, scale=0.95, arms="up", mouth="smile", looking="up")
    tk.title_text(d, (620, 150), "Too heavy to float!", 82, fill=P["white"], stroke=13)
    return tk.vignette(img)


# --------------------------------------------------------------------------
# Scene 9 -- the whole loop, round and round forever
# --------------------------------------------------------------------------
def scene_09():
    img, d = tk.canvas("day")
    tk.sun(d, 220, 190, 104, rotate=8)
    tk.ground(d, 850, color=SEA, dark=SEA_DARK, hills=False)
    vapour(d, 470, 830, n=3, height=280, spread=80)
    tk.cycle_arrow(d, 960, 700, 500, 380, 178, 300, color=P["white"], width=14)
    tk.cloud(d, 1080, 300, 1.5, color=GREY_CLOUD)
    tk.rainfall(d, (1320, 430, 1720, 800), n=22, seed=4)
    # continue the loop the other side: down out of the cloud, back to the sea
    tk.cycle_arrow(d, 960, 700, 500, 380, 330, 48, color=P["white"], width=14)
    tk.title_text(d, (700, 140), "Round and round, forever", 74,
                  fill=P["white"], stroke=12)
    tk.caption(d, "The water in your glass is billions of years old", 50, y=950)
    return tk.vignette(img)


# --------------------------------------------------------------------------
# Scene 10 -- outro (bottom-right 40% stays clear for end cards)
# --------------------------------------------------------------------------
def scene_10():
    img, d = tk.canvas("night")
    tk.stars(d, n=110, seed=17, area=(0, 0, 1920, 900))
    zones = tk.end_screen_guides(d)   # safe-zone contract for this frame
    tk.ground(d, 960, color=(46, 96, 92), dark=(34, 78, 78))
    tk.rocket(d, 250, 540, scale=1.15, face=True)
    tk.raindrop(d, 560, 300, 70)
    tk.title_text(d, (1060, 160), "Mission complete!", 100, fill=P["accent"], stroke=15)
    tk.title_text(d, (1010, 380), "Sun lifts it, cold makes drops,\nheavy drops fall",
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
