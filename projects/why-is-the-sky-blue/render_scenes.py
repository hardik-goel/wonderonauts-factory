#!/usr/bin/env python3
"""
Episode 1 -- "Why Is the Sky BLUE?"

Draws frames/scene_01.png .. scene_10.png at 1920x1080 using only
engine/toolkit.py primitives. Run directly to (re)render, or let factory.py
call it automatically when frames are missing.

    python3 render_scenes.py            # all scenes
    python3 render_scenes.py 3 7        # only scenes 3 and 7
    python3 render_scenes.py --sheet    # also write frames/contact_sheet.jpg
"""

import math
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from engine import toolkit as tk  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FRAMES = os.path.join(HERE, "frames")

P = tk.PALETTE
RB = tk.RAINBOW


def out(n):
    return os.path.join(FRAMES, f"scene_{n:02d}.png")


# --------------------------------------------------------------------------
# Scene 1 -- title card
# --------------------------------------------------------------------------
def scene_01():
    img, d = tk.canvas("day")
    tk.sun(d, 172, 150, 104, rotate=8)
    tk.cloud(d, 1700, 176, 0.78)
    tk.cloud(d, 1180, 300, 0.5)
    tk.cloud(d, 250, 620, 0.66)
    tk.ground(d, 900)

    # rocket blasting up the right side, puff trail below it
    for i, k in enumerate((0.0, 1.0)):
        tk.cloud(d, 1548 + i * 26, 934 + k * 74, 0.22 - i * 0.06)
    tk.rocket(d, 1540, 600, scale=1.05, face=True)

    tk.title_text(d, (800, 152), "WONDER-O-NAUTS", 74, fill=P["accent"], stroke=11)
    tk.title_text(d, (800, 430), "Why is the sky\nBLUE?", 152, fill=P["white"], stroke=15)
    tk.speech_pop(d, 700, 730, "Light science for kids!", 54, fill=P["white"])
    return tk.vignette(img)


# --------------------------------------------------------------------------
# Scene 2 -- the big question
# --------------------------------------------------------------------------
def scene_02():
    img, d = tk.canvas("day")
    tk.sun(d, 1700, 190, 104, rotate=14)
    tk.cloud(d, 420, 200, 0.9)
    tk.cloud(d, 1180, 300, 0.6)
    tk.ground(d, 880)
    tk.kid(d, 520, 1010, scale=1.05, arms="down", mouth="o", looking="up")
    tk.thought_bubble(d, 1270, 350, w=880, h=400,
                      tail_to=(700, 640),
                      text="Why is the sky\nBLUE?", text_size=96)
    # doubt-colors floating around the bubble
    for i, c in enumerate([RB[0], RB[3], RB[6]]):
        x = 1010 + i * 250
        d.ellipse([x - 26, 660, x + 26, 712], fill=c)
    return tk.vignette(img)


# --------------------------------------------------------------------------
# Scene 3 -- sunlight is a hidden rainbow
# --------------------------------------------------------------------------
def scene_03():
    img, d = tk.canvas("day")
    tk.ground(d, 960)
    cx, cy = 330, 300
    for i, c in enumerate(RB):
        a = math.radians(2 + i * 12.5)
        x2 = cx + math.cos(a) * 1560
        y2 = cy + math.sin(a) * 1560
        tk.zig_ray(d, (cx + 150, cy + 40), (x2, y2), color=c,
                   amplitude=26, wavelength=150, width=15, phase=i * 0.7)
    tk.sun(d, cx, cy, 165, rotate=6)
    tk.title_text(d, (1150, 128), "White light = ALL the colors!", 70,
                  fill=P["white"], stroke=12)
    for i, name in enumerate(tk.RAINBOW_NAMES):
        x = 300 + i * 224
        d.rounded_rectangle([x - 96, 898, x + 96, 982], radius=42, fill=RB[i])
        tk.title_text(d, (x, 940), name.upper(), 40, fill=P["white"], stroke=6)
    return tk.vignette(img)


