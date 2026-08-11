/**
 * Parser cases. The point of the paste box is that someone's existing script
 * survives a copy-paste, so each case here is a shape a real script arrives in.
 *
 *   pnpm exec tsx scripts/verify-parse.ts
 */
import { parseScript } from "../lib/parse-script";

let failures = 0;
function check(label: string, cond: boolean, detail = "") {
  if (!cond) failures++;
  console.log(`  ${cond ? "PASS" : "FAIL"}  ${label}${detail ? `  ${detail}` : ""}`);
}

// 1. The markdown table this project hands out (# | Chapter | Narration | Words)
const TABLE = `
**Title:** The Hare and the Tortoise

| # | Chapter | Narration | Words |
|---|---|---|---|
| 1 | Blast off! | Hello, Wonder-o-nauts! Today we are telling a very old story about a speedy hare and a slow tortoise. | 38 |
| 2 | Meet the hare | The hare was fast. Really fast. He could zip across a field before you finished blinking. | 41 |
| 3 | Mission complete! | So the hare had the speed, but the tortoise had the steady. Tell us in the comments! | 39 |
`;
{
  const r = parseScript(TABLE);
  check("table: title", r.title === "The Hare and the Tortoise", r.title);
  check("table: 3 scenes", r.scenes.length === 3, String(r.scenes.length));
  check("table: chapter", r.scenes[1]?.chapter === "Meet the hare", r.scenes[1]?.chapter);
  check("table: narration picked over the word count",
    r.scenes[0]?.narration.startsWith("Hello, Wonder-o-nauts!"), r.scenes[0]?.narration.slice(0, 28));
  check("table: header row dropped",
    !r.scenes.some((s) => /narration/i.test(s.narration)));
}

// 2. Two-column table, no numbering
{
  const r = parseScript(`| Chapter | Narration |
|---|---|
| Opening | The hare was fast and he knew it, telling everyone every day. |
| Closing | The tortoise never stopped walking and reached the tree first. |`);
  check("2-col table: 2 scenes", r.scenes.length === 2, String(r.scenes.length));
  check("2-col table: chapter", r.scenes[0]?.chapter === "Opening", r.scenes[0]?.chapter);
}

// 3. Numbered outline
{
  const r = parseScript(`Title: The Hare and the Tortoise

1. Blast off!
Hello, Wonder-o-nauts! Today we tell a very old story about a speedy hare.

2. The nap
Halfway there the hare looked back, saw nothing, and fell fast asleep.

3. Mission complete!
Slow and steady got there first. What is your slow and steady thing?`);
  check("outline: title", r.title === "The Hare and the Tortoise", r.title);
  check("outline: 3 scenes", r.scenes.length === 3, String(r.scenes.length));
  check("outline: chapter", r.scenes[1]?.chapter === "The nap", r.scenes[1]?.chapter);
  check("outline: number stripped from narration",
    !/^\d/.test(r.scenes[0]?.narration ?? ""), r.scenes[0]?.narration.slice(0, 24));
}

// 4. Bare paragraphs — chapters must be invented, not left blank
{
  const r = parseScript(`The hare was fast and he knew it, telling everyone about it every single day.

The tortoise was slow but she never stopped walking, one small step after another.

She reached the oak tree first while the hare was still fast asleep in the grass.`);
  check("paragraphs: 3 scenes", r.scenes.length === 3, String(r.scenes.length));
  check("paragraphs: every scene gets a chapter",
    r.scenes.every((s) => s.chapter.length > 0), r.scenes.map((s) => s.chapter).join(" / "));
}

// 5. Degenerate input must not throw or invent scenes
{
  check("empty input", parseScript("").scenes.length === 0);
  check("whitespace only", parseScript("   \n\n  ").scenes.length === 0);
  check("title only", parseScript("Title: Nothing else").scenes.length === 0);
  check("too short to be narration", parseScript("hi\n\nthere").scenes.length === 0);
}

console.log(failures ? `\n${failures} FAILED\n` : "\nall parser cases pass\n");
process.exit(failures ? 1 : 0);
