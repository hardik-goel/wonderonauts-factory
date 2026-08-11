import { NextResponse } from "next/server";
import { buildDraft, PROPS, LOOKS, type ScaffoldInput } from "@/lib/scaffold";

/**
 * The keyless authoring route: you supply the words, this supplies a valid
 * video.json and a render_scenes.py. No API key involved.
 */
export const maxDuration = 30;

const MAX_SCENES = 20;

export async function POST(req: Request) {
  let input: Partial<ScaffoldInput>;
  try {
    input = await req.json();
  } catch {
    return NextResponse.json({ error: "Expected JSON body." }, { status: 400 });
  }

  const title = (input.title ?? "").trim();
  if (!title) return NextResponse.json({ error: "Give the episode a title." }, { status: 400 });

  const scenes = (input.scenes ?? [])
    .map((s) => ({ chapter: (s?.chapter ?? "").trim(), narration: (s?.narration ?? "").trim() }))
    .filter((s) => s.narration);

  if (scenes.length < 3) {
    return NextResponse.json(
      { error: "Write at least 3 scenes — 10 is the sweet spot." },
      { status: 400 },
    );
  }
  if (scenes.length > MAX_SCENES) {
    return NextResponse.json({ error: `At most ${MAX_SCENES} scenes.` }, { status: 400 });
  }

  const prop = PROPS.includes(input.prop ?? "") ? input.prop! : "rocket";
  const look = (LOOKS as readonly string[]).includes(input.look ?? "")
    ? (input.look as ScaffoldInput["look"])
    : "land";

  const draft = buildDraft({
    title,
    scenes,
    prop,
    look,
    description: input.description,
    tags: input.tags,
  });

  return NextResponse.json(draft);
}