# --------------------------------------------------------------------------
# Scene 4 -- the prism proof
# --------------------------------------------------------------------------
def scene_04():
    img, d = tk.canvas("day")
    tk.ground(d, 980)
    px, py = 900, 520
    # incoming white beam
    d.line([(60, 430), (px - 60, 500)], fill=P["white"], width=26)
    tk.title_text(d, (300, 340), "white light", 52, fill=P["white"], stroke=9)
    tk.prism(d, px, py, 340)
    # fanned rainbow arrows out the right side
    for i, c in enumerate(RB):
        a = math.radians(-22 + i * 9.5)
        tk.arrow(d, (px + 110, py + 40),
                 (px + 110 + math.cos(a) * 800, py + 40 + math.sin(a) * 800),
                 color=c, width=17, head=40)
    tk.title_text(d, (1520, 200), "RAINBOW!", 96, fill=P["accent"], stroke=14)
    tk.caption(d, "A prism splits light into 7 colors", 54, y=950)
    return tk.vignette(img)


# --------------------------------------------------------------------------
# Scene 5 -- the air is full of tiny molecules
# --------------------------------------------------------------------------
def scene_05():
    img, d = tk.canvas("day")
    tk.ground(d, 990)
    tk.molecule_field(d, n=62, seed=11, area=(90, 170, 1840, 940), r_range=(22, 44))
    tk.title_text(d, (960, 132), "The air is FULL of tiny molecules", 74,
                  fill=P["white"], stroke=12)
    return tk.vignette(img)


# --------------------------------------------------------------------------
# Scene 6 -- blue light bounces
# --------------------------------------------------------------------------
def scene_06():
    img, d = tk.canvas("day")
    tk.ground(d, 1000)
    tk.sun(d, 150, 130, 96, ray_len=0.4)
    spots = [(430, 300), (760, 520), (1120, 260), (1360, 620), (700, 830), (1620, 400)]
    # incoming sunbeam, then blue arrows sprayed out of every molecule
    tk.zig_ray(d, (200, 210), (430, 300), color=P["white"], amplitude=16,
               wavelength=90, width=14)
    for i, (x, y) in enumerate(spots):
        for k in range(6):
            a = math.radians(20 + k * 60 + i * 17)
            tk.arrow(d, (x + math.cos(a) * 62, y + math.sin(a) * 62),
                     (x + math.cos(a) * 205, y + math.sin(a) * 205),
                     color=P["blue_ray"], width=12, head=32)
    for x, y in spots:
        tk.molecule(d, x, y, 54)
    tk.speech_pop(d, 960, 142, "BOING! BOING! BOING!", 66)
    tk.caption(d, "Scattering: blue light bounces everywhere", 52, y=950)
    return tk.vignette(img)


# --------------------------------------------------------------------------
# Scene 7 -- why only blue?
# --------------------------------------------------------------------------
def scene_07():
    img, d = tk.canvas("day")
    tk.ground(d, 1010)
    # long lazy red/orange waves sail straight past
    for i, c in enumerate((P["red_ray"], RB[1])):
        y = 300 + i * 130
        tk.zig_ray(d, (60, y), (1860, y), color=c, amplitude=42,
                   wavelength=330, width=17, phase=i * 1.1)
    tk.title_text(d, (960, 178), "long, lazy waves zoom straight past", 54,
                  fill=P["white"], stroke=10)

    # short wiggly blue wave slams into a molecule and sprays outward
    mx, my = 1150, 760
    tk.zig_ray(d, (60, my), (mx - 70, my), color=P["blue_ray"], amplitude=34,
               wavelength=78, width=17)
    for k in range(5):
        a = math.radians(-70 + k * 36)
        tk.arrow(d, (mx + math.cos(a) * 80, my + math.sin(a) * 80),
                 (mx + math.cos(a) * 260, my + math.sin(a) * 260),
                 color=P["blue_ray"], width=13, head=34)
    tk.molecule(d, mx, my, 70)
    tk.title_text(d, (520, 900), "short, wiggly waves BOUNCE", 54,
                  fill=P["white"], stroke=10)
    return tk.vignette(img)


