#!/usr/bin/env python3
"""
Episode 5 -- "Why Is the SEA Salty?"

Draws frames/scene_01.png .. scene_10.png at 1920x1080 using only
engine/toolkit.py primitives. This episode contributed `sea`, `wave`,
`salt_crystal`, `mountain` and `river`; everything else is reused from
episodes 1-4.

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
GREY_CLOUD = (196, 206, 224)
ROCK = (128, 122, 148)
SALTY = (150, 200, 232)          # the very salty water of scene 9


def out(n):
    return os.path.join(FRAMES, f"scene_{n:02d}.png")


def vapour(d, x, y, n=4, height=320, color=(236, 248, 255), spread=76):
    """Rising invisible-water squiggles, composed from the zig_ray primitive."""
    for i in range(n):
        ox = x + (i - (n - 1) / 2) * spread
        tk.zig_ray(d, (ox, y), (ox, y - height), color=color,
                   amplitude=17, wavelength=74, width=12, phase=i * 0.8)


def salt_sprinkle(d, spots, size=54):
    """A handful of salt grains at the given (x, y, rotation) spots."""
    for x, y, rot in spots:
        tk.salt_crystal(d, x, y, size, rotate=rot)


# --------------------------------------------------------------------------
# Scene 1 -- title card
# --------------------------------------------------------------------------
def scene_01():
    img, d = tk.canvas("day")
    tk.sun(d, 1660, 180, 112, rotate=12)
    tk.cloud(d, 1440, 340, 0.8)
    tk.sea(d, 830, phase=0.4)
    tk.wave(d, 1420, 830, 620, 1.0)
    tk.rocket(d, 250, 700, scale=0.45, face=True)
    # grains belong in the water, not hovering above it
    salt_sprinkle(d, [(1180, 930, 8), (1620, 990, -12)], 62)

    tk.title_text(d, (760, 150), "WONDER-O-NAUTS", 74, fill=P["accent"], stroke=11)
    tk.title_text(d, (720, 440), "Why is the sea\nSALTY?", 138,
                  fill=P["white"], stroke=16)
    tk.speech_pop(d, 620, 700, "Science for kids!", 54, fill=P["white"])
    return tk.vignette(img)


# --------------------------------------------------------------------------
# Scene 2 -- the taste test: everything that flows in is fresh
# --------------------------------------------------------------------------
def scene_02():
    img, d = tk.canvas("day")
    tk.sun(d, 250, 190, 96, rotate=20)
    tk.cloud(d, 1560, 220, 0.9)
    tk.sea(d, 880, phase=1.2)
    tk.kid(d, 470, 1010, scale=1.05, arms="down", mouth="o", looking="up")
    tk.thought_bubble(d, 1140, 430, w=1000, h=380, tail_to=(700, 640),
                      text="Rain is not salty.\nRivers are not salty.\nSo why is the SEA?",
                      text_size=68)
    tk.caption(d, "Every drop flowing in tastes of nothing at all", 50, y=956)
    return tk.vignette(img)


# --------------------------------------------------------------------------
# Scene 3 -- name the misconception, then kill it
# --------------------------------------------------------------------------
def scene_03():
    img, d = tk.canvas("day")
    tk.cloud(d, 1500, 250, 1.0, color=GREY_CLOUD)
    tk.mountain(d, 1560, 880, 700, 520)
    tk.mountain(d, 1200, 890, 460, 340)
    tk.sea(d, 900, phase=2.1)
    tk.title_text(d, (700, 150), "It was not the fish", 86, fill=P["white"], stroke=13)
    tk.speech_pop(d, 430, 400, "the fish did it?", 56, fill=P["white"])
    tk.speech_pop(d, 470, 560, "NOPE!", 78, fill=P["rocket_red"], text_fill=P["white"])
    tk.speech_pop(d, 480, 740, "a ship spilled it?", 56, fill=P["white"])
    tk.speech_pop(d, 520, 900, "NOPE!", 78, fill=P["rocket_red"], text_fill=P["white"])
    tk.title_text(d, (1420, 380), "it starts\nup HERE", 62, fill=P["accent"], stroke=12)
    return tk.vignette(img)


# --------------------------------------------------------------------------
# Scene 4 -- secret 1: falling rain picks up CO2 and turns slightly sour
# --------------------------------------------------------------------------
def scene_04():
    img, d = tk.canvas("day")
    tk.cloud(d, 980, 260, 2.0, color=GREY_CLOUD)
    tk.rainfall(d, (520, 430, 1440, 900), n=38, seed=11, size=(18, 30))
    tk.ground(d, 940)
    # the gas the rain is collecting on the way down
    tk.molecule_field(d, n=9, seed=6, area=(1420, 300, 1860, 880),
                      r_range=(30, 44), color=(178, 216, 244))
    tk.title_text(d, (720, 140), "Secret 1: rain is a\ntiny bit SOUR", 76,
                  fill=P["white"], stroke=13)
    tk.speech_pop(d, 1620, 220, "carbon dioxide", 50, fill=P["accent"])
    tk.caption(d, "Too weak for your tongue -- strong enough for rock", 50, y=1000)
    return tk.vignette(img)


# --------------------------------------------------------------------------
# Scene 5 -- sour rain nibbles specks of mineral out of the stone
# --------------------------------------------------------------------------
def scene_05():
    img, d = tk.canvas("day")
    tk.cloud(d, 700, 220, 1.4, color=GREY_CLOUD)
    tk.mountain(d, 780, 940, 900, 660)
    tk.rainfall(d, (420, 300, 1140, 880), n=34, seed=4, size=(16, 28))
    tk.ground(d, 940)
    salt_sprinkle(d, [(1290, 560, 10), (1450, 690, -8), (1330, 830, 22),
                      (1560, 850, -18)], 74)
    tk.arrow(d, (1120, 520), (1260, 560), color=P["white"], width=12, head=34)
    tk.title_text(d, (1420, 250), "drip, drip,\nNIBBLE", 76, fill=P["accent"], stroke=13)
    tk.caption(d, "Thousands of years to loosen one tiny speck", 50, y=1000)
    return tk.vignette(img)


# --------------------------------------------------------------------------
# Scene 6 -- rivers carry the specks downhill to the sea
# --------------------------------------------------------------------------
def scene_06():
    img, d = tk.canvas("day")
    tk.sun(d, 1660, 180, 92, rotate=6)
    # the land has to sit high enough for the river to run over green, not sky:
    # a blue river on a blue background was invisible in the first pass
    tk.ground(d, 700)
    tk.mountain(d, 420, 720, 760, 560)
    tk.river(d, [(470, 350), (560, 480), (700, 610), (940, 700), (1260, 780),
                 (1620, 830)], width=42, taper=3.0)
    tk.sea(d, 860, phase=0.9)
    salt_sprinkle(d, [(800, 640, 12), (1120, 726, -10), (1440, 792, 18)], 52)
    tk.title_text(d, (1180, 200), "Rivers ARE salty", 84, fill=P["white"], stroke=13)
    tk.speech_pop(d, 1230, 380, "just far too weak to taste", 50, fill=P["white"])
    tk.caption(d, "One river, one day, one grain at a time", 50, y=1000)
    return tk.vignette(img)


# --------------------------------------------------------------------------
# Scene 7 -- secret 2: the water can leave, the salt cannot
# --------------------------------------------------------------------------
def scene_07():
    img, d = tk.canvas("day")
    tk.sun(d, 1640, 190, 118, rotate=16)
    tk.sea(d, 780, phase=1.7)
    for x in (420, 760, 1100):
        vapour(d, x, 760, n=3, height=380, spread=84)
    salt_sprinkle(d, [(520, 900, 8), (880, 960, -14), (1240, 900, 20),
                      (1560, 970, -6)], 74)
    tk.arrow(d, (1430, 700), (1430, 430), color=P["white"], width=14, head=40)
    tk.title_text(d, (830, 150), "Secret 2: the salt trap", 84,
                  fill=P["white"], stroke=13)
    tk.speech_pop(d, 1520, 560, "water flies\nsalt stays", 54, fill=P["accent"])
    return tk.vignette(img)


# --------------------------------------------------------------------------
# Scene 8 -- billions of years of that, piled up
# --------------------------------------------------------------------------
def scene_08():
    img, d = tk.canvas("day")
    tk.sea(d, 720, phase=2.6)
    tk.wave(d, 420, 720, 520, 0.8)
    tk.wave(d, 1480, 720, 560, 0.9)
    salt_sprinkle(d, [(300, 900, 6), (560, 980, -12), (860, 900, 18),
                      (1120, 990, -4), (1420, 910, 14), (1700, 985, -20)], 82)
    tk.title_text(d, (960, 200), "Billions of years of it", 92,
                  fill=P["white"], stroke=14)
    tk.speech_pop(d, 960, 400, "a spoonful of salt in every big bottle", 54,
                  fill=P["accent"])
    tk.caption(d, "Spread on land it would stand fifty storeys tall", 50, y=1000)
    return tk.vignette(img)


# --------------------------------------------------------------------------
# Scene 9 -- bonus wonder: floating, and the experiment to try at home
# --------------------------------------------------------------------------
def scene_09():
    img, d = tk.canvas("day")
    tk.sun(d, 1700, 170, 96, rotate=24)
    tk.sea(d, 800, color=SALTY, deep=(118, 178, 216), phase=0.3)
    tk.kid(d, 470, 980, scale=1.1, arms="up", mouth="o", looking="front")
    # the waterline drawn back over the legs: the kid is IN the sea, not on it
    tk.puddle(d, 470, 950, 330, 74, color=SALTY, shine=False)
    # clear of the raised hands: at y=470 the badge sat on the kid's forehead
    tk.speech_pop(d, 470, 350, "I FLOAT!", 72, fill=P["accent"])
    # the saucer experiment, on the right
    tk.puddle(d, 1440, 930, 340, 78, color=(206, 236, 255))
    salt_sprinkle(d, [(1330, 895, 10), (1470, 930, -14), (1580, 890, 20)], 58)
    tk.title_text(d, (1420, 620), "leave it in the sun --\nthe salt comes back", 56,
                  fill=P["white"], stroke=12)
    tk.title_text(d, (900, 150), "Bonus wonder", 82, fill=P["white"], stroke=13)
    return tk.vignette(img)


# --------------------------------------------------------------------------
# Scene 10 -- outro (bottom-right 40% stays clear for YouTube end cards)
# --------------------------------------------------------------------------
def scene_10():
    img, d = tk.canvas("night")
    tk.stars(d, n=110, seed=21, area=(0, 0, 1920, 880))
    zones = tk.end_screen_guides(d)   # safe-zone contract for this frame
    tk.sea(d, 940, color=(38, 84, 132), deep=(26, 62, 104), phase=1.1)
    tk.rocket(d, 250, 540, scale=1.15, face=True)
    tk.salt_crystal(d, 560, 300, 92, rotate=12)
    tk.title_text(d, (1060, 160), "Mission complete!", 100, fill=P["accent"], stroke=15)
    tk.title_text(d, (1000, 380), "Sour rain frees the salt,\nrivers deliver it,\n"
                                  "the Sun leaves it behind",
                  56, fill=P["white"], stroke=11)
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
