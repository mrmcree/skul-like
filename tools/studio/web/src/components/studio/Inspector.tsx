import { useEffect, useMemo, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { CircleCheck, CircleX, CloudUpload, Save, WandSparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { AssetInfo, EnvConfig, Kind, QcReport, SpriteConfig } from "@/lib/types";
import { cn } from "@/lib/utils";
import { KindBadge, PanelHeader, QcSummary, Tip } from "./common";

export type InspectorTab = "props" | "config" | "raw";

interface Props {
  info: AssetInfo | null;
  images: string[];
  tab: InspectorTab;
  onTab: (t: InspectorTab) => void;
  qc: QcReport | null;
  onSave: (kind: Kind, config: unknown) => Promise<void>;
  onUpload: (files: File[]) => void;
}

export function Inspector({ info, images, tab, onTab, qc, onSave, onUpload }: Props) {
  if (!info) {
    return (
      <div className="flex h-full flex-col bg-card">
        <PanelHeader title="检查器" />
        <p className="p-4 text-xs text-muted-foreground">未选择素材</p>
      </div>
    );
  }
  return (
    <Tabs value={tab} onValueChange={(v) => onTab(v as InspectorTab)} className="h-full bg-card">
      <div className="flex h-8 shrink-0 items-center border-b px-1">
        <TabsList className="h-7 bg-transparent p-0">
          <TabsTrigger value="props">属性</TabsTrigger>
          <TabsTrigger value="config">配置</TabsTrigger>
          <TabsTrigger value="raw">
            原图<span className="text-[10px] opacity-60">{images.length}</span>
          </TabsTrigger>
        </TabsList>
      </div>
      <TabsContent value="props" className="min-h-0 flex-1">
        <ScrollArea className="h-full">
          <Properties info={info} qc={qc} images={images.length} />
        </ScrollArea>
      </TabsContent>
      <TabsContent value="config" className="min-h-0 flex-1">
        <ConfigEditor key={info.name} info={info} onSave={onSave} />
      </TabsContent>
      <TabsContent value="raw" className="min-h-0 flex-1">
        <RawImages name={info.name} images={images} onUpload={onUpload} />
      </TabsContent>
    </Tabs>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="border-b px-3 py-3">
      <h4 className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">{title}</h4>
      <div className="space-y-1.5">{children}</div>
    </section>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3 text-xs">
      <span className="shrink-0 text-muted-foreground">{label}</span>
      <span className="truncate text-right font-mono">{children}</span>
    </div>
  );
}

function Properties({ info, qc, images }: { info: AssetInfo; qc: QcReport | null; images: number }) {
  const sprite = info.kind === "sprite" ? (info.config as SpriteConfig) : null;
  const env = info.kind === "env" ? (info.config as EnvConfig) : null;
  return (
    <div>
      <Section title="素材">
        <Field label="名称">{info.name}</Field>
        <Field label="类型">
          <KindBadge kind={info.kind} />
        </Field>
        <Field label="原图">{images} 张</Field>
        <Field label="质检">{qc ? <QcSummary qc={qc} /> : "—"}</Field>
      </Section>
      {sprite && (
        <>
          <Section title="精灵图">
            <Field label="格子">{sprite.cell.join(" × ")}</Field>
            <Field label="锚点">{sprite.anchor.join(", ")}</Field>
            <Field label="游戏内高度">{sprite.target_height} 纹素</Field>
            <Field label="调色板">{sprite.palette_colors ?? "—"}</Field>
            <Field label="图集尺寸">
              {sprite.cell[0] * Math.max(...sprite.strips.map((s) => s.frames))} × {sprite.cell[1] * sprite.strips.length}
            </Field>
            <Field label="动画 / 总帧数">
              {sprite.strips.length} / {sprite.strips.reduce((n, s) => n + s.frames, 0)}
            </Field>
          </Section>
          <Section title="动画">
            {sprite.strips.map((s, i) => (
              <div key={`${s.name}-${i}`} className="flex items-center gap-2 text-xs">
                <span className="w-5 text-right font-mono text-[10px] text-muted-foreground">{i}</span>
                <span className="flex-1 truncate font-mono">{s.name}</span>
                <span className="truncate font-mono text-[10px] text-muted-foreground">
                  {s.file}
                  {s.row !== undefined ? `:${s.row}` : ""}
                </span>
                <span className="w-8 text-right font-mono">{s.frames}f</span>
              </div>
            ))}
          </Section>
        </>
      )}
      {env && (
        <Section title="环境">
          <Field label="输出目录">{env.out_dir}</Field>
          <Field label="视差层">{env.layers?.length ?? 0}</Field>
          <Field label="地面">{env.ground?.name ?? "—"}</Field>
          <Field label="输出图片">{info.outputs?.length ?? 0}</Field>
        </Section>
      )}
    </div>
  );
}

type Parsed = { ok: true; value: unknown } | { ok: false; error: string };

function ConfigEditor({ info, onSave }: { info: AssetInfo; onSave: Props["onSave"] }) {
  const initial = info.config ? JSON.stringify(info.config, null, 2) : "";
  const initialKind: Kind = info.kind ?? "sprite";
  const [text, setText] = useState(initial);
  const [kind, setKind] = useState<Kind>(initialKind);
  const [saving, setSaving] = useState(false);
  const ref = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    setText(initial);
    setKind(initialKind);
  }, [initial, initialKind]);

  const parsed: Parsed = useMemo(() => {
    if (!text.trim()) return { ok: false, error: "空配置" };
    try {
      return { ok: true, value: JSON.parse(text) };
    } catch (e) {
      return { ok: false, error: (e as Error).message };
    }
  }, [text]);
  const dirty = text !== initial || kind !== initialKind;

  const save = async () => {
    if (!parsed.ok || saving) return;
    setSaving(true);
    try {
      await onSave(kind, parsed.value);
    } finally {
      setSaving(false);
    }
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") {
      e.preventDefault();
      void save();
    } else if (e.key === "Tab") {
      e.preventDefault();
      const el = e.currentTarget;
      const start = el.selectionStart;
      const next = text.slice(0, start) + "  " + text.slice(el.selectionEnd);
      setText(next);
      requestAnimationFrame(() => {
        el.selectionStart = el.selectionEnd = start + 2;
      });
    }
  };

  return (
    <div className="flex h-full flex-col">
      <div className="flex shrink-0 items-center gap-1.5 border-b p-2">
        <Select value={kind} onValueChange={(v) => setKind(v as Kind)}>
          <SelectTrigger className="h-7 flex-1">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="sprite">角色 / 敌人 · sprite.json</SelectItem>
            <SelectItem value="env">关卡环境 · env.json</SelectItem>
          </SelectContent>
        </Select>
        <Tip tip="格式化 JSON">
          <Button
            variant="ghost"
            size="icon-sm"
            disabled={!parsed.ok}
            onClick={() => parsed.ok && setText(JSON.stringify(parsed.value, null, 2))}
          >
            <WandSparkles />
          </Button>
        </Tip>
        <Button size="sm" disabled={!parsed.ok || !dirty || saving} onClick={save}>
          <Save />
          保存
        </Button>
      </div>
      <textarea
        ref={ref}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={onKeyDown}
        spellCheck={false}
        placeholder="还没有配置。可以在「提示词」里一键生成，或手动粘贴。"
        className="min-h-0 flex-1 resize-none bg-background p-3 font-mono text-[12px] leading-relaxed outline-none placeholder:text-muted-foreground/60"
      />
      <div
        className={cn(
          "flex h-6 shrink-0 items-center gap-1.5 border-t px-3 text-[11px]",
          parsed.ok ? "text-muted-foreground" : "text-destructive",
        )}
      >
        {parsed.ok ? <CircleCheck className="size-3 text-success" /> : <CircleX className="size-3" />}
        <span className="truncate">{parsed.ok ? `JSON 有效${dirty ? " · 未保存" : ""}` : parsed.error}</span>
        <span className="ml-auto shrink-0 text-muted-foreground">Ctrl+S 保存</span>
      </div>
    </div>
  );
}