# --------------------------------------------------------------------------
# Scene 8 -- the whole sky glows blue
# --------------------------------------------------------------------------
def scene_08():
    img, d = tk.canvas("day")
    # blue light raining down from every direction
    import random
    rnd = random.Random(21)
    for _ in range(150):
        x = rnd.uniform(20, 1900)
        y = rnd.uniform(40, 900)
        r = rnd.uniform(9, 22)
        d.ellipse([x - r, y - r, x + r, y + r], fill=P["blue_ray"])
    for i in range(9):
        x = 120 + i * 210
        tk.arrow(d, (x, 120), (x - 40, 470), color=(150, 200, 255), width=10, head=28)
    tk.ground(d, 900)
    tk.kid(d, 960, 1030, scale=1.15, arms="up", mouth="o", looking="up")
    tk.title_text(d, (960, 136), "The WHOLE sky glows blue!", 84, fill=P["white"], stroke=13)
    return tk.vignette(img)


# --------------------------------------------------------------------------
# Scene 9 -- sunset bonus
# --------------------------------------------------------------------------
def scene_09():
    img, d = tk.canvas("sunset")
    # only the long red/orange waves survive the long path through the air
    for i, c in enumerate((P["red_ray"], RB[1], RB[2])):
        tk.zig_ray(d, (1720, 690), (40, 340 + i * 150), color=c,
                   amplitude=40, wavelength=340, width=18, phase=i * 0.9)
    tk.sun(d, 1720, 700, 150, rays=True, ray_len=0.35,
           color=(255, 172, 92), ray_color=(238, 126, 74), rotate=10)
    tk.ground(d, 900, color=(74, 78, 118), dark=(56, 58, 96))
    # blue got scattered away long before it arrived
    for i in range(4):
        x = 240 + i * 190
        tk.molecule(d, x, 250 + (i % 2) * 90, 34, color=(150, 170, 210), face=False)
    tk.title_text(d, (600, 148), "Blue scattered away...\nonly RED reaches you!", 66,
                  fill=P["white"], stroke=12)
    tk.kid(d, 620, 1030, scale=0.82, arms="down", mouth="smile", looking="up",
           shirt=(72, 66, 140))
    return tk.vignette(img)


# --------------------------------------------------------------------------
# Scene 10 -- outro (bottom-right 40% stays clear for end cards)
# --------------------------------------------------------------------------
def scene_10():
    img, d = tk.canvas("night")
    tk.stars(d, n=110, seed=9, area=(0, 0, 1920, 900))
    zones = tk.end_screen_guides(d)  # safe-zone contract for this frame
    tk.ground(d, 960, color=(46, 96, 92), dark=(34, 78, 78))
    tk.rocket(d, 240, 530, scale=1.2, face=True)
    tk.title_text(d, (1090, 160), "Mission complete!", 100, fill=P["accent"], stroke=15)
    tk.title_text(d, (1040, 370), "Sunlight = hidden rainbow\nMolecules bounce the blue",
                  60, fill=P["white"], stroke=11)
    tk.speech_pop(d, 760, 590, "LIKE + SUBSCRIBE", 58, fill=P["rocket_red"],
                  text_fill=P["white"])
    tk.title_text(d, (742, 800), "What should we explore next?", 50,
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
    only = {int(a) for a in args} if args else None
    render(only)
    if "--sheet" in sys.argv[1:]:
        sheet = tk.contact_sheet([out(i) for i in range(1, len(SCENES) + 1)],
                                 os.path.join(FRAMES, "contact_sheet.jpg"))
        print(f"  contact sheet -> {os.path.relpath(sheet, HERE)}")
