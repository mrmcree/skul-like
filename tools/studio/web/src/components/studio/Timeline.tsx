import { ClipboardCopy, Columns2, Copy, Download, Film, Play, StepForward } from "lucide-react";
import {
  ContextMenu, ContextMenuContent, ContextMenuItem, ContextMenuLabel, ContextMenuSeparator, ContextMenuTrigger,
} from "@/components/ui/context-menu";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { Issue, Strip } from "@/lib/types";
import { cn } from "@/lib/utils";
import { HealthDot, worst } from "./common";
import { FrameThumb } from "./FrameThumb";
import type { ExportMode } from "./Viewport";

interface Props {
  strips: Strip[];
  sheet: HTMLImageElement | null;
  cell: [number, number];
  row: number;
  frame: number;
  issuesFor: (row: number, frame?: number) => Issue[];
  onRow: (row: number) => void;
  onFrame: (frame: number) => void;
  onCompare: (row: number) => void;
  onExportFrame: (mode: ExportMode, row: number, frame: number) => void;
  onExportStrip: (row: number) => void;
  onCopy: (text: string) => void;
}

export function Timeline(p: Props) {
  const { strips, sheet, cell, row, frame, issuesFor, onRow, onFrame, onCompare, onExportFrame, onExportStrip, onCopy } = p;
  const count = strips[row]?.frames ?? 0;
  return (
    <div className="flex h-[148px] shrink-0 border-t bg-card">
      <ScrollArea className="w-44 shrink-0 border-r">
        <div className="p-1">
          {strips.map((s, i) => (
            <ContextMenu key={`${s.name}-${i}`}>
              <ContextMenuTrigger asChild>
                <button
                  onClick={() => onRow(i)}
                  className={cn(
                    "flex w-full items-center gap-2 rounded-md px-2 py-1 text-left text-xs text-muted-foreground transition-colors hover:bg-accent hover:text-foreground",
                    i === row && "bg-primary/15 text-foreground",
                  )}
                >
                  <Film className={cn("size-3 shrink-0", i === row && "text-primary")} />
                  <span className="flex-1 truncate font-mono">{s.name}</span>
                  <span className="text-[10px] opacity-60">{s.frames}</span>
                  {worst(issuesFor(i)) && <HealthDot health={worst(issuesFor(i))} />}
                </button>
              </ContextMenuTrigger>
              <ContextMenuContent>
                <ContextMenuLabel className="font-mono">{s.name}</ContextMenuLabel>
                <ContextMenuSeparator />
                <ContextMenuItem onSelect={() => onRow(i)}>
                  <Play />
                  播放这个动画
                </ContextMenuItem>
                <ContextMenuItem onSelect={() => onCompare(i)}>
                  <Columns2 />
                  放到对比视图
                </ContextMenuItem>
                <ContextMenuItem onSelect={() => onExportStrip(i)}>
                  <Download />
                  导出整条动画（横条）
                </ContextMenuItem>
                <ContextMenuSeparator />
                <ContextMenuItem onSelect={() => onCopy(s.name)}>
                  <ClipboardCopy />
                  复制动画名
                </ContextMenuItem>
              </ContextMenuContent>
            </ContextMenu>
          ))}
        </div>
      </ScrollArea>
      <div className="min-w-0 flex-1 overflow-x-auto">
        <div className="flex h-full w-max items-center gap-1.5 px-3">
          {Array.from({ length: count }, (_, f) => {
            const list = issuesFor(row, f);
            const h = worst(list);
            return (
              <ContextMenu key={f}>
                <ContextMenuTrigger asChild>
                  <button
                    title={list.map((i) => i.message).join("\n")}
                    onClick={() => onFrame(f)}
                    className={cn(
                      "relative flex shrink-0 flex-col items-center gap-1 rounded-md border bg-background p-1 transition-colors hover:border-muted-foreground/50",
                      h === "warn" && "border-warning/60",
                      h === "err" && "border-destructive/70",
                      f === frame && "border-primary ring-1 ring-primary",
                    )}
                  >
                    <FrameThumb image={sheet} cell={cell} row={row} frame={f} height={92} />
                    <span className={cn("font-mono text-[10px] text-muted-foreground", f === frame && "text-foreground")}>{f + 1}</span>
                    {h && <HealthDot health={h} className="absolute right-1.5 top-1.5" />}
                  </button>
                </ContextMenuTrigger>
                <ContextMenuContent>
                  <ContextMenuLabel className="font-mono">
                    {strips[row]?.name} · 第 {f + 1} 帧
                  </ContextMenuLabel>
                  <ContextMenuSeparator />
                  <ContextMenuItem onSelect={() => onFrame(f)}>
                    <StepForward />
                    跳到这一帧
                  </ContextMenuItem>
                  <ContextMenuItem onSelect={() => onExportFrame("copy", row, f)}>
                    <Copy />
                    复制这一帧 (PNG)
                  </ContextMenuItem>
                  <ContextMenuItem onSelect={() => onExportFrame("download", row, f)}>
                    <Download />
                    导出这一帧
                  </ContextMenuItem>
                </ContextMenuContent>
              </ContextMenu>
            );
          })}
        </div>
      </div>
    </div>
  );
}
