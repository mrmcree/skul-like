import { useEffect, useMemo, useRef, type ReactNode } from "react";
import {
  Columns2, Copy, Crosshair, Download, Film, FlipHorizontal2, Grid3x3, ImageOff, Layers, MousePointerClick, Pause, Play,
  SkipBack, SkipForward, TriangleAlert, Upload, ZoomIn, ZoomOut,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  ContextMenu, ContextMenuContent, ContextMenuItem, ContextMenuSeparator, ContextMenuShortcut, ContextMenuTrigger,
} from "@/components/ui/context-menu";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { usePlayback } from "@/hooks/usePlayback";
import { BACKGROUNDS, drawSprite, ZOOMS, type Background, type ViewOptions } from "@/lib/sprite";
import type { AssetInfo, EnvOutput, Issue, SpriteConfig } from "@/lib/types";
import { cn } from "@/lib/utils";
import { EmptyState, Tip } from "./common";

export type ExportMode = "copy" | "download";

interface Props {
  info: AssetInfo | null;
  sheet: HTMLImageElement | null;
  row: number;
  frame: number;
  frames: number;
  playing: boolean;
  fps: number;
  view: ViewOptions;
  issues: Issue[];
  compareRow: number;
  onPlaying: (v: boolean) => void;
  onFps: (v: number) => void;
  onView: (v: ViewOptions) => void;
  onStep: (delta: number) => void;
  onGoRaw: () => void;
  onCompareRow: (row: number) => void;
  onExportFrame: (mode: ExportMode, row: number, frame: number) => void;
  onExportStrip: (row: number) => void;
}

export function Viewport(props: Props) {
  const { info } = props;
  if (!info) {
    return <EmptyState icon={MousePointerClick} title="选择一个素材" text="从左侧列表选择素材，或点 + 新建一个。按 Ctrl+K 打开命令面板。" />;
  }
  if (info.kind === "env" && info.outputs?.length) return <EnvGallery outputs={info.outputs} />;
  if (info.kind === "sprite" && info.sheet_url) return <SpriteStage {...props} />;
  return (
    <EmptyState
      icon={ImageOff}
      title="还没有处理结果"
      text={info.kind ? "上传原图后点右上角「处理」。" : "先上传原图，并在检查器的「配置」里保存一份配置。"}
      action={
        <Button size="sm" variant="outline" onClick={props.onGoRaw}>
          <Upload />
          上传原图
        </Button>
      }
    />
  );
}

function ToolToggle({ tip, pressed, onClick, children }: { tip: string; pressed?: boolean; onClick: () => void; children: ReactNode }) {
  return (
    <Tip tip={tip}>
      <Button
        variant="ghost"
        size="icon-sm"
        onClick={onClick}
        aria-pressed={pressed}
        className={cn(pressed && "bg-primary/15 text-primary hover:bg-primary/20 hover:text-primary")}
      >
        {children}
      </Button>
    </Tip>
  );
}

interface CanvasProps {
  sheet: HTMLImageElement | null;
  cfg: SpriteConfig;
  row: number;
  frame: number;
  frames: number;
  view: ViewOptions;
}

function SpriteCanvas({ sheet, cfg, row, frame, frames, view }: CanvasProps) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    if (ref.current) drawSprite(ref.current, sheet, cfg.cell, cfg.anchor, row, frame, frames, view);
  }, [sheet, cfg, row, frame, frames, view]);
  return <canvas ref={ref} className="pixelated shadow-2xl shadow-black/60 ring-1 ring-white/10" />;
}

