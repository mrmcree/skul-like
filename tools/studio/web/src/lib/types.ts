export type Kind = "sprite" | "env";
export type Health = "ok" | "warn" | "err";

export interface AssetSummary {
  name: string;
  kind: Kind | null;
  raw_images: string[];
}

export interface Strip {
  name: string;
  file: string;
  frames: number;
  row?: number;
  [key: string]: unknown;
}

export interface SpriteConfig {
  cell: [number, number];
  anchor: [number, number];
  target_height: number;
  palette_colors?: number;
  strips: Strip[];
  [key: string]: unknown;
}

export interface EnvConfig {
  out_dir: string;
  layers: { name: string }[];
  ground: { name: string };
  sheets: unknown[];
  [key: string]: unknown;
}

export interface EnvOutput {
  name: string;
  url: string;
  size?: [number, number];
  texels?: [number, number];
  [key: string]: unknown;
}

export interface AssetInfo {
  name: string;
  kind: Kind | null;
  config: SpriteConfig | EnvConfig | null;
  sheet_url?: string | null;
  sheet_mtime?: number;
  outputs?: EnvOutput[];
}

export interface Issue {
  level: "error" | "warning";
  code: string;
  message: string;
  row: number | null;
  frame: number | null;
}

export interface QcReport {
  ok: boolean;
  errors: number;
  warnings: number;
  issues: Issue[];
}

export interface ProcessResult {
  ok: boolean;
  log: string;
  qc: QcReport;
}

export interface Action {
  name: string;
  frames: number;
  description: string;
}

export interface PromptItem {
  file: string;
  aspect: string;
  rows?: string[];
  prompt: string;
}

export interface PromptRequest {
  kind: "character" | "environment";
  style: string;
  subject?: string;
  actions?: Action[];
  target_height?: number;
  theme?: string;
  items?: string;
}

export interface PromptResult {
  prompts: PromptItem[];
  config?: SpriteConfig;
}

export interface LogLine {
  time: string;
  level: "info" | "ok" | "error";
  text: string;
}

export interface LlmStatus {
  configured: boolean;
  model: string;
}

export interface ExpandResult {
  subject?: string;
  theme?: string;
  items?: string;
}

export interface RefineResult {
  prompt: string;
  warnings: string[];
}
