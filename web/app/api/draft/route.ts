import { NextResponse } from "next/server";
import { writeEpisode } from "@/lib/script";
import { fetchResearch } from "@/lib/youtube";

// Script generation is one long model call; give it room.
export const maxDuration = 300;

export async function POST(req: Request) {
  if (!process.env.ANTHROPIC_API_KEY) {
    return NextResponse.json(
      { error: "ANTHROPIC_API_KEY is not set on this deployment." },
      { status: 500 },
    );
  }

  let input: { topic?: string };
  try {
    input = await req.json();
  } catch {
    return NextResponse.json({ error: "Expected JSON body." }, { status: 400 });
  }

  const topic = (input.topic ?? "").trim();
  if (!topic) {
    return NextResponse.json(
      { error: "Give me a question or a YouTube link." },
      { status: 400 },
    );
  }
  if (topic.length > 2000) {
    return NextResponse.json({ error: "That topic is too long." }, { status: 400 });
  }

  try {
    const research = await fetchResearch(topic);
    // For a link, the video's title is the actual subject; for a plain topic
    // the input is the subject.
    const subject = research.kind === "youtube" ? research.label : topic;
    const draft = await writeEpisode(subject, research);
    return NextResponse.json(draft);
  } catch (err) {
    const message = err instanceof Error ? err.message : "Script generation failed.";
    return NextResponse.json({ error: message }, { status: 502 });
  }
}
