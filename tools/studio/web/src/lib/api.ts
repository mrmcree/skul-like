import type {
  Action, AssetInfo, AssetSummary, ExpandResult, Kind, LlmStatus, ProcessResult, PromptRequest, PromptResult, QcReport,
  RefineResult,
} from "./types";

async function request<T>(method: string, url: string, body?: unknown, raw?: Blob): Promise<T> {
  const init: RequestInit = { method };
  if (raw) {
    init.body = raw;
  } else if (body !== undefined) {
    init.headers = { "Content-Type": "application/json" };
    init.body = JSON.stringify(body);
  }
  let res: Response;
  try {
    res = await fetch(url, init);
  } catch {
    throw new Error("无法连接后端（python tools/asset_studio.py 在运行吗？）");
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = Array.isArray(data.detail)
      ? data.detail.map((d: { msg: string }) => d.msg).join("; ")
      : data.detail;
    throw new Error(detail || `请求失败 (${res.status})`);
  }
  return data as T;
}

const enc = encodeURIComponent;
const base = (name: string) => `/api/assets/${enc(name)}`;

export const api = {
  assets: () => request<AssetSummary[]>("GET", "/api/assets"),
  asset: (name: string) => request<AssetInfo>("GET", base(name)),
  qc: (name: string) => request<QcReport>("GET", `${base(name)}/qc`),
  process: (name: string) => request<ProcessResult>("POST", `${base(name)}/process`),
  saveConfig: (name: string, kind: Kind, config: unknown) =>
    request<{ ok: boolean }>("PUT", `${base(name)}/config`, { kind, config }),
  upload: (name: string, file: File) =>
    request<{ ok: boolean; file: string }>("POST", `${base(name)}/upload?filename=${enc(file.name)}`, undefined, file),
  presets: () => request<Record<string, Action[]>>("GET", "/api/presets"),
  prompts: (body: PromptRequest) => request<PromptResult>("POST", "/api/prompts", body),
  llmStatus: () => request<LlmStatus>("GET", "/api/llm/status"),
  llmModels: () => request<{ models: string[] }>("GET", "/api/llm/models"),
  expand: (kind: PromptRequest["kind"], idea: string, model: string) =>
    request<ExpandResult>("POST", "/api/llm/expand", { kind, idea, model }),
  refine: (prompt: string, instruction: string, model: string) =>
    request<RefineResult>("POST", "/api/llm/refine", { prompt, instruction, model }),
};
