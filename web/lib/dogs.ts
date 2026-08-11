import type { Draft, Scene, VideoConfig } from "./types";
import { slugify } from "./slug";

/**
 * Two dogs, one dad joke, a new setting every time.
 *
 * This is a different shape of episode from the science ones: a two-hander
 * dialogue rather than a narrated explainer. Two things make it work, and both
 * are per-scene rather than per-episode:
 *
 *   voice  — each character gets its own Edge TTS voice, set per scene, so the
 *            two never blur into one narrator reading both parts.
 *   mouth  — the character with the line is drawn with an open muzzle and the
 *            other with a closed one, so it is always obvious who is speaking.
 *
 * The mouth is a per-LINE state, not phoneme lip-sync. The pipeline renders one
 * still per scene and pans it, so there is no frame-by-frame mouth to animate.
 * Real lip-sync would need a frame-sequence renderer and a forced aligner.
 */

export type DogLine = { speaker: string; text: string };

export type DogInput = {
  title?: string;
  script: string;
  setting?: string;
  /** Optional per-speaker voice override, keyed by the name in the script. */
  voices?: Record<string, string>;
};

/**
 * Deliberately contrasting voices. Two similar ones defeat the whole point of
 * giving each dog its own, so these are picked to differ in pitch and accent.
 */
export const DOG_VOICES = [
  { id: "en-US-GuyNeural", label: "Guy — warm US male" },
  { id: "en-GB-RyanNeural", label: "Ryan — bright UK male" },
  { id: "en-US-JennyNeural", label: "Jenny — friendly US female" },
  { id: "en-AU-WilliamNeural", label: "William — laid-back AU male" },
  { id: "en-GB-SoniaNeural", label: "Sonia — crisp UK female" },
  { id: "en-US-AnaNeural", label: "Ana — child" },
];

/** Each setting is a list of toolkit calls plus where the dogs stand. */
type Setting = {
  id: string;
  label: string;
  sky: "day" | "sunset" | "night";
  /** Drawn before the characters. */
  backdrop: string[];
  /** y of the dogs' paws. */
  groundY: number;
};

export const SETTINGS: Setting[] = [
  {
    id: "beach",
    label: "Beach",
    sky: "day",
    groundY: 1010,
    backdrop: [
      `tk.sun(d, 1660, 180, 112, rotate=12)`,
      `tk.sea(d, 700, phase=0.4)`,
      `tk.ground(d, 880, color=(244, 220, 168), dark=(228, 200, 146), hills=False)`,
      `tk.wave(d, 300, 700, 520, 0.7)`,
    ],
  },
  {
    id: "mountains",
    label: "Mountains",
    sky: "day",
    groundY: 1010,
    backdrop: [
      `tk.mountain(d, 300, 880, 720, 560)`,
      `tk.mountain(d, 780, 890, 520, 400)`,
      `tk.cloud(d, 1500, 240, 1.0)`,
      `tk.ground(d, 880)`,
    ],
  },
  {
    id: "park",
    label: "Park",
    sky: "day",
    groundY: 1010,
    backdrop: [
      `tk.sun(d, 250, 190, 100, rotate=18)`,
      `tk.cloud(d, 900, 230, 1.0)`,
      `tk.cloud(d, 1560, 320, 0.75)`,
      `tk.ground(d, 860)`,
    ],
  },
  {
    id: "campfire",
    label: "Night camp",
    sky: "night",
    groundY: 1010,
    backdrop: [
      `tk.stars(d, n=130, seed=11, area=(0, 0, 1920, 820))`,
      `tk.mountain(d, 1560, 900, 760, 460, color=(74, 78, 104), shade=(58, 62, 86))`,
      `tk.ground(d, 880, color=(52, 92, 88), dark=(40, 74, 72))`,
    ],
  },
  {
    id: "rainy",
    label: "Rainy day",
    sky: "day",
    groundY: 1010,
    backdrop: [
      `tk.cloud(d, 700, 220, 1.8, color=(186, 198, 216))`,
      `tk.cloud(d, 1400, 280, 1.4, color=(196, 206, 222))`,
      `tk.rainfall(d, (200, 340, 1720, 840), n=44, seed=6, size=(16, 26))`,
      `tk.ground(d, 880)`,
      `tk.puddle(d, 960, 1020, 320, 60)`,
    ],
  },
  {
    id: "space",
    label: "Moon",
    sky: "night",
    groundY: 1010,
    backdrop: [
      `tk.stars(d, n=150, seed=23, area=(0, 0, 1920, 860))`,
      `tk.planet(d, 1620, 300, 150, face=False)`,
      `tk.ground(d, 890, color=(120, 122, 138), dark=(96, 98, 116))`,
    ],
  },
];

