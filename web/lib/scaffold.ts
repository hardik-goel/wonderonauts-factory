import type { Draft, Scene, VideoConfig } from "./types";
import { slugify } from "./slug";

/**
 * The keyless authoring path.
 *
 * The factory's whole promise is "no API keys, no accounts". Script generation
 * is the one step that needs either an LLM or a human, so when there is no
 * Anthropic key the human supplies the words and this module supplies
 * everything else: a valid video.json and a render_scenes.py built from real
 * toolkit primitives.
 *
 * The art it emits is deliberately simple and template-driven rather than
 * bespoke. It is a watchable episode, not a designed one -- the point is that
 * someone with no key and no Python can still ship, and can hand-edit the
 * generated render_scenes.py afterwards if they want more.
 */

export type ScaffoldInput = {
  title: string;
  /** One entry per scene: a short on-screen label plus the narration. */
  scenes: { chapter: string; narration: string }[];
  /** Hero object, must be one of engine/thumbnail.py PROPS. */
  prop: string;
  /** Scene backdrop family. */
  look: "land" | "sea" | "space";
  description?: string;
  tags?: string;
};

const SFX_CYCLE = [
  "sparkle", "pop", "whoosh", "whoosh", "whoosh",
  "pop", "whoosh", "sparkle", "whoosh", "success",
] as const;

/** Props the generated Python is allowed to draw, mapped to a safe call. */
const PROP_CALL: Record<string, (x: number, y: number, s: number) => string> = {
  rocket: (x, y, s) => `tk.rocket(d, ${x}, ${y}, ${s}, face=True)`,
  plane: (x, y, s) => `tk.plane(d, ${x}, ${y}, ${(s * 0.7).toFixed(2)})`,
  paper_plane: (x, y, s) => `tk.paper_plane(d, ${x}, ${y}, ${(s * 1.5).toFixed(2)})`,
  sun: (x, y, s) => `tk.sun(d, ${x}, ${y}, ${Math.round(150 * s)})`,
  molecule: (x, y, s) => `tk.molecule(d, ${x}, ${y}, ${Math.round(130 * s)})`,
  planet: (x, y, s) => `tk.planet(d, ${x}, ${y}, ${Math.round(160 * s)}, face=True)`,
  raindrop: (x, y, s) => `tk.raindrop(d, ${x}, ${y}, ${Math.round(150 * s)})`,
  prism: (x, y, s) => `tk.prism(d, ${x}, ${y}, ${Math.round(280 * s)})`,
  cloud: (x, y, s) => `tk.cloud(d, ${x}, ${y}, ${(1.3 * s).toFixed(2)})`,
  airfoil: (x, y, s) => `tk.airfoil(d, ${x}, ${y}, ${(1.1 * s).toFixed(2)})`,
  kid: (x, y, s) => `tk.kid(d, ${x}, ${y + 160}, ${(1.1 * s).toFixed(2)}, arms="one_up", mouth="o")`,
  salt_crystal: (x, y, s) => `tk.salt_crystal(d, ${x}, ${y}, ${Math.round(200 * s)})`,
  wave: (x, y, s) => `tk.wave(d, ${x}, ${y}, ${Math.round(560 * s)})`,
  mountain: (x, y, s) => `tk.mountain(d, ${x}, ${y + 180}, ${Math.round(520 * s)}, ${Math.round(420 * s)})`,
};

export const PROPS = Object.keys(PROP_CALL);
export const LOOKS = ["land", "sea", "space"] as const;

/** Python string literal — the chapter text is user input. */
function py(s: string): string {
  return JSON.stringify(String(s));
}

function backdrop(look: ScaffoldInput["look"], y: number): { sky: string; floor: string } {
  if (look === "sea") return { sky: "day", floor: `tk.sea(d, ${y})` };
  if (look === "space") return { sky: "night", floor: `tk.stars(d, n=110, seed=17)` };
  return { sky: "day", floor: `tk.ground(d, ${y})` };
}

/**
 * Body of one scene function. Layouts rotate so ten frames don't look
 * identical; every text element sits inside tk.SAFE.
 */
