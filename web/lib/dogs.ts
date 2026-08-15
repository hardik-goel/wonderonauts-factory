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
  sky: "day" | "sunset" | "night" | "plain";
  /** Drawn before the characters. */
  backdrop: string[];
  /**
   * Drawn AFTER the characters. A car dashboard has to sit in front of the dogs
   * or they look welded to the bonnet; everything else leaves this empty.
   */
  foreground?: string[];
  /** y of the dogs' paws. */
  groundY: number;
  /**
   * What the dogs wear here — the joke lands better when they are dressed for
   * the place. toolkit.dog understands: shades | helmet | beanie | rainhat |
   * partyhat.
   */
  outfit?: string;
  /** What they hold: beer | marshmallow | ball. Omitted where it would look
   *  daft, e.g. a beer inside a sealed space helmet. */
  holding?: string;
};

export const SETTINGS: Setting[] = [
  {
    id: "beach",
    label: "Beach",
    sky: "day",
    groundY: 1010,
    outfit: "shades",
    holding: "beer",
    backdrop: [
      `tk.sun(d, 1660, 180, 112, rotate=12)`,
      `tk.sea(d, 700, phase=0.4)`,
      `tk.ground(d, 880, color=(244, 220, 168), dark=(228, 200, 146), hills=False)`,
      `tk.wave(d, 320, 790, 460, 0.55)`,
    ],
  },
  {
    id: "mountains",
    label: "Mountains",
    sky: "day",
    groundY: 1010,
    outfit: "beanie",
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
    holding: "ball",
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
    outfit: "beanie",
    holding: "marshmallow",
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
    outfit: "rainhat",
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
    outfit: "helmet",
    backdrop: [
      `tk.stars(d, n=150, seed=23, area=(0, 0, 1920, 860))`,
      `tk.planet(d, 1620, 300, 150, face=False)`,
      `tk.ground(d, 890, color=(120, 122, 138), dark=(96, 98, 116))`,
    ],
  },
  // ---- interiors. These use canvas("plain") and paint their own room, since
  // an indoor scene wants a wall rather than a sky.
  {
    id: "livingroom",
    label: "Living room",
    sky: "plain",
    groundY: 1020,
    holding: "mug",
    backdrop: [
      `tk.room(d, 880, wall=(238, 226, 208), floor=(196, 162, 126))`,
      `tk.wallpaper_stripes(d, 880)`,
      `tk.framed_art(d, 1180, 300, 210, 170, motif="paw")`,
      `tk.shelf(d, 1560, 420, 340)`,
      `tk.lamp(d, 210, 880, 1.0)`,
      `tk.rug(d, 960, 1046, 1120, 120)`,
      `tk.couch(d, 960, 1010, 1080, 250)`,
    ],
  },
  {
    id: "kitchen",
    label: "Kitchen",
    sky: "plain",
    groundY: 1000,
    outfit: "chef",
    holding: "spatula",
    backdrop: [
      `tk.room(d, 820, wall=(226, 232, 224), floor=(178, 176, 170))`,
      `tk.window_view(d, 960, 330, 420, 300, mode="day")`,
      `tk.fridge(d, 250, 1010, 0.86)`,
      `tk.shelf(d, 1580, 360, 300, books=False)`,
      `tk.counter(d, 1010, 560, 1920, doors=4)`,
    ],
  },
  {
    id: "car",
    label: "Road trip",
    sky: "plain",
    groundY: 940,
    outfit: "cap",
    backdrop: [`tk.car_interior(d, 900, view="day")`],
    // the dash and wheel belong in front of the dogs, not behind them
    foreground: [`tk.car_foreground(d, 900, wheel_x=1470)`],
  },
  {
    id: "office",
    label: "Office",
    sky: "plain",
    groundY: 1010,
    holding: "mug",
    backdrop: [
      `tk.room(d, 860, wall=(224, 228, 236), floor=(150, 146, 152))`,
      // Dressing sits low and centre-right on purpose: the speech bubble owns
      // the top-left of every frame, and anything put up there is never seen.
      `tk.window_view(d, 1520, 300, 400, 280, mode="day")`,
      `tk.framed_art(d, 960, 590, 190, 150, motif="bone")`,
      `tk.shelf(d, 200, 600, 260)`,
    ],
    // The desk goes in FRONT and high enough to cut across them. Behind the
    // dogs it vanished entirely and they read as sitting on the floor of an
    // empty room; a thin strip at their paws read as skirting board.
    foreground: [
      `tk.desk(d, 950)`,
      `tk.monitor(d, 960, 950, 0.62)`,
    ],
  },
  {
    id: "snowy",
    label: "Snowy street",
    sky: "day",
    groundY: 1010,
    outfit: "beanie",
    holding: "mug",
    backdrop: [
      `tk.skyline(d, 880, seed=7, color=(140, 156, 186), lit=False)`,
      `tk.snow_ground(d, 880)`,
      `tk.snowfall(d, area=(0, 0, 1920, 1080), n=110, seed=12)`,
    ],
  },
  {
    id: "rooftop",
    label: "Rooftop",
    sky: "sunset",
    groundY: 1010,
    holding: "beer",
    backdrop: [
      `tk.skyline(d, 900, seed=3, color=(74, 66, 104), lit=True)`,
      `tk.ground(d, 900, color=(96, 92, 108), dark=(78, 74, 90), hills=False)`,
      `tk.string_lights(d, 120, sag=80, n=13)`,
    ],
  },
];

