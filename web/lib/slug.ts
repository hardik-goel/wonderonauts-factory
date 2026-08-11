/**
 * Shared so the keyless scaffold path never has to import lib/script.ts,
 * which pulls in the Anthropic SDK.
 */
export function slugify(s: string): string {
  return (
    s
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .replace(/-{2,}/g, "-")
      .slice(0, 60) || "new-episode"
  );
}