function sceneBody(i: number, total: number, input: Prepared): string {
  const chapter = py(input.chapter(i));
  const drawProp = PROP_CALL[input.prop] ?? PROP_CALL.rocket;

  if (i === 0) {
    const { sky, floor } = backdrop(input.look, 860);
    return [
      `    img, d = tk.canvas("${sky}")`,
      `    tk.sun(d, 1660, 175, 118, rotate=12)`,
      `    tk.cloud(d, 1300, 350, 0.85)`,
      `    ${floor}`,
      `    ${drawProp(1480, 640, 1.5)}`,
      `    tk.title_text(d, (700, 150), "WONDER-O-NAUTS", 74, fill=P["accent"], stroke=11)`,
      `    tk.title_text(d, (680, 440), ${py(wrapTitle(input.title))}, 120, fill=P["white"], stroke=16)`,
      `    tk.speech_pop(d, 580, 720, "Science for kids!", 54, fill=P["white"])`,
    ].join("\n");
  }

  if (i === total - 1) {
    // Outro: bottom-right 40% must stay clear for YouTube end cards. The last
    // chapter is usually "Mission complete!" too, so don't print it twice.
    const recap = input.chapter(i).toLowerCase().includes("mission complete")
      ? py("Thanks for exploring\nwith us today!")
      : chapter;
    return [
      `    img, d = tk.canvas("night")`,
      `    tk.stars(d, n=120, seed=21, area=(0, 0, 1920, 880))`,
      `    zones = tk.end_screen_guides(d)`,
      `    tk.ground(d, 960, color=(46, 96, 92), dark=(34, 78, 78))`,
      `    tk.rocket(d, 280, 520, scale=1.35, face=True)`,
      `    tk.title_text(d, (1060, 160), "Mission complete!", 100, fill=P["accent"], stroke=15)`,
      `    tk.title_text(d, (1010, 370), ${recap}, 60, fill=P["white"], stroke=11)`,
      `    tk.speech_pop(d, 780, 600, "LIKE + SUBSCRIBE", 58, fill=P["rocket_red"], text_fill=P["white"])`,
      `    tk.title_text(d, (640, 800), "What should we explore next?", 48, fill=P["white"], stroke=10)`,
      `    assert not tk.safe_zone_violations(zones["end_cards"]), \\`,
      `        tk.safe_zone_violations(zones["end_cards"])`,
    ].join("\n");
  }

  // Middle scenes rotate through four compositions. Each one has to fill the
  // frame: a lone small prop on an empty field reads as an unfinished slide.
  const layout = (i - 1) % 4;
  const { sky, floor } = backdrop(input.look, 900);

  if (layout === 0) {
    return [
      `    img, d = tk.canvas("${sky}")`,
      `    tk.cloud(d, 1560, 220, 0.9)`,
      `    ${floor}`,
      `    tk.kid(d, 400, 1010, scale=1.25, arms="down", mouth="o", looking="up")`,
      `    tk.thought_bubble(d, 1150, 400, w=1020, h=400, tail_to=(680, 660),`,
      `                      text=${chapter}, text_size=76)`,
    ].join("\n");
  }
  if (layout === 1) {
    return [
      `    img, d = tk.canvas("${sky}")`,
      `    tk.sun(d, 250, 200, 104, rotate=20)`,
      `    tk.cloud(d, 700, 260, 0.7)`,
      `    ${floor}`,
      `    ${drawProp(1330, 600, 1.9)}`,
      `    tk.title_text(d, (620, 340), ${chapter}, 92, fill=P["white"], stroke=14)`,
    ].join("\n");
  }
  if (layout === 2) {
    return [
      `    img, d = tk.canvas("${sky}")`,
      `    tk.cloud(d, 320, 230, 0.8)`,
      `    tk.cloud(d, 1620, 300, 0.7)`,
      `    ${floor}`,
      `    ${drawProp(430, 600, 1.25)}`,
      `    ${drawProp(960, 540, 1.5)}`,
      `    ${drawProp(1490, 600, 1.25)}`,
      `    tk.caption(d, ${chapter}, 56, y=950)`,
    ].join("\n");
  }
  return [
    `    img, d = tk.canvas("${sky}")`,
    `    tk.cloud(d, 1500, 240, 1.05)`,
    `    ${floor}`,
    `    ${drawProp(1340, 620, 1.8)}`,
    `    tk.speech_pop(d, 620, 330, ${chapter}, 70, fill=P["accent"])`,
    `    tk.kid(d, 400, 1020, scale=1.0, arms="point_up", mouth="smile")`,
  ].join("\n");
}

/** Break a long title across two lines so it fits the frame. */
function wrapTitle(title: string): string {
  const words = title.trim().split(/\s+/);
  if (words.length < 4) return title.trim();
  const mid = Math.ceil(words.length / 2);
  return words.slice(0, mid).join(" ") + "\n" + words.slice(mid).join(" ");
}

