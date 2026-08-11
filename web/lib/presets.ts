/**
 * The episodes that ship in the repo. Rendering one needs no API key and no
 * typing at all — the script and the scene art are already committed, so the
 * sandbox just runs the factory against a project that is already there.
 *
 * This is the zero-input proof that the keyless path works end to end.
 */
export const PRESETS = [
  {
    slug: "why-is-the-sky-blue",
    title: "Why Is the Sky BLUE?",
    blurb: "Light scattering. The reference episode, and the only one with a Hindi variant.",
  },
  {
    slug: "how-do-planes-fly",
    title: "How Do Planes FLY?",
    blurb: "Lift and thrust — and why the popular explanation is simply wrong.",
  },
  {
    slug: "why-do-we-have-seasons",
    title: "Why Do We Have SEASONS?",
    blurb: "Axial tilt, drawn so the axis points the same way in both orbit positions.",
  },
  {
    slug: "where-does-rain-come-from",
    title: "Where Does RAIN Come From?",
    blurb: "The water cycle, start to finish.",
  },
  {
    slug: "why-is-the-ocean-salty",
    title: "Why Is the SEA Salty?",
    blurb: "Weathering, rivers, and the evaporation trap.",
  },
] as const;

export type Preset = (typeof PRESETS)[number];

export function isPreset(slug: string): boolean {
  return PRESETS.some((p) => p.slug === slug);
}