const SFX_CYCLE = ["sparkle", "pop", "whoosh", "pop", "sparkle", "whoosh"] as const;

/** Two coats that never blur together, plus matching collars. */
const LOOKS = [
  { coat: "(216, 170, 110)", collar: "(224, 86, 86)" },
  { coat: "(122, 134, 152)", collar: "(86, 184, 224)" },
];

function py(s: string): string {
  return JSON.stringify(String(s));
}

function hash(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (Math.imul(31, h) + s.charCodeAt(i)) | 0;
  return h;
}

/**
 * Parse "Name: line" dialogue. Continuation lines belong to the previous
 * speaker, so a joke can wrap without becoming its own scene.
 */
export function parseDialogue(raw: string): { title: string; lines: DogLine[] } {
  const text = (raw ?? "").replace(/\r\n?/g, "\n").trim();
  let title = "";
  const lines: DogLine[] = [];

  for (const rawLine of text.split("\n")) {
    const line = rawLine.replace(/^[\s>*-]+/, "").replace(/\*\*/g, "").trim();
    if (!line) continue;

    const titleMatch = line.match(/^title\s*[:\-—]\s*(.+)$/i);
    if (titleMatch) {
      title = titleMatch[1].trim();
      continue;
    }

    // "Rex: ..." — a speaker label is short and has no sentence punctuation
    const m = line.match(/^([A-Za-z][\w '.-]{0,24})\s*[:\-—]\s*(.+)$/);
    if (m && m[1].split(/\s+/).length <= 3) {
      lines.push({ speaker: m[1].trim(), text: m[2].trim() });
    } else if (lines.length) {
      lines[lines.length - 1].text += " " + line;
    }
  }
  return { title, lines };
}

export function speakersOf(lines: DogLine[]): string[] {
  const seen: string[] = [];
  for (const l of lines) {
    const key = l.speaker.toLowerCase();
    if (!seen.some((s) => s.toLowerCase() === key)) seen.push(l.speaker);
  }
  return seen;
}

/** Words that clearly mean a particular setting, so "Beach Day" is not set on the moon. */
const SETTING_HINTS: [RegExp, string][] = [
  [/\b(beach|sea|shore|sand|ocean|surf|crab)\b/i, "beach"],
  [/\b(mountain|hike|hiking|summit|peak|climb)\b/i, "mountains"],
  [/\b(camp|campfire|tent|night|star|stars)\b/i, "campfire"],
  [/\b(rain|rainy|puddle|storm|umbrella|wet)\b/i, "rainy"],
  [/\b(space|moon|rocket|planet|astronaut)\b/i, "space"],
  [/\b(park|picnic|garden|walk)\b/i, "park"],
];

function hintedSetting(text: string): Setting | undefined {
  if (!text.trim()) return undefined;
  for (const [re, id] of SETTING_HINTS) {
    if (re.test(text)) return SETTINGS.find((s) => s.id === id);
  }
  return undefined;
}

/**
 * The title wins over the dialogue, and both win over the shuffle. A joke about
 * crabs inside "Mountain Hike Havoc" should not drag the scene to the beach,
 * and picking the moon for "Beach Day Bonanza" is technically "a different
 * setting every time" and still wrong.
 */
function pickSetting(seed: string, requested?: string, title = "", body = ""): Setting {
  if (requested) {
    const found = SETTINGS.find((s) => s.id === requested);
    if (found) return found;
  }
  return (
    hintedSetting(title) ??
    hintedSetting(body) ??
    SETTINGS[Math.abs(hash(seed)) % SETTINGS.length]
  );
}

/** One dialogue beat: both dogs, only the speaker's muzzle open. */
function beat(
  setting: Setting,
  speakerIdx: number,
  text: string,
  expression: string,
): string[] {
  const y = setting.groundY;
  const left = `tk.dog(d, 470, ${y}, 1.15, facing="right", coat=${LOOKS[0].coat}, collar=${LOOKS[0].collar}, speaking=${speakerIdx === 0 ? "True" : "False"}, expression=${py(speakerIdx === 0 ? expression : "happy")})`;
  const right = `tk.dog(d, 1450, ${y}, 1.15, facing="left", coat=${LOOKS[1].coat}, collar=${LOOKS[1].collar}, speaking=${speakerIdx === 1 ? "True" : "False"}, expression=${py(speakerIdx === 1 ? expression : "happy")})`;
  // the bubble sits over the speaker's side so the eye goes to the right dog
  const bx = speakerIdx === 0 ? 660 : 1240;
  return [
    `    img, d = tk.canvas("${setting.sky}")`,
    ...setting.backdrop.map((b) => `    ${b}`),
    `    ${left}`,
    `    ${right}`,
    `    tk.thought_bubble(d, ${bx}, 330, w=980, h=300, tail_to=(${speakerIdx === 0 ? 520 : 1400}, 640),`,
    `                      text=${py(wrap(text, 34))}, text_size=58)`,
  ];
}

/** Wrap to roughly `per` characters a line so the bubble never overflows. */
function wrap(text: string, per: number): string {
  const words = text.split(/\s+/);
  const out: string[] = [];
  let line = "";
  for (const w of words) {
    if (line && (line + " " + w).length > per) {
      out.push(line);
      line = w;
    } else {
      line = line ? line + " " + w : w;
    }
  }
  if (line) out.push(line);
  return out.slice(0, 4).join("\n");
}

export function buildDogRenderScenes(
  title: string,
  lines: DogLine[],
  speakers: string[],
  setting: Setting,
): string {
  const y = setting.groundY;
  const bodies: string[] = [];

  // title card
  bodies.push(
    [
      `def scene_01():`,
      `    img, d = tk.canvas("${setting.sky}")`,
      ...setting.backdrop.map((b) => `    ${b}`),
      `    tk.dog(d, 470, ${y}, 1.15, facing="right", coat=${LOOKS[0].coat}, collar=${LOOKS[0].collar}, expression="happy")`,
      `    tk.dog(d, 1450, ${y}, 1.15, facing="left", coat=${LOOKS[1].coat}, collar=${LOOKS[1].collar}, expression="smug")`,
      `    tk.title_text(d, (960, 190), ${py(wrap(title, 22))}, 116, fill=P["white"], stroke=16)`,
      `    tk.speech_pop(d, 960, 430, ${py(`${speakers[0]} & ${speakers[1] ?? speakers[0]}`)}, 56, fill=P["accent"])`,
      `    return tk.vignette(img)`,
    ].join("\n"),
  );

  // one scene per line; the last line of the joke gets the laugh
  lines.forEach((l, i) => {
    const idx = speakers.findIndex((s) => s.toLowerCase() === l.speaker.toLowerCase());
    const isPunchline = i === lines.length - 1 || /[!]$/.test(l.text);
    bodies.push(
      [
        `def scene_${String(i + 2).padStart(2, "0")}():`,
        ...beat(setting, Math.max(0, idx), l.text, isPunchline ? "laugh" : "happy"),
        `    return tk.vignette(img)`,
      ].join("\n"),
    );
  });

  // outro — end-card zone must stay clear
  const last = lines.length + 2;
  bodies.push(
    [
      `def scene_${String(last).padStart(2, "0")}():`,
      `    img, d = tk.canvas("night")`,
      `    tk.stars(d, n=120, seed=31, area=(0, 0, 1920, 880))`,
      `    zones = tk.end_screen_guides(d)`,
      `    tk.ground(d, 980, color=(46, 96, 92), dark=(34, 78, 78))`,
      // Both dogs sign off together, sitting low-left. Every line of text is
      // stacked above them and left of the end-card zone, so nothing lands on a
      // face and nothing lands under YouTube's subscribe card.
      `    tk.dog(d, 350, 1030, 1.0, facing="right", coat=${LOOKS[0].coat}, collar=${LOOKS[0].collar}, expression="laugh", speaking=True)`,
      `    tk.dog(d, 780, 1030, 1.0, facing="left", coat=${LOOKS[1].coat}, collar=${LOOKS[1].collar}, expression="smug")`,
      `    tk.title_text(d, (860, 150), "Same time tomorrow?", 88, fill=P["accent"], stroke=14)`,
      `    tk.title_text(d, (860, 320), "More dad jokes every week", 54, fill=P["white"], stroke=11)`,
      `    tk.speech_pop(d, 700, 470, "LIKE + SUBSCRIBE", 58, fill=P["rocket_red"], text_fill=P["white"])`,
      `    tk.title_text(d, (700, 620), "Got a worse one? Comments!", 46, fill=P["white"], stroke=10)`,
      `    assert not tk.safe_zone_violations(zones["end_cards"]), \\`,
      `        tk.safe_zone_violations(zones["end_cards"])`,
      `    return tk.vignette(img)`,
    ].join("\n"),
  );

  const names = bodies.map((_, i) => `scene_${String(i + 1).padStart(2, "0")}`);

  return `#!/usr/bin/env python3
"""${title.replace(/"/g, "'")} -- a two-dog dad joke, set at the ${setting.label.toLowerCase()}.

Generated by Wonder-o-nauts Studio. Only the dog with the current line is drawn
with an open muzzle, so it is always clear who is speaking.
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


${bodies.join("\n\n\n")}


SCENES = [${names.join(", ")}]


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

export function buildDogEpisode(input: DogInput): Draft & { setting: string } {
  const parsed = parseDialogue(input.script);
  const lines = parsed.lines;
  if (lines.length < 2) throw new Error("Need at least two lines of dialogue.");

  const speakers = speakersOf(lines);
  const title = (input.title || parsed.title || `${speakers.join(" & ")}: Dad Jokes`).trim();
  const setting = pickSetting(title + input.script.slice(0, 40), input.setting, title, input.script);

  // Distinct voice per speaker. This is what keeps the two from intermingling.
  const voiceFor: Record<string, string> = {};
  speakers.forEach((s, i) => {
    voiceFor[s.toLowerCase()] =
      input.voices?.[s] ?? DOG_VOICES[i % DOG_VOICES.length].id;
  });

  const scenes: Scene[] = [];
  // title card: narrated by speaker one
  scenes.push({
    image: "frames/scene_01.png",
    chapter: "Meet the dogs",
    sfx: "sparkle",
    narration: `${title}. Two good dogs, one terrible joke.`,
    voice: voiceFor[speakers[0].toLowerCase()],
  } as Scene);

  lines.forEach((l, i) => {
    scenes.push({
      image: `frames/scene_${String(i + 2).padStart(2, "0")}.png`,
      chapter: `${l.speaker}`,
      sfx: SFX_CYCLE[i % SFX_CYCLE.length],
      narration: l.text,
      voice: voiceFor[l.speaker.toLowerCase()] ?? DOG_VOICES[0].id,
    } as Scene);
  });

  const lastIdx = lines.length + 2;
  scenes.push({
    image: `frames/scene_${String(lastIdx).padStart(2, "0")}.png`,
    chapter: "Same time tomorrow?",
    sfx: "success",
    narration:
      "That is all the jokes our brains can hold. Got a worse one? Put it in the comments, and we will read the best out next time.",
    voice: voiceFor[speakers[0].toLowerCase()],
  } as Scene);

  // the Short wants the setup and the punchline, not the title card
  const punch = lines.length + 1;
  const shorts = Array.from(
    new Set([Math.max(2, punch - 2), Math.max(2, punch - 1), punch]),
  ).filter((n) => n >= 1 && n <= scenes.length);

  const videoJson: VideoConfig = {
    title,
    // Tells factory.py to lint this against dialogue word bounds: "Why not?" is
    // a whole beat here, not a scene that forgot its narration.
    format: "dialogue",
    voice: DOG_VOICES[0].id,
    rate: "+0%",
    description:
      `${title}\n\nTwo dogs. One dad joke. Today at the ${setting.label.toLowerCase()}.\n\n` +
      `Got a worse one? Put it in the comments.\n\n#dadjokes #dogs #cartoon #funny`,
    tags: `dad jokes, talking dogs, cartoon dogs, funny animals, ${setting.id}, kids comedy`,
    thumbnail_text: `DAD JOKES\nAT THE ${setting.label.toUpperCase()}`,
    thumbnail_prop: "kid",
    thumbnail_bg: setting.id === "beach" ? "sea" : setting.sky === "night" ? "none" : "land",
    music: true,
    music_seed: (Math.abs(hash(title)) % 97) + 1,
    bgm_vol: 0.1,
    shorts_scenes: shorts.length ? shorts : [2],
    scenes,
  };

  return {
    slug: slugify(title),
    title,
    videoJson,
    renderScenes: buildDogRenderScenes(title, lines, speakers, setting),
    source: { kind: "topic", label: title, transcriptChars: 0 },
    setting: setting.label,
  };
}
