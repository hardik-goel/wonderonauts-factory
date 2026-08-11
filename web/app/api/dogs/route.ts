import { NextResponse } from "next/server";
import { buildDogEpisode, parseDialogue, DOG_VOICES, SETTINGS } from "@/lib/dogs";

/** Keyless: you paste the dialogue, this builds the episode. */
export const maxDuration = 30;

export async function GET() {
  return NextResponse.json({
    voices: DOG_VOICES,
    settings: SETTINGS.map((s) => ({ id: s.id, label: s.label })),
  });
}

export async function POST(req: Request) {
  let input: { script?: string; title?: string; setting?: string; voices?: Record<string, string> };
  try {
    input = await req.json();
  } catch {
    return NextResponse.json({ error: "Expected JSON body." }, { status: 400 });
  }

  const script = (input.script ?? "").trim();
  if (!script) {
    return NextResponse.json({ error: "Paste some dialogue first." }, { status: 400 });
  }
  if (script.length > 20_000) {
    return NextResponse.json({ error: "That script is too long." }, { status: 400 });
  }

  const { lines } = parseDialogue(script);
  if (lines.length < 2) {
    return NextResponse.json(
      {
        error:
          'Write it as "Name: line", one per line — e.g. "Rex: Why don\'t crabs share?"',
      },
      { status: 400 },
    );
  }
  if (lines.length > 24) {
    return NextResponse.json({ error: "Keep it under 24 lines." }, { status: 400 });
  }

  try {
    return NextResponse.json(buildDogEpisode(input as never));
  } catch (err) {
    const message = err instanceof Error ? err.message : "Could not build the episode.";
    return NextResponse.json({ error: message }, { status: 400 });
  }
}
