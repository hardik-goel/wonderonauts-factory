import Anthropic from "@anthropic-ai/sdk";
import { TOOLKIT_REFERENCE } from "./toolkit-reference";
import type { Draft, VideoConfig } from "./types";
import type { Research } from "./youtube";

const anthropic = new Anthropic();

const MODEL = "claude-opus-5";

const SYSTEM = `You write episodes of "Wonder-o-nauts", a YouTube science channel for
children aged 4-9. You produce exactly two artifacts: a video.json config and a
render_scenes.py that draws the episode's ten frames.

EDITORIAL RULES (learned across five produced episodes)
- 10 scenes. 35-55 words of narration each. That lands at 3.5-4.5 minutes, the
  sweet spot for this age band. Under 20 or over 80 words fails validation.
- Speak to a curious six-year-old: short sentences, one idea per sentence.
- At most two "secrets" (the real mechanism), plus one bonus wonder near the end
  -- the bit a child repeats to a grown-up.
- Name the common misconception explicitly and kill it. Children deserve the
  real explanation, not the popular wrong one.
- Draw the physics, not a picture of it. A diagram that is decorative but wrong
  teaches the wrong thing even when the narration is right.
- Every scene needs a short \`chapter\` label and an \`sfx\`.
- End the last scene with a question to the comments.
- Any hands-on experiment must be safe unsupervised: no sun-staring, nothing
  hot, sharp, electrical, or edible-in-quantity.
- Never state a fact you are not confident is true. Where scientists genuinely
  disagree, say so -- that is a feature of the channel, not a flaw.

SCENE ART RULES
- render_scenes.py may ONLY use engine/toolkit.py primitives, listed below.
  Inventing a primitive, importing PIL directly, or drawing with raw d.ellipse
  calls is a failure. Compose what you need from what exists.
- Keep every text element inside tk.SAFE (120, 80) - (1800, 1000). The Ken Burns
  zoom crops roughly 4% off each edge over a scene.
- Scene 10 is the outro: it must call tk.end_screen_guides(d) and leave the
  bottom-right 40% of the frame visually empty for YouTube's end cards, then
  assert tk.safe_zone_violations(zones["end_cards"]) is empty.
- Vary the compositions. Ten frames with the same layout is a boring episode.
- Place objects consistently with their coordinate contract: kid() and
  mountain() take the position of their FEET; sea() and ground() fill
  everything below y.

${TOOLKIT_REFERENCE}

render_scenes.py MUST have exactly this shape:

#!/usr/bin/env python3
"""Episode -- "<Title>"."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from engine import toolkit as tk  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FRAMES = os.path.join(HERE, "frames")
P = tk.PALETTE


def out(n):
    return os.path.join(FRAMES, f"scene_{n:02d}.png")


def scene_01():
    img, d = tk.canvas("day")
    ...
    return tk.vignette(img)

... scene_02 through scene_10 ...

SCENES = [scene_01, scene_02, scene_03, scene_04, scene_05,
          scene_06, scene_07, scene_08, scene_09, scene_10]


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
                         os.path.join(FRAMES, "contact_sheet.jpg"))`;

const SCENE_SCHEMA = {
  type: "object",
  properties: {
    image: { type: "string", description: "frames/scene_NN.png" },
    chapter: { type: "string", description: "Short chapter label, 2-4 words" },
    sfx: { type: "string", enum: ["whoosh", "pop", "sparkle", "success"] },
    narration: { type: "string", description: "35-55 words spoken to a 6-year-old" },
  },
  required: ["image", "chapter", "sfx", "narration"],
  additionalProperties: false,
} as const;

