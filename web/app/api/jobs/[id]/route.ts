import { NextResponse } from "next/server";
import { getJob, stopJob } from "@/lib/sandbox";

export const maxDuration = 60;

const ID = /^[a-z0-9-]{3,64}$/;

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  if (!ID.test(id)) return NextResponse.json({ error: "Bad job id." }, { status: 400 });

  try {
    return NextResponse.json(await getJob(id));
  } catch (err) {
    const message = err instanceof Error ? err.message : "Job not found.";
    return NextResponse.json({ error: message }, { status: 404 });
  }
}

/** Stop the microVM once the artifacts have been collected. */
export async function DELETE(
  _req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  if (!ID.test(id)) return NextResponse.json({ error: "Bad job id." }, { status: 400 });

  try {
    await stopJob(id);
    return NextResponse.json({ stopped: true });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Could not stop the job.";
    return NextResponse.json({ error: message }, { status: 502 });
  }
}
