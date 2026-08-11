/**
 * Parse a pasted script into scenes.
 *
 * People arrive with a script already written, in whatever shape the thing
 * that produced it used — a markdown table from a chat, a numbered outline
 * from a doc, or just paragraphs. Retyping ten scenes into ten boxes is the
 * kind of friction that stops someone shipping, so this accepts all of those
 * and is deliberately forgiving: an unrecognised shape degrades to
 * "one paragraph per scene" rather than erroring.
 */

export type ParsedScript = {
  title: string;
  scenes: { chapter: string; narration: string }[];
};

/** Header cells that mean "this row is column labels, not content". */
const HEADERISH = /^(#|no\.?|num(ber)?|scene|chapter|section|narration|script|words?|count)$/i;

function splitRow(line: string): string[] {
  return line
    .replace(/^\s*\|/, "")
    .replace(/\|\s*$/, "")
    .split("|")
    .map((c) => c.trim());
}

/** A markdown separator row: |---|:--:|---| */
function isSeparator(cells: string[]): boolean {
  return cells.length > 0 && cells.every((c) => /^:?-{2,}:?$/.test(c));
}

function stripMarkdown(s: string): string {
  return s
    .replace(/\*\*(.*?)\*\*/g, "$1")
    .replace(/[*_`]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function wordCount(s: string): number {
  return s.trim().split(/\s+/).filter(Boolean).length;
}

function findTitle(text: string): string {
  // "Title: X", "**Title:** X", or a leading markdown heading
  const explicit = text.match(/^\s*(?:\*\*)?title(?:\*\*)?\s*[:\-—]\s*(.+)$/im);
  if (explicit) return stripMarkdown(explicit[1]);
  const heading = text.match(/^\s{0,3}#{1,3}\s+(.+)$/m);
  if (heading) return stripMarkdown(heading[1]);
  return "";
}

/**
 * Markdown / pipe table. The column layout varies (`# | Chapter | Narration |
 * Words`, `Chapter | Narration`, …), so identify columns by content rather
 * than position: the longest cell in a row is the narration, and the best
 * short non-numeric cell is the chapter.
 */
function parseTable(lines: string[]): ParsedScript["scenes"] {
  const rows = lines
    .filter((l) => l.trim().startsWith("|"))
    .map(splitRow)
    .filter((cells) => cells.length >= 2 && !isSeparator(cells));

  const scenes: ParsedScript["scenes"] = [];
  for (const cells of rows) {
    const clean = cells.map(stripMarkdown);
    // header row: every non-empty cell is a known column label
    const nonEmpty = clean.filter(Boolean);
    if (nonEmpty.length && nonEmpty.every((c) => HEADERISH.test(c))) continue;

    let narrIdx = -1;
    let best = 0;
    clean.forEach((c, i) => {
      const w = wordCount(c);
      if (w > best) {
        best = w;
        narrIdx = i;
      }
    });
    if (narrIdx < 0 || best < 4) continue; // not a content row

    const narration = clean[narrIdx];
    const chapter =
      clean.find(
        (c, i) =>
          i !== narrIdx && c && !/^\d+$/.test(c) && wordCount(c) <= 6,
      ) ?? "";

    scenes.push({ chapter, narration });
  }
  return scenes;
}

/**
 * Blocks separated by blank lines. A block may lead with a label line
 * ("1. Blast off!", "Chapter: Blast off!", "Blast off!") followed by prose.
 */
function parseBlocks(text: string): ParsedScript["scenes"] {
  const blocks = text
    .split(/\n\s*\n/)
    .map((b) => b.trim())
    .filter(Boolean);

  const scenes: ParsedScript["scenes"] = [];
  for (const block of blocks) {
    const lines = block.split("\n").map((l) => l.trim()).filter(Boolean);
    if (!lines.length) continue;

    // skip a stray title line
    if (/^(?:\*\*)?title(?:\*\*)?\s*[:\-—]/i.test(lines[0]) && lines.length === 1) continue;

    let chapter = "";
    let body = lines;

    const first = stripMarkdown(lines[0]);
    const labelled = first.match(/^(?:scene\s*)?\d+\s*[.):\-—]\s*(.+)$/i);
    const colon = first.match(/^(?:chapter|section)\s*[:\-—]\s*(.+)$/i);

    if (colon) {
      chapter = colon[1];
      body = lines.slice(1);
    } else if (labelled && wordCount(labelled[1]) <= 6 && lines.length > 1) {
      chapter = labelled[1];
      body = lines.slice(1);
    } else if (lines.length > 1 && wordCount(first) <= 6) {
      // a short standalone first line is a heading, not narration
      chapter = first.replace(/^#+\s*/, "");
      body = lines.slice(1);
    }

    const narration = stripMarkdown(
      body.join(" ").replace(/^(?:scene\s*)?\d+\s*[.):\-—]\s*/i, ""),
    );
    if (wordCount(narration) < 4) continue;
    scenes.push({ chapter, narration });
  }
  return scenes;
}

export function parseScript(raw: string): ParsedScript {
  const text = (raw ?? "").replace(/\r\n?/g, "\n").trim();
  if (!text) return { title: "", scenes: [] };

  const title = findTitle(text);
  const lines = text.split("\n");

  let scenes = parseTable(lines);
  if (scenes.length < 2) {
    // Not a table (or only one row survived): fall back to blocks, minus any
    // table rows and the title line so they can't leak into the prose.
    const withoutTable = lines
      .filter((l) => !l.trim().startsWith("|"))
      .filter((l) => !/^\s*(?:\*\*)?title(?:\*\*)?\s*[:\-—]/i.test(l))
      .join("\n");
    const blocks = parseBlocks(withoutTable);
    if (blocks.length > scenes.length) scenes = blocks;
  }

  // Fill any chapter the source didn't give us; the factory requires one.
  scenes = scenes.map((s, i) => ({
    chapter: s.chapter || defaultChapter(i, scenes.length),
    narration: s.narration,
  }));

  return { title, scenes };
}

function defaultChapter(i: number, total: number): string {
  if (i === 0) return "Blast off!";
  if (i === total - 1) return "Mission complete!";
  return `Part ${i + 1}`;
}
