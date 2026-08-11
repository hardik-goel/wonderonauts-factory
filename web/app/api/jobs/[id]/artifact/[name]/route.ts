import { NextResponse } from "next/server";
import { readArtifact } from "@/lib/sandbox";

export const maxDuration = 300;

const ID = /^[a-z0-9-]{3,64}$/;
const NAME = /^[a-z0-9_]+\.(mp4|jpg|srt|txt|json)$/;

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ id: string; name: string }> },
) {
  const { id, name } = await params;
  if (!ID.test(id) || !NAME.test(name)) {
    return NextResponse.json({ error: "Bad request." }, { status: 400 });
  }

  try {
    const found = await readArtifact(id, name);
    if (!found) return NextResponse.json({ error: "No such artifact." }, { status: 404 });

    return new Response(found.body, {
      headers: {
        "content-type": found.contentType,
        // inline so video/images preview in the browser; the UI adds
        // `download` on the links that should save instead
        "content-disposition": `inline; filename="${name}"`,
        "cache-control": "private, max-age=3600",
      },
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Could not read the artifact.";
    return NextResponse.json({ error: message }, { status: 502 });
  }
}