const SFX_CYCLE = ["sparkle", "pop", "whoosh", "pop", "sparkle", "whoosh"] as const;

/**
 * The cast. Two fixed characters rather than two anonymous coat colours.
 *
 * GOOFY is the golden retriever who tells the joke; WOOFY is the black-and-white
 * collie who regrets asking. They are told apart three ways on purpose — coat,
 * markings, and collar colour — because on a phone screen, at Short size, coat
 * alone is not enough. The bone tag names them on screen.
 *
 * Whatever the script calls its speakers, the first speaker is drawn as Goofy
 * and the second as Woofy: the art is the constant, the names in the dialogue
 * are not.
 */
export const CAST = [
  {
    name: "Goofy",
    breed: "golden retriever",
    coat: "(232, 178, 106)",
    collar: "(66, 126, 190)",
    markings: null as string | null,
    /** Sunny, over-eager, always has the joke. */
    persona: "teller",
  },
  {
    name: "Woofy",
    breed: "border collie",
    coat: "(58, 60, 74)",
    collar: "(206, 66, 62)",
    markings: "collie",
    /** Dry, long-suffering, sets up the punchline and regrets it. */
    persona: "straight",
  },
] as const;

const LOOKS = CAST;

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
  // Interiors. Checked after the outdoor ones so "a walk in the park" still
  // goes outside rather than being dragged indoors by a stray "sofa".
  [/\b(kitchen|cook|cooking|chef|noodle|pasta|recipe|bake|baking|dinner)\b/i, "kitchen"],
  [/\b(car|drive|driving|road ?trip|traffic|seatbelt|steering)\b/i, "car"],
  [/\b(office|work|meeting|email|boss|desk|deadline)\b/i, "office"],
  [/\b(snow|snowy|winter|cold|freezing|scarf|ice)\b/i, "snowy"],
  [/\b(roof|rooftop|city|skyline|sunset|evening)\b/i, "rooftop"],
  [/\b(couch|sofa|living ?room|tv|telly|remote|home)\b/i, "livingroom"],
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

/**
 * One `tk.dog(...)` call.
 *
 * Every scene draws the same two dogs, so building the call in one place is
 * what stops a costume from being applied to the title card and forgotten on
 * the punchline — they have to stay dressed the same all the way through.
 */
