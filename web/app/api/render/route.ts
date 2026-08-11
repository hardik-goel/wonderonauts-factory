import { NextResponse } from "next/server";
import { startRender } from "@/lib/sandbox";
import { slugify } from "@/lib/script";
import type { Draft } from "@/lib/types";

// Creating the sandbox and writing files is quick; the build itself is
// detached and outlives this request.
export const maxDuration = 120;

export async function POST(req: Request) {
  let draft: Draft;
  try {
    draft = (await req.json()) as Draft;
  } catch {
    return NextResponse.json({ error: "Expected JSON body." }, { status: 400 });
  }

  if (!draft?.videoJson?.scenes?.length || !draft.renderScenes) {
    return NextResponse.json(
      { error: "That draft is incomplete — write the script first." },
      { status: 400 },
    );
  }

  draft.slug = slugify(draft.slug || draft.videoJson.title);

  try {
    const job = await startRender(draft);
    return NextResponse.json(job);
  } catch (err) {
    const message = err instanceof Error ? err.message : "Could not start the render.";
    return NextResponse.json({ error: message }, { status: 502 });
  }
}
