/**
 * Verify the keyless scaffold generates Python that actually renders.
 *
 * The generator emits source that only runs later, inside a sandbox — so a
 * broken primitive call would first surface a minute into a user's build.
 * This writes a throwaway project, renders it with the real toolkit, and lints
 * the config, catching that here instead.
 *
 * Coverage is pairwise, not the full cross product: `look` only selects the
 * backdrop call and `prop` only selects the hero call, so they cannot interact.
 * Checking every prop against one look plus every look against one prop is the
 * same coverage as all 42 combinations at a third of the render time.
 *
 *   pnpm exec tsx scripts/verify-scaffold.ts
 */
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { buildDraft, PROPS, LOOKS, type ScaffoldInput } from "../lib/scaffold";

const ROOT = path.resolve(import.meta.dirname, "../..");
const PROJECT = path.join(ROOT, "projects", "_scaffoldcheck");
const PY = fs.existsSync(path.join(ROOT, ".venv/bin/python"))
  ? path.join(ROOT, ".venv/bin/python")
  : "python3";

const CHAPTERS = [
  "Blast off!", "The big question", "Not what you think", "Secret one",
  "A closer look", "Secret two", "Try it yourself", "The numbers",
  "Bonus wonder", "Mission complete!",
];

function run(args: string[]): string {
  return execFileSync(PY, args, {
    cwd: ROOT,
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
  });
}

let failures = 0;

const CASES: { look: ScaffoldInput["look"]; prop: string }[] = [
  ...PROPS.map((prop) => ({ look: "land" as const, prop })),
  ...LOOKS.filter((l) => l !== "land").map((look) => ({ look, prop: "rocket" })),
];

// Only these scenes are rendered: between them they exercise the title card,
// all four middle layouts (so every way the prop is drawn), and the outro's
// end-card safe-zone assertion.
const COVER = [1, 2, 3, 4, 5, 10];

{
  for (const { look, prop } of CASES) {
    const input: ScaffoldInput = {
      title: "Why do magnets stick together?",
      scenes: CHAPTERS.map((chapter) => ({
        chapter,
        narration: "word ".repeat(42).trim(),
      })),
      prop,
      look,
    };

    fs.rmSync(PROJECT, { recursive: true, force: true });
    fs.mkdirSync(path.join(PROJECT, "frames"), { recursive: true });

    const draft = buildDraft(input);
    fs.writeFileSync(path.join(PROJECT, "render_scenes.py"), draft.renderScenes);
    fs.writeFileSync(
      path.join(PROJECT, "video.json"),
      JSON.stringify(draft.videoJson, null, 2) + "\n",
    );

    try {
      run([path.join(PROJECT, "render_scenes.py"), ...COVER.map(String)]);
      const frames = fs
        .readdirSync(path.join(PROJECT, "frames"))
        .filter((f) => f.endsWith(".png"));
      if (frames.length !== COVER.length) {
        throw new Error(`rendered ${frames.length}/${COVER.length} frames`);
      }
      // --validate prints "<slug>  --  OK" (two spaces); match loosely so the
      // check tests the generator rather than the exact column layout.
      const lint = run(["factory.py", "--validate", "projects/_scaffoldcheck"]);
      if (!/--\s+OK\b/.test(lint)) throw new Error(`lint said: ${lint.trim()}`);
      console.log(`  PASS  ${look.padEnd(6)} ${prop}`);
    } catch (err) {
      failures++;
      const msg = err instanceof Error ? err.message : String(err);
      console.log(
        `  FAIL  ${look.padEnd(6)} ${prop}\n        ` +
          msg.split("\n").slice(-4).join("\n        "),
      );
    }
  }
}

fs.rmSync(PROJECT, { recursive: true, force: true });
console.log(
  failures
    ? `\n${failures} combination(s) FAILED\n`
    : `\nall ${CASES.length} combinations render and lint clean\n`,
);
process.exit(failures ? 1 : 0);
