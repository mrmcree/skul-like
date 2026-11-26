import { useCallback, useEffect, useRef, useState } from "react";
import {
  Columns2, Copy, Crosshair, Download, Film, FlipHorizontal2, FolderOpen, Grid3x3, Keyboard, Layers, LayoutGrid,
  Palette, Pause, Play, RefreshCw, ScanSearch, Settings2, Sparkles, Upload, ZoomIn, ZoomOut, type LucideIcon,
} from "lucide-react";
import { Toaster, toast } from "sonner";
import { AssetExplorer } from "@/components/studio/AssetExplorer";
import { BottomPanel, type BottomTab } from "@/components/studio/BottomPanel";
import { CommandPalette, type Command } from "@/components/studio/CommandPalette";
import { healthOf } from "@/components/studio/common";
import { Inspector, type InspectorTab } from "@/components/studio/Inspector";
import { PromptWorkbench } from "@/components/studio/PromptWorkbench";
import { ShortcutsDialog } from "@/components/studio/ShortcutsDialog";
import { StatusBar } from "@/components/studio/StatusBar";
import { Timeline } from "@/components/studio/Timeline";
import { TopBar, type Workspace } from "@/components/studio/TopBar";
import { Viewport, type ExportMode } from "@/components/studio/Viewport";
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from "@/components/ui/resizable";
import { TooltipProvider } from "@/components/ui/tooltip";
import { useImage } from "@/hooks/useImage";
import { usePlayback } from "@/hooks/usePlayback";
import { api } from "@/lib/api";
import {
  BACKGROUNDS, copyCanvas, defaultView, downloadCanvas, frameCanvas, stripCanvas, ZOOMS, type Background, type ViewOptions,
} from "@/lib/sprite";
import type { AssetInfo, AssetSummary, Health, Issue, Kind, LogLine, QcReport, SpriteConfig } from "@/lib/types";
import { errorMessage } from "@/lib/utils";

const VIEW_KEY = "asset-studio:view";
type Toggle = "onion" | "anchor" | "flip" | "grid" | "compare";
const TOGGLES: [Toggle, string, LucideIcon][] = [
  ["onion", "洋葱皮", Layers],
  ["anchor", "锚点", Crosshair],
  ["flip", "镜像", FlipHorizontal2],
  ["grid", "像素网格", Grid3x3],
  ["compare", "并排对比", Columns2],
];

function loadView(): ViewOptions {
  try {
    return { ...defaultView, ...JSON.parse(localStorage.getItem(VIEW_KEY) ?? "{}") };
  } catch {
    return defaultView;
  }
}

