/**
 * Verify the dad-joke generator: dialogue parses, each speaker keeps its own
 * voice, and every setting renders through the real toolkit.
 *
 *   pnpm exec tsx scripts/verify-dogs.ts
 */
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { buildDogEpisode, parseDialogue, speakersOf, SETTINGS } from "../lib/dogs";

const ROOT = path.resolve(import.meta.dirname, "../..");
const PROJECT = path.join(ROOT, "projects", "_dogcheck");
const PY = fs.existsSync(path.join(ROOT, ".venv/bin/python"))
  ? path.join(ROOT, ".venv/bin/python")
  : "python3";

const SCRIPT = `Title: Beach Day Bonanza
Rex: Hey Bo, why don't crabs ever share their snacks?
Bo: I don't know Rex, why not?
Rex: Because they're shellfish!
Bo: That was terrible. Do another one.`;

let fails = 0;
const ok = (label: string, cond: boolean, detail = "") => {
  if (!cond) fails++;
  console.log(`  ${cond ? "PASS" : "FAIL"}  ${label}${detail ? `  ${detail}` : ""}`);
};

const parsed = parseDialogue(SCRIPT);
ok("title parsed", parsed.title === "Beach Day Bonanza", parsed.title);
ok("4 lines", parsed.lines.length === 4, String(parsed.lines.length));
ok("two speakers", speakersOf(parsed.lines).join(",") === "Rex,Bo", speakersOf(parsed.lines).join(","));

const ep = buildDogEpisode({ script: SCRIPT });
const voices = ep.videoJson.scenes.map((s) => s.voice);
const rexVoices = new Set(ep.videoJson.scenes.filter((s) => s.chapter === "Rex").map((s) => s.voice));
const boVoices = new Set(ep.videoJson.scenes.filter((s) => s.chapter === "Bo").map((s) => s.voice));
ok("every scene has a voice", voices.every(Boolean));
ok("Rex uses exactly one voice", rexVoices.size === 1, [...rexVoices].join(","));
ok("Bo uses exactly one voice", boVoices.size === 1, [...boVoices].join(","));
ok("the two dogs never share a voice",
   [...rexVoices][0] !== [...boVoices][0], `${[...rexVoices][0]} vs ${[...boVoices][0]}`);
ok("scene count = title + lines + outro",
   ep.videoJson.scenes.length === parsed.lines.length + 2, String(ep.videoJson.scenes.length));

// every setting must render — the user gets a different one each time
for (const setting of SETTINGS) {
  const e = buildDogEpisode({ script: SCRIPT, setting: setting.id });
  fs.rmSync(PROJECT, { recursive: true, force: true });
  fs.mkdirSync(path.join(PROJECT, "frames"), { recursive: true });
  fs.writeFileSync(path.join(PROJECT, "render_scenes.py"), e.renderScenes);
  fs.writeFileSync(path.join(PROJECT, "video.json"), JSON.stringify(e.videoJson, null, 2) + "\n");
  try {
    execFileSync(PY, [path.join(PROJECT, "render_scenes.py")], { cwd: ROOT, stdio: ["ignore", "pipe", "pipe"] });
    const n = fs.readdirSync(path.join(PROJECT, "frames")).filter((f) => f.endsWith(".png")).length;
    if (n !== e.videoJson.scenes.length) throw new Error(`${n}/${e.videoJson.scenes.length} frames`);
    ok(`setting ${setting.id} renders`, true, `${n} frames`);
  } catch (err) {
    ok(`setting ${setting.id} renders`, false,
       (err instanceof Error ? err.message : String(err)).split("\n").slice(-3).join(" | "));
  }
}

fs.rmSync(PROJECT, { recursive: true, force: true });

// A title that names a place must get that place. "Different every time" is not
// a licence to set "Beach Day Bonanza" on the moon.
const HINTS: [string, string][] = [
  ["Beach Day Bonanza", "Beach"],
  ["Mountain Hike Havoc", "Mountains"],
  ["Rainy Day Riddles", "Rainy day"],
  ["Moon Landing Laughs", "Moon"],
  ["Campfire Chuckles", "Night camp"],
  ["Park Picnic Puns", "Park"],
];
// The stock script is beach-flavoured (crabs, shellfish) on purpose here: the
// title must still win, otherwise every joke about the sea drags the scene to
// the beach no matter what the episode is called.
const BODY = SCRIPT.split("\n").slice(1).join("\n");
for (const [title, expected] of HINTS) {
  const e = buildDogEpisode({ script: `Title: ${title}\n${BODY}` });
  ok(`"${title}" picks ${expected}`, e.setting === expected, e.setting);
}

console.log(fails ? `\n${fails} FAILED\n` : "\nall dog checks pass\n");
process.exit(fails ? 1 : 0);