function SpriteStage(p: Props) {
  const { info, sheet, row, frame, frames, playing, fps, view, issues, compareRow } = p;
  const { onPlaying, onFps, onView, onStep, onCompareRow, onExportFrame, onExportStrip } = p;
  const cfg = info!.config as SpriteConfig;
  const stageRef = useRef<HTMLDivElement>(null);
  const viewRef = useRef(view);
  viewRef.current = view;

  // Second animation for side-by-side compare; shares FPS and play/pause.
  const cRow = Math.min(Math.max(0, compareRow), cfg.strips.length - 1);
  const cFrames = view.compare ? (cfg.strips[cRow]?.frames ?? 0) : 0;
  const [cFrame] = usePlayback(cFrames, fps, playing);

  const zoomBy = (dir: number) => {
    const v = viewRef.current;
    const i = ZOOMS.indexOf(v.zoom);
    const next = ZOOMS[Math.min(ZOOMS.length - 1, Math.max(0, (i < 0 ? 3 : i) + dir))];
    if (next !== v.zoom) onView({ ...v, zoom: next });
  };

  // Ctrl + wheel zooms (non-passive so the browser page zoom doesn't kick in).
  useEffect(() => {
    const el = stageRef.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => {
      if (!e.ctrlKey && !e.metaKey) return;
      e.preventDefault();
      zoomBy(e.deltaY < 0 ? 1 : -1);
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  });

  const set = (patch: Partial<ViewOptions>) => onView({ ...view, ...patch });
  const strip = cfg.strips[row];

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex h-9 shrink-0 items-center gap-1 border-b bg-card px-2">
        <Tip tip="上一帧 (←)">
          <Button variant="ghost" size="icon-sm" onClick={() => onStep(-1)}>
            <SkipBack />
          </Button>
        </Tip>
        <Tip tip="播放 / 暂停 (空格)">
          <Button variant="secondary" size="icon-sm" onClick={() => onPlaying(!playing)}>
            {playing ? <Pause /> : <Play />}
          </Button>
        </Tip>
        <Tip tip="下一帧 (→)">
          <Button variant="ghost" size="icon-sm" onClick={() => onStep(1)}>
            <SkipForward />
          </Button>
        </Tip>
        <label className="ml-1 flex items-center gap-1.5 text-[11px] text-muted-foreground">
          FPS
          <Input
            type="number"
            min={1}
            max={60}
            value={fps}
            onChange={(e) => onFps(Math.min(60, Math.max(1, Number(e.target.value) || 10)))}
            className="h-6 w-12 px-1.5 font-mono"
          />
        </label>
        <Separator orientation="vertical" className="mx-1 h-4" />
        <Tip tip="缩小 (Ctrl+滚轮)">
          <Button variant="ghost" size="icon-sm" onClick={() => zoomBy(-1)}>
            <ZoomOut />
          </Button>
        </Tip>
        <span className="w-8 text-center font-mono text-[11px]">{view.zoom}×</span>
        <Tip tip="放大 (Ctrl+滚轮)">
          <Button variant="ghost" size="icon-sm" onClick={() => zoomBy(1)}>
            <ZoomIn />
          </Button>
        </Tip>
        <Separator orientation="vertical" className="mx-1 h-4" />
        <ToolToggle tip="洋葱皮：叠加上一帧" pressed={view.onion} onClick={() => set({ onion: !view.onion })}>
          <Layers />
        </ToolToggle>
        <ToolToggle tip="显示锚点" pressed={view.anchor} onClick={() => set({ anchor: !view.anchor })}>
          <Crosshair />
        </ToolToggle>
        <ToolToggle tip="镜像" pressed={view.flip} onClick={() => set({ flip: !view.flip })}>
          <FlipHorizontal2 />
        </ToolToggle>
        <ToolToggle tip="像素网格（4× 以上）" pressed={view.grid} onClick={() => set({ grid: !view.grid })}>
          <Grid3x3 />
        </ToolToggle>
        <Separator orientation="vertical" className="mx-1 h-4" />
        <ToolToggle tip="并排对比两个动画" pressed={view.compare} onClick={() => set({ compare: !view.compare })}>
          <Columns2 />
        </ToolToggle>
        <div className="flex-1" />
        <Select value={view.background} onValueChange={(v) => set({ background: v as Background })}>
          <SelectTrigger className="h-6 w-24">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {Object.entries(BACKGROUNDS).map(([k, label]) => (
              <SelectItem key={k} value={k}>
                {label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <ContextMenu>
        <ContextMenuTrigger asChild>
          <div ref={stageRef} className="stage-dots relative min-h-0 flex-1 overflow-auto">
            <div className="flex min-h-full min-w-full w-max items-center justify-center gap-12 p-10">
              <figure className="flex flex-col items-center gap-2">
                <SpriteCanvas sheet={sheet} cfg={cfg} row={row} frame={frame} frames={frames} view={view} />
                {view.compare && (
                  <figcaption className="flex h-6 items-center font-mono text-[11px] text-muted-foreground">
                    {strip?.name} · {frames ? frame + 1 : 0}/{frames}
                  </figcaption>
                )}
              </figure>
              {view.compare && (
                <figure className="flex flex-col items-center gap-2">
                  <SpriteCanvas sheet={sheet} cfg={cfg} row={cRow} frame={cFrame} frames={cFrames} view={view} />
                  <figcaption className="flex items-center gap-2 font-mono text-[11px] text-muted-foreground">
                    <Select value={String(cRow)} onValueChange={(v) => onCompareRow(Number(v))}>
                      <SelectTrigger className="h-6 w-32 font-mono">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {cfg.strips.map((s, i) => (
                          <SelectItem key={`${s.name}-${i}`} value={String(i)}>
                            {s.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {cFrames ? cFrame + 1 : 0}/{cFrames}
                  </figcaption>
                </figure>
              )}
            </div>
            {issues.length > 0 && (
              <div className="pointer-events-none absolute left-3 top-3 flex max-w-[60%] flex-col gap-1">
                {issues.map((i, n) => (
                  <div
                    key={n}
                    className={cn(
                      "flex items-center gap-1.5 rounded-md border px-2 py-1 text-[11px] backdrop-blur",
                      i.level === "error"
                        ? "border-destructive/40 bg-destructive/15 text-destructive"
                        : "border-warning/40 bg-warning/10 text-warning",
                    )}
                  >
                    <TriangleAlert className="size-3 shrink-0" />
                    {i.message}
                  </div>
                ))}
              </div>
            )}
            {!view.compare && (
              <div className="pointer-events-none absolute bottom-3 right-3 rounded-md bg-black/60 px-2 py-0.5 font-mono text-[11px] text-white/80">
                {strip?.name} · {frames ? frame + 1 : 0}/{frames}
              </div>
            )}
          </div>
        </ContextMenuTrigger>
        <ContextMenuContent>
          <ContextMenuItem onSelect={() => onExportFrame("copy", row, frame)}>
            <Copy />
            复制当前帧
            <ContextMenuShortcut>PNG</ContextMenuShortcut>
          </ContextMenuItem>
          <ContextMenuItem onSelect={() => onExportFrame("download", row, frame)}>
            <Download />
            导出当前帧
          </ContextMenuItem>
          <ContextMenuItem onSelect={() => onExportStrip(row)}>
            <Film />
            导出整条动画（横条）
          </ContextMenuItem>
          <ContextMenuSeparator />
          <ContextMenuItem onSelect={() => onPlaying(!playing)}>
            {playing ? <Pause /> : <Play />}
            {playing ? "暂停" : "播放"}
            <ContextMenuShortcut>空格</ContextMenuShortcut>
          </ContextMenuItem>
          <ContextMenuItem onSelect={() => set({ compare: !view.compare })}>
            <Columns2 />
            {view.compare ? "关闭对比" : "并排对比"}
          </ContextMenuItem>
          <ContextMenuItem onSelect={() => set({ onion: !view.onion })}>
            <Layers />
            {view.onion ? "关闭洋葱皮" : "打开洋葱皮"}
          </ContextMenuItem>
          <ContextMenuItem onSelect={() => set({ flip: !view.flip })}>
            <FlipHorizontal2 />
            {view.flip ? "取消镜像" : "镜像"}
          </ContextMenuItem>
        </ContextMenuContent>
      </ContextMenu>
    </div>
  );
}

function EnvGallery({ outputs }: { outputs: EnvOutput[] }) {
  const stamp = useMemo(() => Date.now(), [outputs]);
  return (
    <ScrollArea className="stage-dots min-h-0 flex-1">
      <div className="grid gap-3 p-4 [grid-template-columns:repeat(auto-fill,minmax(320px,1fr))]">
        {outputs.map((o) => (
          <figure key={o.name} className="overflow-hidden rounded-lg border bg-card">
            <div className="checker flex h-44 items-center justify-center p-2">
              <img src={`${o.url}?t=${stamp}`} alt={o.name} className="pixelated max-h-full max-w-full object-contain" />
            </div>
            <figcaption className="flex items-center justify-between gap-2 border-t px-3 py-2 text-xs">
              <span className="font-mono font-medium">{o.name}</span>
              <span className="truncate text-muted-foreground">
                游戏内 {o.size ? o.size.join("×") : "?"} · 纹素 {o.texels ? o.texels.join("×") : "?"}
              </span>
            </figcaption>
          </figure>
        ))}
      </div>
    </ScrollArea>
  );
}