function dogCall(
  setting: Setting,
  which: 0 | 1,
  x: number,
  y: number,
  scale: number,
  opts: { speaking?: boolean; expression: string; costume?: boolean } = {
    expression: "happy",
  },
): string {
  const look = LOOKS[which];
  const dressed = opts.costume !== false;
  // tk.character picks sprite art when it exists and falls back to the vector
  // dog when it does not, so the same emitted call works either way and an
  // episode does not have to know which one it got.
  const parts = [
    `tk.character(img, d, ${py(look.name.toLowerCase())}, ${x}, ${y}, ${scale}`,
    `facing="${which === 0 ? "right" : "left"}"`,
    `coat=${look.coat}`,
    `collar=${look.collar}`,
    `name=${py(look.name)}`,
    `speaking=${opts.speaking ? "True" : "False"}`,
    `expression=${py(opts.expression)}`,
  ];
  if (look.markings) parts.push(`markings=${py(look.markings)}`);
  if (dressed && setting.outfit) {
    // Woofy wears the red frames; everything else is worn by both.
    const outfit =
      setting.outfit === "shades" && which === 1 ? "redshades" : setting.outfit;
    parts.push(`outfit=${py(outfit)}`);
  }
  if (dressed && setting.holding) parts.push(`holding=${py(setting.holding)}`);
  return parts.join(", ") + ")";
}

/** One dialogue beat: both dogs, only the speaker's muzzle open. */
function beat(
  setting: Setting,
  speakerIdx: number,
  text: string,
  expression: string,
): string[] {
  const y = setting.groundY;
  const left = dogCall(setting, 0, 470, y, 1.15, {
    speaking: speakerIdx === 0,
    expression: speakerIdx === 0 ? expression : "happy",
  });
  const right = dogCall(setting, 1, 1450, y, 1.15, {
    speaking: speakerIdx === 1,
    expression: speakerIdx === 1 ? expression : "happy",
  });
  // the bubble sits over the speaker's side so the eye goes to the right dog
  const bx = speakerIdx === 0 ? 660 : 1240;

  // Size the bubble to the line, not to the widest line anyone might ever
  // write: a fixed 980x300 balloon around "Why not?" reads as a mistake.
  const wrapped = wrap(text, 34);
  const lines = wrapped.split("\n");
  const longest = Math.max(...lines.map((l) => l.length));
  const bw = Math.min(980, Math.max(460, Math.round(longest * 30) + 170));
  const bh = Math.min(320, Math.max(190, lines.length * 76 + 110));

  return [
    `    img, d = tk.canvas("${setting.sky}")`,
    ...setting.backdrop.map((b) => `    ${b}`),
    `    ${left}`,
    `    ${right}`,
    ...(setting.foreground ?? []).map((f) => `    ${f}`),
    // The tail has to stop above whoever is speaking. 640 was the vector dog's
    // head top; sprite art stands taller, so a fixed value now lands the tail
    // dots across the speaker's face. Derive it from the character height
    // instead — see SPRITE_HEIGHT in toolkit.py.
    `    tk.thought_bubble(d, ${bx}, 330, w=${bw}, h=${bh}, tail_to=(${speakerIdx === 0 ? 520 : 1400}, ${y - Math.round(470 * 1.15) - 18}),`,
    `                      text=${py(wrapped)}, text_size=58)`,
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
      `    ${dogCall(setting, 0, 470, y, 1.15, { expression: "happy" })}`,
      `    ${dogCall(setting, 1, 1450, y, 1.15, { expression: "smug" })}`,
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
      // Undressed here on purpose: the outro is its own starry place, not the
      // episode's setting, so a space helmet or a beach beer would be stranded
      // in a scene that no longer explains it.
      `    ${dogCall(setting, 0, 350, 1030, 1.0, { expression: "laugh", speaking: true, costume: false })}`,
      `    ${dogCall(setting, 1, 780, 1030, 1.0, { expression: "smug", costume: false })}`,
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