/**
 * thumbnail_text must be EXACTLY two non-empty lines -- line 2 becomes the big
 * word on variant B, and --validate rejects anything else. A short title wraps
 * to one line, so split it deliberately rather than hoping.
 */
function thumbnailText(title: string): string {
  const clean = title.trim().replace(/[?!.]+$/, "").toUpperCase();
  const words = clean.split(/\s+/);
  if (words.length === 1) return `WONDER-O-NAUTS\n${words[0]}`;
  const mid = Math.max(1, Math.ceil(words.length / 2));
  return `${words.slice(0, mid).join(" ")}\n${words.slice(mid).join(" ")}`;
}

type Prepared = ScaffoldInput & { chapter: (i: number) => string };

export function buildRenderScenes(raw: ScaffoldInput): string {
  const total = raw.scenes.length;
  const input: Prepared = {
    ...raw,
    chapter: (i) => raw.scenes[i]?.chapter || `Scene ${i + 1}`,
  };

  const fns = input.scenes
    .map((_, i) => `def scene_${String(i + 1).padStart(2, "0")}():\n${sceneBody(i, total, input)}\n    return tk.vignette(img)`)
    .join("\n\n\n");

  const list = input.scenes
    .map((_, i) => `scene_${String(i + 1).padStart(2, "0")}`)
    .join(", ");

  return `#!/usr/bin/env python3
"""${raw.title.replace(/"/g, "'")}

Generated by Wonder-o-nauts Studio without an API key. Every frame is composed
from engine/toolkit.py primitives -- edit this file directly to art-direct it.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from engine import toolkit as tk  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FRAMES = os.path.join(HERE, "frames")

P = tk.PALETTE


def out(n):
    return os.path.join(FRAMES, f"scene_{n:02d}.png")


${fns}


SCENES = [${list}]


def render(only=None):
    os.makedirs(FRAMES, exist_ok=True)
    for i, fn in enumerate(SCENES, 1):
        if only and i not in only:
            continue
        print(f"  scene {i:02d} -> {os.path.relpath(tk.save(fn(), out(i)), HERE)}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--sheet"]
    render({int(a) for a in args} if args else None)
    if "--sheet" in sys.argv[1:]:
        tk.contact_sheet([out(i) for i in range(1, len(SCENES) + 1)],
                         os.path.join(FRAMES, "contact_sheet.jpg"))
`;
}

export function buildVideoJson(input: ScaffoldInput): VideoConfig {
  const n = input.scenes.length;
  const scenes: Scene[] = input.scenes.map((s, i) => ({
    image: `frames/scene_${String(i + 1).padStart(2, "0")}.png`,
    chapter: s.chapter || `Scene ${i + 1}`,
    sfx: SFX_CYCLE[i % SFX_CYCLE.length],
    narration: s.narration,
  }));

  // Three distinct, in-range scenes that stand alone.
  const shorts = Array.from(new Set([2, Math.min(6, n), Math.min(8, n)]))
    .filter((i) => i >= 1 && i <= n)
    .slice(0, 3);

  return {
    title: input.title,
    voice: "en-US-AnaNeural",
    rate: "+0%",
    description:
      input.description?.trim() ||
      `${input.title}\n\nBlast off with the Wonder-o-nauts and find out!\n\n` +
        `What should we explore next? Tell us in the comments!\n\n` +
        `#kidsscience #stemforkids #wonderonauts #scienceforkids`,
    tags:
      input.tags?.trim() ||
      `kids science, science for kids, STEM for kids, educational video for children, wonder-o-nauts`,
    thumbnail_text: thumbnailText(input.title),
    thumbnail_prop: input.prop,
    thumbnail_bg: input.look === "sea" ? "sea" : input.look === "space" ? "none" : "land",
    music: true,
    music_seed: (Math.abs(hash(input.title)) % 97) + 1,
    bgm_vol: 0.13,
    shorts_scenes: shorts.length ? shorts : [1],
    scenes,
  };
}

export function buildDraft(input: ScaffoldInput): Draft {
  return {
    slug: slugify(input.title),
    videoJson: buildVideoJson(input),
    renderScenes: buildRenderScenes(input),
    source: { kind: "topic", label: input.title, transcriptChars: 0 },
  };
}

function hash(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (Math.imul(31, h) + s.charCodeAt(i)) | 0;
  return h;
}
