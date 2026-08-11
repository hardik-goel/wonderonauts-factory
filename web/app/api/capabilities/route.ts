import { NextResponse } from "next/server";
import { PROPS, LOOKS } from "@/lib/scaffold";
import { PRESETS } from "@/lib/presets";

/**
 * What this deployment can actually do. The UI reads this on load so a
 * key-less deployment shows the keyless paths instead of offering an AI
 * button that dead-ends in an error.
 */
export async function GET() {
  return NextResponse.json({
    ai: Boolean(process.env.ANTHROPIC_API_KEY),
    props: PROPS,
    looks: LOOKS,
    presets: PRESETS,
  });
}