const DRAFT_SCHEMA = {
  type: "object",
  properties: {
    slug: {
      type: "string",
      description: "kebab-case folder name, e.g. how-do-magnets-work",
    },
    video_json: {
      type: "object",
      properties: {
        title: { type: "string" },
        voice: { type: "string" },
        rate: { type: "string" },
        description: { type: "string" },
        tags: { type: "string" },
        thumbnail_text: { type: "string", description: "Exactly two lines separated by \\n" },
        thumbnail_prop: {
          type: "string",
          enum: [
            "rocket", "plane", "paper_plane", "sun", "molecule", "planet",
            "raindrop", "prism", "cloud", "airfoil", "kid", "salt_crystal",
            "wave", "mountain",
          ],
        },
        thumbnail_bg: { type: "string", enum: ["land", "sea", "none"] },
        music: { type: "boolean" },
        music_seed: { type: "integer" },
        bgm_vol: { type: "number" },
        shorts_scenes: {
          type: "array",
          items: { type: "integer" },
          description: "Exactly 3 distinct scene numbers that stand alone",
        },
        scenes: { type: "array", items: SCENE_SCHEMA },
      },
      required: [
        "title", "voice", "rate", "description", "tags", "thumbnail_text",
        "thumbnail_prop", "thumbnail_bg", "music", "music_seed", "bgm_vol",
        "shorts_scenes", "scenes",
      ],
      additionalProperties: false,
    },
    render_scenes_py: {
      type: "string",
      description: "Complete Python source for render_scenes.py",
    },
  },
  required: ["slug", "video_json", "render_scenes_py"],
  additionalProperties: false,
} as const;

function buildPrompt(topic: string, research: Research, seedHint: number): string {
  const parts: string[] = [];
  parts.push(`Write a Wonder-o-nauts episode answering: "${topic}"`);

  if (research.kind === "youtube") {
    parts.push(
      `\nThe user supplied a YouTube video as research: "${research.label}".`,
    );
    if (research.transcript) {
      parts.push(
        `Its transcript is below. Use it ONLY to understand the subject and to` +
          ` notice what a general audience finds confusing. Write an entirely` +
          ` original script in the channel's own voice -- do not reuse its` +
          ` structure, phrasing, examples, or jokes. Correct anything in it you` +
          ` know to be wrong rather than repeating it.\n\n<transcript>\n${research.transcript}\n</transcript>`,
      );
    } else {
      parts.push(
        `Its transcript could not be retrieved, so work from the title and your` +
          ` own knowledge of the subject.`,
      );
    }
  }

  parts.push(
    `\nUse music_seed ${seedHint}. Set voice "en-US-AnaNeural" and rate "+0%".` +
      ` Set music true and bgm_vol 0.13. Image paths are frames/scene_01.png` +
      ` through frames/scene_10.png in order. Pick thumbnail_prop and` +
      ` thumbnail_bg that actually match the subject.`,
  );

  return parts.join("\n");
}

export async function writeEpisode(
  topic: string,
  research: Research,
): Promise<Draft> {
  // Deterministic-ish seed so two episodes rarely collide on the music bed.
  const seedHint = (Math.abs(hash(topic)) % 97) + 1;

  const stream = anthropic.messages.stream({
    model: MODEL,
    max_tokens: 32000,
    system: SYSTEM,
    output_config: {
      effort: "high",
      format: { type: "json_schema", schema: DRAFT_SCHEMA },
    },
    messages: [{ role: "user", content: buildPrompt(topic, research, seedHint) }],
  } as Anthropic.MessageStreamParams);

  const message = await stream.finalMessage();

  if (message.stop_reason === "refusal") {
    throw new Error(
      "The script writer declined this topic. Try rephrasing, or pick a different subject.",
    );
  }
  if (message.stop_reason === "max_tokens") {
    throw new Error(
      "The script came back truncated. Try again, or simplify the topic.",
    );
  }

  const text = message.content.find((b) => b.type === "text");
  if (!text || text.type !== "text") throw new Error("No script returned.");

  let parsed: { slug: string; video_json: VideoConfig; render_scenes_py: string };
  try {
    parsed = JSON.parse(text.text);
  } catch {
    throw new Error("The script writer returned malformed JSON.");
  }

  return {
    slug: slugify(parsed.slug || topic),
    videoJson: parsed.video_json,
    renderScenes: parsed.render_scenes_py,
    source: {
      kind: research.kind,
      label: research.label,
      transcriptChars: research.transcript.length,
    },
  };
}

export function slugify(s: string): string {
  return (
    s
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .replace(/-{2,}/g, "-")
      .slice(0, 60) || "new-episode"
  );
}

function hash(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (Math.imul(31, h) + s.charCodeAt(i)) | 0;
  return h;
}
