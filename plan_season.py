#!/usr/bin/env python3
"""
Season planner -- the production dashboard, deliberately kept tiny.

    python3 plan_season.py add how-do-planes-fly       # scaffold + register
    python3 plan_season.py status                      # the table
    python3 plan_season.py set how-do-planes-fly ready # move it along
    python3 plan_season.py remove how-do-planes-fly    # unregister (keeps files)

Statuses flow: draft -> scripted -> ready -> published.
`factory.py --all` builds only the episodes marked `ready`.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SEASON = os.path.join(HERE, "season.json")
STATUSES = ["draft", "scripted", "ready", "published"]


def load():
    if not os.path.exists(SEASON):
        return {"season": "Season 1", "episodes": []}
    with open(SEASON, encoding="utf-8") as f:
        return json.load(f)


def save(data):
    with open(SEASON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def find(data, slug):
    return next((e for e in data["episodes"] if e["slug"] == slug), None)


def cmd_add(a):
    import new_episode

    data = load()
    slug = new_episode.slugify(a.slug)
    proj = os.path.join(HERE, "projects", slug)
    if not os.path.exists(proj):
        new_episode.scaffold(slug, a.title, a.scenes)
    else:
        print(f"  projects/{slug}/ already exists -- registering it as is")
    if find(data, slug):
        print(f"  {slug} is already in season.json")
    else:
        title = a.title or slug.replace("-", " ").title()
        if os.path.exists(os.path.join(proj, "video.json")):
            with open(os.path.join(proj, "video.json"), encoding="utf-8") as f:
                title = json.load(f).get("title", title)
        data["episodes"].append({"slug": slug, "title": title, "status": "draft"})
        save(data)
        print(f"  registered {slug} as draft")
    return cmd_status(a)


def cmd_set(a):
    data = load()
    if a.status not in STATUSES:
        raise SystemExit(f"status must be one of {STATUSES}")
    e = find(data, a.slug)
    if not e:
        raise SystemExit(f"{a.slug} is not in season.json -- add it first")
    old, e["status"] = e["status"], a.status
    save(data)
    print(f"  {a.slug}: {old} -> {a.status}")
    return cmd_status(a)


def cmd_remove(a):
    data = load()
    n = len(data["episodes"])
    data["episodes"] = [e for e in data["episodes"] if e["slug"] != a.slug]
    save(data)
    print(f"  {'removed' if len(data['episodes']) < n else 'not found:'} {a.slug}"
          " (project files kept on disk)")
    return cmd_status(a)


def cmd_status(a=None):
    data = load()
    eps = data["episodes"]
    print(f"\n  {data.get('season', 'Season')}  --  {len(eps)} episodes")
    print(f"  {'#':<3} {'status':<10} {'slug':<30} title")
    print("  " + "-" * 76)
    for i, e in enumerate(eps, 1):
        print(f"  {i:<3} {e.get('status', '?'):<10} {e['slug']:<30} {e.get('title', '')[:36]}")
    print("  " + "-" * 76)
    counts = {s: sum(1 for e in eps if e.get("status") == s) for s in STATUSES}
    print("  " + "   ".join(f"{s}: {counts[s]}" for s in STATUSES))
    if counts["ready"]:
        print("\n  build them: python3 factory.py --all --shorts")
    print()
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="plan_season.py", description=__doc__.split("\n")[1])
    sub = ap.add_subparsers(dest="cmd")

    p = sub.add_parser("add", help="scaffold an episode and register it as draft")
    p.add_argument("slug")
    p.add_argument("--title")
    p.add_argument("--scenes", type=int, default=10)
    p.set_defaults(fn=cmd_add)

    p = sub.add_parser("set", help="change an episode's status")
    p.add_argument("slug")
    p.add_argument("status", choices=STATUSES)
    p.set_defaults(fn=cmd_set)

    p = sub.add_parser("remove", help="unregister an episode")
    p.add_argument("slug")
    p.set_defaults(fn=cmd_remove)

    sub.add_parser("status", help="print the season table").set_defaults(fn=cmd_status)

    a = ap.parse_args(argv)
    if not getattr(a, "fn", None):
        return cmd_status()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
