import type { AssetInfo, SpriteConfig } from "@/lib/types";
import { cn } from "@/lib/utils";

interface Props {
  online: boolean | null;
  info: AssetInfo | null;
  rowName?: string;
  frame: number;
  frames: number;
  zoom: number;
  fps: number;
  playing: boolean;
}

export function StatusBar({ online, info, rowName, frame, frames, zoom, fps, playing }: Props) {
  const sprite = info?.kind === "sprite" ? (info.config as SpriteConfig) : null;
  return (
    <footer className="flex h-6 shrink-0 items-center gap-4 border-t bg-card px-3 font-mono text-[11px] text-muted-foreground">
      <span className="flex items-center gap-1.5">
        <span
          className={cn(
            "size-1.5 rounded-full",
            online === null ? "bg-muted-foreground/40" : online ? "bg-success" : "bg-destructive",
          )}
        />
        {online === null ? "连接中…" : online ? "后端已连接" : "后端未连接"}
      </span>
      {sprite && info?.sheet_url && (
        <>
          <span>
            {rowName} {frames ? frame + 1 : 0}/{frames} {playing ? "▶" : "❚❚"}
          </span>
          <span>{fps} fps</span>
        </>
      )}
      <div className="flex-1" />
      {sprite && (
        <>
          <span>cell {sprite.cell.join("×")}</span>
          <span>anchor {sprite.anchor.join(",")}</span>
          <span>{zoom}×</span>
        </>
      )}
      <span>127.0.0.1 · 本地</span>
    </footer>
  );
}
