#!/usr/bin/env python3
"""
Scaffold a new episode folder.

    python3 new_episode.py how-do-planes-fly
    python3 new_episode.py how-do-planes-fly --title "How Do Planes FLY?" --scenes 10

Creates projects/<slug>/ with a video.json skeleton and a render_scenes.py that
already draws placeholder frames, so `python3 factory.py projects/<slug>` works
the moment the folder exists. Then hand video.json to Claude with your topic and
paste back the finished script + scene art.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECTS = os.path.join(HERE, "projects")

RENDER_TEMPLATE = '''#!/usr/bin/env python3
"""
{title}

Draws frames/scene_01.png .. scene_{n:02d}.png at 1920x1080 from
engine/toolkit.py primitives only. Replace each placeholder body with the real
composition -- add new primitives to engine/toolkit.py, never inline here.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from engine import toolkit as tk  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FRAMES = os.path.join(HERE, "frames")

P = tk.PALETTE
RB = tk.RAINBOW


def out(n):
    return os.path.join(FRAMES, f"scene_{{n:02d}}.png")


def placeholder(n, label, outro=False):
    """Temporary frame so the pipeline runs before the art is finished.

    Everything sits inside tk.SAFE (the Ken Burns zoom crops the edges) and
    clear of the bottom-right end-card zone, so a scaffolded episode passes
    tests/unit.py before a single line of real art is drawn.
    """
    img, d = tk.canvas("day" if n % 2 else "night")
    tk.ground(d, 900)
    zones = tk.end_screen_guides(d)
    tk.rocket(d, 330, 560, scale=0.9, face=True)
    tk.title_text(d, (900, 200), "WONDER-O-NAUTS", 64, fill=P["accent"], stroke=10)
    tk.title_text(d, (880, 430), label, 96, fill=P["white"], stroke=14)
    if outro:
        assert not tk.safe_zone_violations(zones["end_cards"]), \
            tk.safe_zone_violations(zones["end_cards"])
    return tk.vignette(img)


{scene_fns}

SCENES = [{scene_list}]


def render(only=None):
    os.makedirs(FRAMES, exist_ok=True)
    for i, fn in enumerate(SCENES, 1):
        if only and i not in only:
            continue
        print(f"  scene {{i:02d}} -> {{os.path.relpath(tk.save(fn(), out(i)), HERE)}}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--sheet"]
    render({{int(a) for a in args}} if args else None)
    if "--sheet" in sys.argv[1:]:
        tk.contact_sheet([out(i) for i in range(1, len(SCENES) + 1)],
                         os.path.join(FRAMES, "contact_sheet.jpg"))
'''

SFX_CYCLE = ["sparkle", "pop", "whoosh", "whoosh", "whoosh", "pop", "whoosh",
             "sparkle", "whoosh", "success"]


def slugify(s: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return re.sub(r"-{2,}", "-", s) or "new-episode"


def title_from_slug(slug: str) -> str:
    return slug.replace("-", " ").strip().capitalize() + "?"


def scaffold(slug: str, title: str | None = None, n_scenes: int = 10,
             force: bool = False) -> str:
    slug = slugify(slug)
    title = title or title_from_slug(slug)
    proj = os.path.join(PROJECTS, slug)
    if os.path.exists(proj) and not force:
        raise SystemExit(f"projects/{slug} already exists (use --force to overwrite)")
    os.makedirs(os.path.join(proj, "frames"), exist_ok=True)

    cfg = {
        "title": f"{title} 🌈 Science for Kids | Wonder-o-nauts",
        "voice": "en-US-AnaNeural",
        "rate": "-8%",
        "description": (f"{title} Blast off with the Wonder-o-nauts and find out!\n\n"
                        "In this episode:\n"
                        "☀️ TODO bullet one\n"
                        "🔺 TODO bullet two\n"
                        "💨 TODO bullet three\n\n"
                        "What should we explore next? Tell us in the comments!\n\n"
                        "#kidsscience #stemforkids #wonderonauts #scienceforkids"),
        "tags": f"kids science, {slug.replace('-', ' ')}, science for kids, "
                "STEM for kids, educational video for children, wonder-o-nauts",
        "thumbnail_text": title.replace("?", "").strip().upper()[:18] + "?",
        "music": True,
        # stable across machines and runs -- Python's str hash is randomized
        "music_seed": int(hashlib.sha256(slug.encode()).hexdigest()[:8], 16) % 97 + 1,
        "bgm_vol": 0.13,
        "shorts_scenes": [2, min(6, n_scenes), min(8, n_scenes)],
        "scenes": [{
            "image": f"frames/scene_{i:02d}.png",
            "chapter": "Blast off!" if i == 1 else (
                "Mission complete!" if i == n_scenes else f"TODO chapter {i}"),
            "sfx": SFX_CYCLE[(i - 1) % len(SFX_CYCLE)],
            "narration": ("Hello, Wonder-o-nauts! Welcome aboard our rocket of "
                          "curiosity!" if i == 1 else
                          f"TODO: write scene {i} narration here. Two to four short "
                          "sentences, spoken to a curious six year old."),
        } for i in range(1, n_scenes + 1)],
    }
    with open(os.path.join(proj, "video.json"), "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
        f.write("\n")

    fns = "\n\n".join(
        f'def scene_{i:02d}():\n    return placeholder({i}, "Scene {i}"'
        + (", outro=True)" if i == n_scenes else ")")
        for i in range(1, n_scenes + 1))
    lst = ", ".join(f"scene_{i:02d}" for i in range(1, n_scenes + 1))
    with open(os.path.join(proj, "render_scenes.py"), "w", encoding="utf-8") as f:
        f.write(RENDER_TEMPLATE.format(title=title, n=n_scenes,
                                       scene_fns=fns, scene_list=lst))

    print(f"  created projects/{slug}/")
    print(f"    video.json        {n_scenes} scenes (TODO narration)")
    print("    render_scenes.py  placeholder art")
    print("\n  next: draft the script, then run")
    print(f"    python3 factory.py projects/{slug} --preview")
    return proj


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="new_episode.py",
                                 description="Scaffold a Wonder-o-nauts episode.")
    ap.add_argument("slug", help="folder name, e.g. how-do-planes-fly")
    ap.add_argument("--title", help="display title (default: derived from the slug)")
    ap.add_argument("--scenes", type=int, default=10, help="scene count (default 10)")
    ap.add_argument("--force", action="store_true", help="overwrite an existing folder")
    a = ap.parse_args(argv)
    scaffold(a.slug, a.title, a.scenes, a.force)
    return 0


if __name__ == "__main__":
    sys.exit(main())
