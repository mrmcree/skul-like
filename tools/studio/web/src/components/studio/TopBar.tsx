import { Boxes, LayoutGrid, Loader2, Play, ScanSearch, Search, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import type { Kind, QcReport } from "@/lib/types";
import { cn } from "@/lib/utils";
import { KindBadge, QcSummary, Tip } from "./common";

export type Workspace = "assets" | "prompts";

interface Props {
  workspace: Workspace;
  onWorkspace: (w: Workspace) => void;
  current: string | null;
  kind: Kind | null;
  qc: QcReport | null;
  processing: boolean;
  onProcess: () => void;
  onQc: () => void;
  onPalette: () => void;
}

const WORKSPACES = [
  { id: "assets", label: "素材", icon: LayoutGrid },
  { id: "prompts", label: "提示词", icon: Sparkles },
] as const;

export function TopBar({ workspace, onWorkspace, current, kind, qc, processing, onProcess, onQc, onPalette }: Props) {
  const showAsset = workspace === "assets" && current;
  return (
    <header className="flex h-11 shrink-0 items-center gap-3 border-b bg-card px-3">
      <div className="flex items-center gap-2">
        <div className="grid size-6 place-items-center rounded-md bg-primary text-primary-foreground shadow-[0_0_12px] shadow-primary/40">
          <Boxes className="size-3.5" />
        </div>
        <span className="text-sm font-semibold tracking-tight">Asset Studio</span>
      </div>
      <Separator orientation="vertical" className="h-5" />
      <nav className="flex items-center gap-0.5 rounded-md bg-muted p-0.5">
        {WORKSPACES.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => onWorkspace(id)}
            className={cn(
              "flex h-7 items-center gap-1.5 rounded px-2.5 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground",
              workspace === id && "bg-accent text-foreground shadow-sm",
            )}
          >
            <Icon className="size-3.5" />
            {label}
          </button>
        ))}
      </nav>
      {showAsset && (
        <div className="flex min-w-0 items-center gap-2 text-xs text-muted-foreground">
          <span className="opacity-50">/</span>
          <span className="truncate font-mono font-medium text-foreground">{current}</span>
          <KindBadge kind={kind} />
        </div>
      )}
      <div className="flex-1" />
      <button
        onClick={onPalette}
        className="flex h-7 w-56 items-center gap-2 rounded-md border bg-background px-2 text-xs text-muted-foreground transition-colors hover:border-muted-foreground/40 hover:text-foreground"
      >
        <Search className="size-3.5" />
        搜索命令、素材…
        <kbd className="ml-auto rounded border px-1 font-mono text-[10px]">Ctrl K</kbd>
      </button>
      {showAsset && (
        <div className="flex items-center gap-2">
          <QcSummary qc={qc} />
          <Tip tip="重新运行质检">
            <Button variant="outline" size="sm" onClick={onQc} disabled={!kind || processing}>
              <ScanSearch />
              质检
            </Button>
          </Tip>
          <Tip tip="运行处理脚本 · Ctrl+Enter">
            <Button size="sm" onClick={onProcess} disabled={!kind || processing} className="min-w-20">
              {processing ? <Loader2 className="animate-spin" /> : <Play />}
              {processing ? "处理中…" : "处理"}
            </Button>
          </Tip>
        </div>
      )}
    </header>
  );
}