function RawImages({ name, images, onUpload }: { name: string; images: string[]; onUpload: (f: File[]) => void }) {
  const [over, setOver] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const stamp = useMemo(() => Date.now(), [images]);
  const url = (file: string) => `/files/raw/${encodeURIComponent(name)}/${encodeURIComponent(file)}?t=${stamp}`;

  return (
    <div className="flex h-full flex-col">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setOver(true);
        }}
        onDragLeave={() => setOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setOver(false);
          onUpload([...e.dataTransfer.files]);
        }}
        onClick={() => inputRef.current?.click()}
        className={cn(
          "m-2 flex cursor-pointer flex-col items-center justify-center gap-1 rounded-lg border border-dashed px-3 py-5 text-center text-xs text-muted-foreground transition-colors hover:border-primary/60 hover:bg-primary/5",
          over && "border-primary bg-primary/10 text-foreground",
        )}
      >
        <CloudUpload className="size-5" />
        <span>把即梦生成的图片拖到这里，或点击选择</span>
        <span className="text-[10px] opacity-70">png / jpg / webp · 最大 40 MB · 同名会覆盖</span>
        <input
          ref={inputRef}
          type="file"
          hidden
          multiple
          accept=".png,.jpg,.jpeg,.webp"
          onChange={(e) => {
            if (e.target.files) onUpload([...e.target.files]);
            e.target.value = "";
          }}
        />
      </div>
      <ScrollArea className="min-h-0 flex-1">
        <div className="grid grid-cols-2 gap-2 p-2 pt-0">
          {images.map((f) => (
            <button
              key={f}
              onClick={() => setPreview(f)}
              className="overflow-hidden rounded-md border bg-background text-left transition-colors hover:border-primary/60"
            >
              <div className="checker aspect-square">
                <img src={url(f)} alt={f} loading="lazy" className="size-full object-contain" />
              </div>
              <div className="truncate border-t px-1.5 py-1 font-mono text-[10px] text-muted-foreground">{f}</div>
            </button>
          ))}
        </div>
        {images.length === 0 && <p className="p-6 text-center text-xs text-muted-foreground">还没有原图</p>}
      </ScrollArea>
      <Dialog open={preview !== null} onOpenChange={(o) => !o && setPreview(null)}>
        <DialogContent className="max-w-[90vw]">
          <DialogTitle className="font-mono">{preview}</DialogTitle>
          <div className="checker max-h-[78vh] overflow-auto rounded-md">
            {preview && <img src={url(preview)} alt={preview} className="mx-auto" />}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
