export type Scene = {
  image: string;
  chapter: string;
  sfx: "whoosh" | "pop" | "sparkle" | "success";
  narration: string;
  /** Overrides the episode voice for this scene — how a two-hander gives each
   *  character its own voice instead of one narrator reading both parts. */
  voice?: string;
  rate?: string;
};

export type VideoConfig = {
  title: string;
  /** "dialogue" relaxes factory.py's per-scene word-count lint for two-handers. */
  format?: "explainer" | "dialogue";
  voice: string;
  rate: string;
  description: string;
  tags: string;
  thumbnail_text: string;
  thumbnail_prop: string;
  thumbnail_bg?: "land" | "sea" | "none";
  music: boolean;
  music_seed: number;
  bgm_vol: number;
  shorts_scenes: number[];
  scenes: Scene[];
};

export type Draft = {
  slug: string;
  /** Present on bundled episodes; otherwise taken from videoJson.title. */
  title?: string;
  videoJson: VideoConfig;
  renderScenes: string;
  /** Where the research came from, for the UI to show provenance. */
  source: { kind: "topic" | "youtube"; label: string; transcriptChars: number };
};

export type JobStatus = "starting" | "running" | "done" | "failed";

export type Job = {
  id: string;
  slug: string;
  title: string;
  status: JobStatus;
  createdAt: string;
  finishedAt?: string;
  exitCode?: number;
  /** Populated once the build finishes. */
  artifacts: string[];
  qc?: string;
};

/** Artifacts the factory writes, in the order the UI should present them. */
export const ARTIFACTS = [
  "final.mp4",
  "short.mp4",
  "thumbnail_a.jpg",
  "thumbnail_b.jpg",
  "captions.srt",
  "short_captions.srt",
  "metadata.txt",
  "qc_report.txt",
  "build_manifest.json",
] as const;