export default function App() {
  const [workspace, setWorkspace] = useState<Workspace>("assets");
  const [online, setOnline] = useState<boolean | null>(null);
  const [assets, setAssets] = useState<AssetSummary[]>([]);
  const [current, setCurrent] = useState<string | null>(null);
  const [info, setInfo] = useState<AssetInfo | null>(null);
  const [qc, setQc] = useState<QcReport | null>(null);
  const [health, setHealth] = useState<Record<string, Health>>({});
  const [log, setLog] = useState<LogLine[]>([]);
  const [processing, setProcessing] = useState(false);
  const [inspectorTab, setInspectorTab] = useState<InspectorTab>("props");
  const [bottomTab, setBottomTab] = useState<BottomTab>("issues");
  const [row, setRowState] = useState(0);
  const [playing, setPlaying] = useState(true);
  const [fps, setFps] = useState(10);
  const [view, setView] = useState<ViewOptions>(loadView);
  const [compareRow, setCompareRow] = useState(1);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);

  const sprite = info?.kind === "sprite" ? (info.config as SpriteConfig) : null;
  const strips = sprite?.strips ?? [];
  const frames = strips[row]?.frames ?? 0;
  const [frame, setFrame] = usePlayback(frames, fps, playing);
  const sheet = useImage(sprite && info?.sheet_url ? `${info.sheet_url}?t=${info.sheet_mtime ?? 0}` : null);
  const hasSheet = Boolean(sprite && info?.sheet_url);
  const currentRef = useRef(current);
  currentRef.current = current;

  useEffect(() => localStorage.setItem(VIEW_KEY, JSON.stringify(view)), [view]);

  const addLog = useCallback((text: string, level: LogLine["level"] = "info") => {
    const time = new Date().toLocaleTimeString("zh-CN", { hour12: false });
    setLog((l) => [...l, ...text.split("\n").map((t) => ({ time, level, text: t }))].slice(-2000));
  }, []);

  const markHealth = useCallback((name: string, report: QcReport | null) => {
    const h = healthOf(report);
    setHealth((m) => {
      const next = { ...m };
      if (h) next[name] = h;
      else delete next[name];
      return next;
    });
  }, []);

  const setRow = useCallback(
    (r: number) => {
      setRowState(Math.max(0, r));
      setFrame(0);
    },
    [setFrame],
  );

  const runQc = useCallback(
    async (name: string, kind: Kind | null) => {
      const report = kind ? await api.qc(name) : null;
      setQc(report);
      markHealth(name, report);
      return report;
    },
    [markHealth],
  );

  const openAsset = useCallback(
    async (name: string) => {
      setCurrent(name);
      try {
        const data = await api.asset(name);
        setInfo(data);
        const count = data.kind === "sprite" ? (data.config as SpriteConfig).strips.length : 0;
        setRowState((r) => Math.min(r, Math.max(0, count - 1)));
        setFrame(0);
        await runQc(name, data.kind);
      } catch (e) {
        toast.error(errorMessage(e));
      }
    },
    [runQc, setFrame],
  );

  const loadAssets = useCallback(
    async (select?: string | null) => {
      try {
        const list = await api.assets();
        setAssets(list);
        setOnline(true);
        if (select) await openAsset(select);
        return list;
      } catch (e) {
        setOnline(false);
        toast.error(errorMessage(e));
        return [];
      }
    },
    [openAsset],
  );

  // First load: list assets, then QC each one in the background for the health dots.
  const started = useRef(false);
  useEffect(() => {
    if (started.current) return;
    started.current = true;
    void (async () => {
      const list = await loadAssets();
      for (const a of list) {
        if (!a.kind) continue;
        try {
          markHealth(a.name, await api.qc(a.name));
        } catch {
          /* shown when opened */
        }
      }
    })();
  }, [loadAssets, markHealth]);

  const newAsset = (name: string) => {
    setWorkspace("assets");
    setCurrent(name);
    setInfo({ name, kind: null, config: null });
    setQc(null);
    setInspectorTab("raw");
  };

  const process = async (target: string | null = current) => {
    if (!target || processing) return;
    const kind = target === current ? info?.kind : assets.find((a) => a.name === target)?.kind;
    if (!kind) {
      toast.error("还没有配置文件，先在「配置」里保存一份");
      return;
    }
    setProcessing(true);
    setBottomTab("log");
    addLog(`▶ 开始处理 ${target}（可能要 1–2 分钟）`);
    try {
      const res = await api.process(target);
      addLog(res.log || "(没有输出)", res.ok ? "info" : "error");
      addLog(res.ok ? `✓ ${target} 处理完成` : `✗ ${target} 处理失败`, res.ok ? "ok" : "error");
      markHealth(target, res.qc);
      if (currentRef.current === target) {
        setInfo(await api.asset(target));
        setQc(res.qc);
      }
      if (res.ok) {
        const n = res.qc.errors + res.qc.warnings;
        toast.success(`${target} 处理完成`, { description: n ? `质检发现 ${n} 个问题` : "质检通过" });
        if (n) setBottomTab("issues");
      } else {
        toast.error(`${target} 处理失败，查看输出日志`);
      }
    } catch (e) {
      addLog(errorMessage(e), "error");
      toast.error(errorMessage(e));
    } finally {
      setProcessing(false);
    }
  };
  const processRef = useRef(process);
  processRef.current = process;

  const recheck = async () => {
    if (!current || !info) return;
    try {
      const report = await runQc(current, info.kind);
      setBottomTab("issues");
      if (report) toast.message(`质检：${report.errors} 错误 · ${report.warnings} 警告`);
    } catch (e) {
      toast.error(errorMessage(e));
    }
  };

  const saveConfig = async (kind: Kind, config: unknown) => {
    if (!current) return;
    try {
      await api.saveConfig(current, kind, config);
      toast.success("配置已保存");
      addLog(`已保存 ${current} 的 ${kind === "sprite" ? "sprite.json" : "env.json"}`, "ok");
      await loadAssets(current);
    } catch (e) {
      toast.error(errorMessage(e));
    }
  };

  const upload = async (files: File[]) => {
    if (!current || !files.length) return;
    let ok = 0;
    for (const file of files) {
      try {
        await api.upload(current, file);
        addLog(`已上传 ${file.name}`, "ok");
        ok++;
      } catch (e) {
        addLog(`上传失败 ${file.name}：${errorMessage(e)}`, "error");
        toast.error(`${file.name}：${errorMessage(e)}`);
      }
    }
    if (ok) toast.success(`已上传 ${ok} 张图片`);
    await loadAssets(current);
    setInspectorTab("raw");
  };

  const step = useCallback(
    (delta: number) => {
      if (!frames) return;
      setPlaying(false);
      setFrame((f) => (f + delta + frames) % frames);
    },
    [frames, setFrame],
  );

  const jumpTo = (issue: Issue) => {
    if (issue.row === null) return;
    setRowState(issue.row);
    if (issue.frame !== null) {
      setPlaying(false);
      setFrame(issue.frame);
    } else {
      setFrame(0);
    }
  };

  const issuesFor = (r: number, f?: number) =>
    (qc?.issues ?? []).filter((i) => i.row === r && (f === undefined || i.frame === f || i.frame === null));

  // ---------- copy / export ----------
  const copyText = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      toast.success("已复制", { description: text });
    } catch (e) {
      toast.error(errorMessage(e));
    }
  };

  const exportFrame = async (mode: ExportMode, r = row, f = frame) => {
    if (!sheet || !sprite || !current) return;
    const c = frameCanvas(sheet, sprite.cell, r, f, 1, view.flip);
    const name = `${current}_${strips[r]?.name ?? r}_${f + 1}.png`;
    try {
      if (mode === "copy") {
        await copyCanvas(c);
        toast.success("帧已复制到剪贴板", { description: name });
      } else {
        await downloadCanvas(c, name);
      }
    } catch (e) {
      toast.error(errorMessage(e));
    }
  };

  const exportStrip = async (r = row) => {
    if (!sheet || !sprite || !current) return;
    const n = strips[r]?.frames ?? 0;
    if (!n) return;
    try {
      await downloadCanvas(stripCanvas(sheet, sprite.cell, r, n, 1), `${current}_${strips[r].name}_strip.png`);
    } catch (e) {
      toast.error(errorMessage(e));
    }
  };

  const compareWith = (r: number) => {
    setCompareRow(r);
    setView((v) => ({ ...v, compare: true }));
  };
  const toggle = (k: Toggle) => setView((v) => ({ ...v, [k]: !v[k] }));
  const zoomBy = (dir: number) =>
    setView((v) => {
      const i = ZOOMS.indexOf(v.zoom);
      return { ...v, zoom: ZOOMS[Math.min(ZOOMS.length - 1, Math.max(0, (i < 0 ? 3 : i) + dir))] };
    });

  // ---------- command palette ----------
  const commands: Command[] = [];
  const add = (...c: Command[]) => commands.push(...c);
  const inAssets = (fn: () => void) => () => {
    setWorkspace("assets");
    fn();
  };
  add(
    { id: "ws-assets", group: "工作区", label: "切换到素材", icon: LayoutGrid, run: () => setWorkspace("assets") },
    { id: "ws-prompts", group: "工作区", label: "切换到提示词生成", icon: Sparkles, keywords: "prompt 即梦 ai", run: () => setWorkspace("prompts") },
    { id: "process", group: "当前素材", label: "处理", hint: "Ctrl+Enter", icon: Play, disabled: !info?.kind || processing, run: () => void process() },
    { id: "qc", group: "当前素材", label: "重新质检", icon: ScanSearch, disabled: !info?.kind, run: () => void recheck() },
    { id: "upload", group: "当前素材", label: "上传原图", icon: Upload, disabled: !current, run: inAssets(() => setInspectorTab("raw")) },
    { id: "config", group: "当前素材", label: "编辑配置", icon: Settings2, disabled: !current, run: inAssets(() => setInspectorTab("config")) },
    { id: "copy-name", group: "当前素材", label: "复制素材名", icon: Copy, disabled: !current, run: () => current && void copyText(current) },
    { id: "refresh", group: "当前素材", label: "刷新素材列表", icon: RefreshCw, run: () => void loadAssets(current) },
  );
  if (hasSheet) {
    add(
      { id: "play", group: "播放", label: playing ? "暂停" : "播放", hint: "空格", icon: playing ? Pause : Play, run: () => setPlaying((p) => !p) },
      { id: "zoom-in", group: "播放", label: "放大", hint: "Ctrl+滚轮", icon: ZoomIn, run: () => zoomBy(1) },
      { id: "zoom-out", group: "播放", label: "缩小", hint: "Ctrl+滚轮", icon: ZoomOut, run: () => zoomBy(-1) },
      ...TOGGLES.map(([k, label, icon]) => ({
        id: `view-${k}`, group: "视图", label: `${view[k] ? "关闭" : "打开"}${label}`, icon, run: inAssets(() => toggle(k)),
      })),
      ...Object.entries(BACKGROUNDS).map(([k, label]) => ({
        id: `bg-${k}`, group: "视图", label: `背景：${label}`, icon: Palette, run: () => setView((v) => ({ ...v, background: k as Background })),
      })),
      { id: "export-copy", group: "导出", label: "复制当前帧 (PNG)", icon: Copy, run: () => void exportFrame("copy") },
      { id: "export-frame", group: "导出", label: "导出当前帧 PNG", icon: Download, run: () => void exportFrame("download") },
      { id: "export-strip", group: "导出", label: "导出当前动画横条 PNG", icon: Film, keywords: "strip", run: () => void exportStrip() },
      ...strips.map((s, i) => ({
        id: `row-${i}`, group: "跳到动画", label: s.name, hint: `${s.frames} 帧`, icon: Film, run: inAssets(() => setRow(i)),
      })),
    );
  }
  add(
    ...assets.map((a) => ({
      id: `open-${a.name}`, group: "打开素材", label: a.name, keywords: a.kind ?? "", icon: FolderOpen,
      run: inAssets(() => void openAsset(a.name)),
    })),
    { id: "help", group: "帮助", label: "键盘快捷键", hint: "?", icon: Keyboard, run: () => setHelpOpen(true) },
  );

  // ---------- keyboard ----------
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPaletteOpen((o) => !o);
        return;
      }
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        void processRef.current();
        return;
      }
      const t = e.target as HTMLElement;
      if (t.closest("input, textarea, select, [contenteditable], [role=combobox], [role=dialog], [role=menu]")) return;
      if (e.key === "?") {
        e.preventDefault();
        setHelpOpen(true);
        return;
      }
      if (workspace !== "assets" || !hasSheet) return;
      if (e.key === " ") {
        e.preventDefault();
        setPlaying((p) => !p);
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        step(-1);
      } else if (e.key === "ArrowRight") {
        e.preventDefault();
        step(1);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setRow(Math.max(0, row - 1));
      } else if (e.key === "ArrowDown") {
        e.preventDefault();
        setRow(Math.min(strips.length - 1, row + 1));
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [workspace, hasSheet, step, setRow, row, strips.length]);

  const images = assets.find((a) => a.name === current)?.raw_images ?? [];

  return (
    <TooltipProvider delayDuration={300}>
      <div className="flex h-full flex-col">
        <TopBar
          workspace={workspace}
          onWorkspace={setWorkspace}
          current={current}
          kind={info?.kind ?? null}
          qc={qc}
          processing={processing}
          onProcess={() => void process()}
          onQc={() => void recheck()}
          onPalette={() => setPaletteOpen(true)}
        />
        <div className="min-h-0 flex-1">
          {workspace === "assets" ? (
            <ResizablePanelGroup direction="horizontal" autoSaveId="asset-studio:h">
              <ResizablePanel defaultSize={16} minSize={11} maxSize={30}>
                <AssetExplorer
                  assets={assets}
                  current={current}
                  health={health}
                  processing={processing}
                  onOpen={(n) => void openAsset(n)}
                  onNew={newAsset}
                  onRefresh={() => void loadAssets(current)}
                  onProcess={(n) => void process(n)}
                  onShowRaw={(n) => {
                    void openAsset(n);
                    setInspectorTab("raw");
                  }}
                  onCopy={(t) => void copyText(t)}
                />
              </ResizablePanel>
              <ResizableHandle />
              <ResizablePanel defaultSize={60} minSize={30}>
                <ResizablePanelGroup direction="vertical" autoSaveId="asset-studio:v">
                  <ResizablePanel defaultSize={74} minSize={30}>
                    <div className="flex h-full flex-col">
                      <Viewport
                        info={info}
                        sheet={sheet}
                        row={row}
                        frame={frame}
                        frames={frames}
                        playing={playing}
                        fps={fps}
                        view={view}
                        issues={issuesFor(row, frame)}
                        compareRow={compareRow}
                        onPlaying={setPlaying}
                        onFps={setFps}
                        onView={setView}
                        onStep={step}
                        onGoRaw={() => setInspectorTab("raw")}
                        onCompareRow={setCompareRow}
                        onExportFrame={(m, r, f) => void exportFrame(m, r, f)}
                        onExportStrip={(r) => void exportStrip(r)}
                      />
                      {sprite && hasSheet && (
                        <Timeline
                          strips={strips}
                          sheet={sheet}
                          cell={sprite.cell}
                          row={row}
                          frame={frame}
                          issuesFor={issuesFor}
                          onRow={setRow}
                          onFrame={(f) => {
                            setPlaying(false);
                            setFrame(f);
                          }}
                          onCompare={compareWith}
                          onExportFrame={(m, r, f) => void exportFrame(m, r, f)}
                          onExportStrip={(r) => void exportStrip(r)}
                          onCopy={(t) => void copyText(t)}
                        />
                      )}
                    </div>
                  </ResizablePanel>
                  <ResizableHandle />
                  <ResizablePanel defaultSize={26} minSize={8}>
                    <BottomPanel
                      tab={bottomTab}
                      onTab={setBottomTab}
                      qc={qc}
                      strips={strips}
                      log={log}
                      onJump={jumpTo}
                      onClearLog={() => setLog([])}
                    />
                  </ResizablePanel>
                </ResizablePanelGroup>
              </ResizablePanel>
              <ResizableHandle />
              <ResizablePanel defaultSize={24} minSize={16} maxSize={42}>
                <Inspector
                  info={info}
                  images={images}
                  tab={inspectorTab}
                  onTab={setInspectorTab}
                  qc={qc}
                  onSave={saveConfig}
                  onUpload={(f) => void upload(f)}
                />
              </ResizablePanel>
            </ResizablePanelGroup>
          ) : (
            <PromptWorkbench
              onSaved={(name) => {
                setWorkspace("assets");
                setInspectorTab("raw");
                void loadAssets(name);
              }}
            />
          )}
        </div>
        <StatusBar
          online={online}
          info={info}
          rowName={strips[row]?.name}
          frame={frame}
          frames={frames}
          zoom={view.zoom}
          fps={fps}
          playing={playing}
        />
      </div>
      <CommandPalette open={paletteOpen} onOpenChange={setPaletteOpen} commands={commands} />
      <ShortcutsDialog open={helpOpen} onOpenChange={setHelpOpen} />
      <Toaster theme="dark" position="bottom-right" richColors closeButton />
    </TooltipProvider>
  );
}
