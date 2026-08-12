import { NextResponse } from "next/server";
import { startRender, describeSandboxError } from "@/lib/sandbox";
import { slugify } from "@/lib/slug";
import { PRESETS, isPreset } from "@/lib/presets";
import type { Draft } from "@/lib/types";

// Creating the sandbox and writing files is quick; the build itself is
// detached and outlives this request.
export const maxDuration = 120;

export async function POST(req: Request) {
  let body: Draft & { preset?: string };
  try {
    body = (await req.json()) as Draft & { preset?: string };
  } catch {
    return NextResponse.json({ error: "Expected JSON body." }, { status: 400 });
  }

  // Bundled episode: script and art are already committed in the repo the
  // sandbox clones, so there is nothing to write and no key involved.
  if (body.preset) {
    if (!isPreset(body.preset)) {
      return NextResponse.json({ error: "No such bundled episode." }, { status: 400 });
    }
    const preset = PRESETS.find((p) => p.slug === body.preset)!;
    try {
      return NextResponse.json(
        await startRender({ slug: preset.slug, title: preset.title }),
      );
    } catch (err) {
      return NextResponse.json({ error: describeSandboxError(err) }, { status: 502 });
    }
  }

  const draft = body;
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
    return NextResponse.json({ error: describeSandboxError(err) }, { status: 502 });
  }
}
