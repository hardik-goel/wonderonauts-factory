/**
 * YouTube link -> research material.
 *
 * This fetches the *transcript only*, and it is used purely as research input
 * for an original script. Nothing from the source video ends up in the output:
 * no audio, no frames, no phrasing lifted verbatim. That boundary is the whole
 * reason the factory's output stays copyright-clean, so do not extend this to
 * download media.
 *
 * There is no official transcript API without OAuth, so this scrapes the
 * caption track out of the watch page. That is inherently fragile and
 * frequently blocked from datacenter IPs, so every failure path degrades to
 * "use the title as the topic" rather than throwing.
 */

export type Research = {
  kind: "topic" | "youtube";
  label: string;
  transcript: string;
};

const UA =
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 " +
  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36";

export function parseVideoId(input: string): string | null {
  const s = input.trim();
  if (/^[\w-]{11}$/.test(s)) return s;
  let u: URL;
  try {
    u = new URL(s);
  } catch {
    return null;
  }
  if (!/(^|\.)(youtube\.com|youtu\.be)$/i.test(u.hostname)) return null;
  if (u.hostname.toLowerCase().endsWith("youtu.be")) {
    const id = u.pathname.slice(1).split("/")[0];
    return /^[\w-]{11}$/.test(id) ? id : null;
  }
  const v = u.searchParams.get("v");
  if (v && /^[\w-]{11}$/.test(v)) return v;
  const m = u.pathname.match(/\/(shorts|embed|live)\/([\w-]{11})/);
  return m ? m[2] : null;
}

function decodeEntities(s: string): string {
  return s
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&#(\d+);/g, (_, d) => String.fromCharCode(Number(d)));
}

/** Pull the first usable caption track out of the watch page's player JSON. */
function findCaptionUrl(html: string): string | null {
  const marker = '"captionTracks":';
  const at = html.indexOf(marker);
  if (at < 0) return null;
  const start = html.indexOf("[", at);
  if (start < 0) return null;
  // walk to the matching bracket rather than regex-ing across nested objects
  let depth = 0;
  let end = -1;
  for (let i = start; i < html.length; i++) {
    if (html[i] === "[") depth++;
    else if (html[i] === "]") {
      depth--;
      if (depth === 0) {
        end = i + 1;
        break;
      }
    }
  }
  if (end < 0) return null;
  let tracks: Array<{ baseUrl?: string; languageCode?: string; kind?: string }>;
  try {
    tracks = JSON.parse(html.slice(start, end));
  } catch {
    return null;
  }
  const english = tracks.find((t) => t.languageCode?.startsWith("en"));
  return (english ?? tracks[0])?.baseUrl ?? null;
}

export async function fetchResearch(input: string): Promise<Research> {
  const id = parseVideoId(input);
  if (!id) return { kind: "topic", label: input.trim(), transcript: "" };

  const url = `https://www.youtube.com/watch?v=${id}`;
  let title = url;
  try {
    const page = await fetch(url, {
      headers: { "user-agent": UA, "accept-language": "en-US,en;q=0.9" },
    });
    if (!page.ok) throw new Error(`watch page ${page.status}`);
    const html = await page.text();

    const t = html.match(/<meta name="title" content="([^"]*)"/);
    if (t) title = decodeEntities(t[1]);

    const capUrl = findCaptionUrl(html);
    if (!capUrl) return { kind: "youtube", label: title, transcript: "" };

    const cap = await fetch(decodeEntities(capUrl), { headers: { "user-agent": UA } });
    if (!cap.ok) throw new Error(`caption track ${cap.status}`);
    const xml = await cap.text();
    const transcript = Array.from(xml.matchAll(/<text[^>]*>([\s\S]*?)<\/text>/g))
      .map((m) => decodeEntities(m[1].replace(/<[^>]+>/g, "")).replace(/\s+/g, " "))
      .join(" ")
      .trim();

    return { kind: "youtube", label: title, transcript: transcript.slice(0, 40_000) };
  } catch {
    // Blocked, rate-limited, or no captions: the title alone is still a useful
    // topic, and the script writer is told to treat research as optional.
    return { kind: "youtube", label: title, transcript: "" };
  }
}
