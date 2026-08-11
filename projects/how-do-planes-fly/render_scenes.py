#!/usr/bin/env python3
"""
Episode 2 -- "How Do Planes FLY?"

Draws frames/scene_01.png .. scene_10.png at 1920x1080 using only
engine/toolkit.py primitives. The plane, airfoil, wind-streak and labelled
force-arrow primitives were added to the toolkit for this episode -- they are
channel property now, not episode property.

    python3 render_scenes.py            # all scenes
    python3 render_scenes.py 4 5        # only scenes 4 and 5
    python3 render_scenes.py --sheet    # also write frames/contact_sheet.jpg
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from engine import toolkit as tk  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FRAMES = os.path.join(HERE, "frames")

P = tk.PALETTE
LIFT_C = (46, 150, 96)
WEIGHT_C = (208, 74, 96)
THRUST_C = (72, 118, 226)
DRAG_C = (150, 96, 196)


def out(n):
    return os.path.join(FRAMES, f"scene_{n:02d}.png")


# --------------------------------------------------------------------------
# Scene 1 -- title card
# --------------------------------------------------------------------------
def scene_01():
    img, d = tk.canvas("day")
    tk.sun(d, 168, 148, 100, rotate=12)
    tk.cloud(d, 1500, 760, 0.72)
    tk.cloud(d, 380, 640, 0.6)
    tk.ground(d, 920)
    tk.wind_streaks(d, 1080, 300, n=4, length=260, spread=150, width=8)
    tk.plane(d, 1500, 300, 0.78)
    tk.rocket(d, 1700, 830, scale=0.42, face=True)

    tk.title_text(d, (760, 152), "WONDER-O-NAUTS", 74, fill=P["accent"], stroke=11)
    tk.title_text(d, (760, 470), "How do planes\nFLY?", 148, fill=P["white"], stroke=15)
    tk.speech_pop(d, 660, 762, "Science for kids!", 54, fill=P["white"])
    return tk.vignette(img)


# --------------------------------------------------------------------------
# Scene 2 -- the big question
# --------------------------------------------------------------------------
def scene_02():
    img, d = tk.canvas("day")
    tk.sun(d, 1740, 176, 96, rotate=20)
    tk.cloud(d, 300, 260, 0.8)
    tk.ground(d, 890)
    tk.plane(d, 1240, 250, 0.5)
    tk.kid(d, 480, 1020, scale=1.05, arms="down", mouth="o", looking="up")
    tk.thought_bubble(d, 1180, 560, w=900, h=380, tail_to=(660, 660),
                      text="How do planes\nFLY?", text_size=92)
    return tk.vignette(img)


# --------------------------------------------------------------------------
# Scene 3 -- air is real stuff
# --------------------------------------------------------------------------
def scene_03():
    img, d = tk.canvas("day")
    tk.ground(d, 980)
    tk.molecule_field(d, n=40, seed=17, area=(620, 210, 1840, 900), r_range=(24, 46))
    tk.wind_streaks(d, 640, 620, n=6, length=520, spread=420, width=11, seed=4)
    tk.kid(d, 420, 1010, scale=1.05, arms="one_up", mouth="smile", looking="front")
    tk.title_text(d, (1080, 132), "Air is REAL stuff!", 84, fill=P["white"], stroke=13)
    tk.caption(d, "Trillions of tiny molecules you can feel but not see", 50, y=950)
    return tk.vignette(img)


# --------------------------------------------------------------------------
# Scene 4 -- the wing throws air downward
# --------------------------------------------------------------------------
def scene_04():
    img, d = tk.canvas("day")
    tk.ground(d, 1010)
    # air arrives level, leaves heading downward -- that is the whole trick
    tk.wind_streaks(d, 90, 440, n=6, length=460, spread=210, width=11, seed=6)
    tk.wind_streaks(d, 1010, 520, n=6, length=520, spread=200, width=11,
                    curve=230, seed=7)
    tk.airfoil(d, 800, 500, 1.9, angle=13)
    tk.force_arrow(d, (1380, 700), (1380, 906), "AIR PUSHED DOWN", color=THRUST_C,
                   width=18, label_size=42, label_off=(-210, 40))
    tk.title_text(d, (900, 132), "The wing throws air DOWNWARD", 74,
                  fill=P["white"], stroke=12)
    return tk.vignette(img)


# --------------------------------------------------------------------------
# Scene 5 -- and the air pushes back: lift
# --------------------------------------------------------------------------
def scene_05():
    img, d = tk.canvas("day")
    tk.ground(d, 1010)
    tk.wind_streaks(d, 120, 520, n=5, length=420, spread=180, width=10, seed=6)
    tk.wind_streaks(d, 980, 600, n=5, length=460, spread=170, width=10,
                    curve=210, seed=7)
    tk.airfoil(d, 800, 580, 1.8, angle=13)
    tk.force_arrow(d, (800, 470), (800, 250), "LIFT", color=LIFT_C, width=22,
                   label_size=62, label_off=(0, -60))
    tk.force_arrow(d, (1370, 646), (1370, 800), "air down", color=THRUST_C,
                   width=14, label_size=38, label_off=(-196, 4))
    tk.caption(d, "Push the air down, and the air pushes you UP", 52, y=950)
    return tk.vignette(img)


# --------------------------------------------------------------------------
# Scene 6 -- thrust
# --------------------------------------------------------------------------
def scene_06():
    img, d = tk.canvas("day")
    tk.cloud(d, 320, 250, 0.7)
    tk.cloud(d, 1640, 620, 0.55)
    tk.ground(d, 960)
    tk.wind_streaks(d, 120, 420, n=6, length=520, spread=260, width=11, seed=9)
    tk.plane(d, 1180, 440, 1.05)
    tk.force_arrow(d, (860, 760), (1420, 760), "THRUST", color=THRUST_C, width=22,
                   label_size=58, label_off=(0, -70))
    tk.title_text(d, (900, 132), "Engines push the plane FORWARD", 72,
                  fill=P["white"], stroke=12)
    return tk.vignette(img)


# --------------------------------------------------------------------------
# Scene 7 -- the four forces
# --------------------------------------------------------------------------
def scene_07():
    img, d = tk.canvas("day")
    tk.ground(d, 1020)
    tk.plane(d, 960, 540, 0.92)
    tk.force_arrow(d, (960, 400), (960, 210), "LIFT", color=LIFT_C, width=20,
                   label_size=52, label_off=(0, -56))
    tk.force_arrow(d, (960, 680), (960, 872), "WEIGHT", color=WEIGHT_C, width=20,
                   label_size=52, label_off=(0, 56))
    tk.force_arrow(d, (1240, 545), (1610, 545), "THRUST", color=THRUST_C, width=20,
                   label_size=52, label_off=(60, -70))
    tk.force_arrow(d, (700, 545), (330, 545), "DRAG", color=DRAG_C, width=20,
                   label_size=52, label_off=(-50, -70))
    tk.caption(d, "Lift beats weight and up you go!", 54, y=950)
    return tk.vignette(img)


# --------------------------------------------------------------------------
# Scene 8 -- try it yourself
# --------------------------------------------------------------------------
def scene_08():
    img, d = tk.canvas("day")
    tk.cloud(d, 1560, 250, 0.62)
    tk.ground(d, 900)
    # dotted flight path arcing away from the kid's hand
    for i in range(9):
        t = i / 8.0
        x = 700 + t * 560
        y = 620 - 210 * t + 150 * t * t
        r = 11 - i * 0.5
        d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255))
    tk.paper_plane(d, 1330, 560, 1.5)
    tk.wind_streaks(d, 900, 520, n=3, length=200, spread=110, width=8, seed=12)
    tk.kid(d, 480, 1020, scale=1.1, arms="point_up", mouth="smile", looking="up")
    tk.title_text(d, (1120, 150), "Try it yourself!", 92, fill=P["accent"], stroke=14)
    tk.caption(d, "Fold a paper plane and give it a push", 52, y=950)
    return tk.vignette(img)


# --------------------------------------------------------------------------
# Scene 9 -- bonus: why runways are long
# --------------------------------------------------------------------------
def scene_09():
    img, d = tk.canvas("day")
    tk.cloud(d, 400, 240, 0.66)
    tk.ground(d, 880)
    # runway with dashed centre line
    d.rectangle([0, 880, 1920, 1080], fill=(86, 92, 108))
    d.rectangle([0, 874, 1920, 882], fill=(228, 232, 240))
    for i in range(11):
        x = 40 + i * 180
        d.rectangle([x, 952, x + 120, 968], fill=(244, 246, 252))
    tk.wind_streaks(d, 90, 600, n=5, length=560, spread=230, width=12, seed=21)
    tk.plane(d, 1310, 520, 0.95, pitch=12)
    tk.title_text(d, (860, 132), "Why runways are so LONG", 76,
                  fill=P["white"], stroke=12)
    tk.caption(d, "Faster wing = more air pushed down = more lift", 50, y=822)
    return tk.vignette(img)


# --------------------------------------------------------------------------
# Scene 10 -- outro (bottom-right 40% stays clear for end cards)
# --------------------------------------------------------------------------
def scene_10():
    img, d = tk.canvas("night")
    tk.stars(d, n=110, seed=14, area=(0, 0, 1920, 900))
    zones = tk.end_screen_guides(d)   # safe-zone contract for this frame
    tk.ground(d, 960, color=(46, 96, 92), dark=(34, 78, 78))
    tk.rocket(d, 250, 540, scale=1.15, face=True)
    tk.plane(d, 640, 250, 0.42, body=(226, 234, 248))
    tk.title_text(d, (1060, 160), "Mission complete!", 100, fill=P["accent"], stroke=15)
    tk.title_text(d, (1010, 380), "Wings throw air down\nThe air lifts the plane up",
                  60, fill=P["white"], stroke=11)
    tk.speech_pop(d, 760, 590, "LIKE + SUBSCRIBE", 58, fill=P["rocket_red"],
                  text_fill=P["white"])
    tk.title_text(d, (640, 800), "What should we explore next?", 48,
                  fill=P["white"], stroke=10)
    # prove it, do not assume it: nothing important may sit under the end cards
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
