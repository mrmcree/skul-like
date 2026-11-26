import { useEffect, useState, type ReactNode } from "react";
import { Bot, Check, Copy, Loader2, Mountain, PersonStanding, Plus, Save, Sparkles, Undo2, WandSparkles, X } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";
import type { Action, LlmStatus, PromptItem, PromptRequest, PromptResult } from "@/lib/types";
import { cn, errorMessage, NAME_RE } from "@/lib/utils";
import { PanelHeader, Tip } from "./common";

const DEFAULT_STYLE = "16位复古游戏风格，清晰像素颗粒，黑色描边";
const MAX_ROWS = 5;

type PromptKind = PromptRequest["kind"];

function Label({ title, hint, children }: { title: string; hint?: string; children: ReactNode }) {
  return (
    <label className="block space-y-1.5">
      <span className="flex items-baseline justify-between text-xs font-medium">
        {title}
        {hint && <span className="text-[10px] font-normal text-muted-foreground">{hint}</span>}
      </span>
      {children}
    </label>
  );
}

function CopyButton({ text }: { text: string }) {
  const [done, setDone] = useState(false);
  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={async () => {
        await navigator.clipboard.writeText(text);
        setDone(true);
        setTimeout(() => setDone(false), 1500);
      }}
    >
      {done ? <Check className="text-success" /> : <Copy />}
      {done ? "已复制" : "复制"}
    </Button>
  );
}

export function PromptWorkbench({ onSaved }: { onSaved: (name: string) => void }) {
  const [kind, setKind] = useState<PromptKind>("character");
  const [presets, setPresets] = useState<Record<string, Action[]>>({});
  const [preset, setPreset] = useState("");
  const [subject, setSubject] = useState("");
  const [actions, setActions] = useState<Action[]>([]);
  const [height, setHeight] = useState(60);
  const [theme, setTheme] = useState("");
  const [items, setItems] = useState("");
  const [style, setStyle] = useState(DEFAULT_STYLE);
  const [result, setResult] = useState<PromptResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [assetName, setAssetName] = useState("");
  const [llm, setLlm] = useState<LlmStatus | null>(null);
  const [model, setModel] = useState("");
  const [models, setModels] = useState<string[]>([]);
  const [idea, setIdea] = useState("");
  const [expanding, setExpanding] = useState(false);
  const [gen, setGen] = useState(0);

  useEffect(() => {
    api
      .llmStatus()
      .then((s) => {
        setLlm(s);
        setModel(s.model);
      })
      .catch(() => setLlm({ configured: false, model: "" }));
  }, []);

  const loadModels = () => {
    if (models.length || !llm?.configured) return;
    api.llmModels().then((r) => setModels(r.models)).catch(() => {});
  };

  const expandIdea = async () => {
    if (!idea.trim()) return;
    setExpanding(true);
    try {
      const res = await api.expand(kind, idea.trim(), model.trim());
      if (kind === "character") {
        setSubject(res.subject ?? "");
      } else {
        setTheme(res.theme ?? "");
        if (res.items) setItems(res.items);
      }
      toast.success("AI 已填入描述", { description: "可以再手动改改，然后点「生成提示词」。" });
    } catch (e) {
      toast.error(errorMessage(e));
    } finally {
      setExpanding(false);
    }
  };

  const updatePrompt = (file: string, prompt: string) =>
    setResult((r) => r && { ...r, prompts: r.prompts.map((p) => (p.file === file ? { ...p, prompt } : p)) });

  useEffect(() => {
    api
      .presets()
      .then((p) => {
        setPresets(p);
        const first = Object.keys(p)[0];
        if (first) {
          setPreset(first);
          setActions(p[first]);
        }
      })
      .catch((e) => toast.error(errorMessage(e)));
  }, []);

  const valid = actions.filter((a) => a.name.trim());
  const sheets = Math.max(1, Math.ceil(valid.length / MAX_ROWS));
  const update = (i: number, patch: Partial<Action>) =>
    setActions((list) => list.map((a, n) => (n === i ? { ...a, ...patch } : a)));

  const generate = async () => {
    const body: PromptRequest =
      kind === "character"
        ? { kind, style, subject: subject.trim(), actions: valid.map((a) => ({ ...a, name: a.name.trim() })), target_height: height }
        : { kind, style, theme: theme.trim(), items: items.trim() };
    setBusy(true);
    try {
      const res = await api.prompts(body);
      setResult(res);
      setGen((g) => g + 1);
      toast.success(`生成了 ${res.prompts.length} 条提示词`, { description: "每次生成都上传同一张参考图，角色会更一致。" });
    } catch (e) {
      toast.error(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  const saveConfig = async () => {
    const name = assetName.trim();
    if (!NAME_RE.test(name)) {
      toast.error("请填写合法的素材名");
      return;
    }
    try {
      await api.saveConfig(name, "sprite", result?.config);
      toast.success(`已保存为「${name}」的配置`, { description: "把图片按卡片上的文件名上传到这个素材，再点处理。" });
      onSaved(name);
    } catch (e) {
      toast.error(errorMessage(e));
    }
  };

  const allText = result?.prompts.map((p) => `【${p.file}】\n${p.prompt}`).join("\n\n") ?? "";

  return (
    <div className="grid h-full grid-cols-[minmax(380px,460px)_1fr]">
      <div className="flex min-h-0 flex-col border-r bg-card">
        <PanelHeader title="提示词生成" />
        <ScrollArea className="min-h-0 flex-1">
          <div className="space-y-5 p-4">
            <div className="grid grid-cols-2 gap-1 rounded-lg bg-muted p-1">
              {(
                [
                  ["character", "角色 / 敌人", PersonStanding],
                  ["environment", "关卡环境", Mountain],
                ] as const
              ).map(([id, label, Icon]) => (
                <button
                  key={id}
                  onClick={() => setKind(id)}
                  className={cn(
                    "flex h-8 items-center justify-center gap-1.5 rounded-md text-xs font-medium text-muted-foreground transition-colors hover:text-foreground",
                    kind === id && "bg-accent text-foreground shadow-sm",
                  )}
                >
                  <Icon className="size-3.5" />
                  {label}
                </button>
              ))}
            </div>

            <div className="space-y-2 rounded-lg border border-primary/30 bg-primary/5 p-3">
              <div className="flex items-center gap-1.5 text-xs font-medium">
                <Bot className="size-3.5 text-primary" />
                AI 扩写
                <span className="text-[10px] font-normal text-muted-foreground">硅基流动</span>
                <span className="ml-auto flex items-center gap-1.5 text-[10px] font-normal text-muted-foreground">
                  <span
                    className={cn(
                      "size-1.5 rounded-full",
                      llm === null ? "bg-muted-foreground/40" : llm.configured ? "bg-success" : "bg-destructive",
                    )}
                  />
                  {llm === null ? "检查中…" : llm.configured ? "已连接" : "未配置 Key"}
                </span>
              </div>
              <Textarea
                rows={2}
                value={idea}
                onChange={(e) => setIdea(e.target.value)}
                onKeyDown={(e) => {
                  if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
                    e.preventDefault();
                    e.stopPropagation();
                    void expandIdea();
                  }
                }}
                placeholder={kind === "character" ? "一句话想法，如：拿火焰镰刀的骷髅死神" : "一句话想法，如：雪夜里的废弃山寺"}
              />
              <div className="flex gap-1.5">
                <Input
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  onFocus={loadModels}
                  list="llm-models"
                  placeholder="模型"
                  className="h-7 flex-1 font-mono text-[11px]"
                />
                <datalist id="llm-models">
                  {models.map((m) => (
                    <option key={m} value={m} />
                  ))}
                </datalist>
                <Button size="sm" disabled={!llm?.configured || !idea.trim() || expanding} onClick={() => void expandIdea()}>
                  {expanding ? <Loader2 className="animate-spin" /> : <WandSparkles />}
                  扩写
                </Button>
              </div>
            </div>

            {kind === "character" ? (
              <>
                <Label title="角色描述">
                  <Textarea
                    rows={3}
                    value={subject}
                    onChange={(e) => setSubject(e.target.value)}
                    placeholder="例：年轻女武士，黑色高马尾配红色发带，红色羽织外衣，身后飘动的红色围巾，深色袴裤，右手持武士太刀"
                  />
                </Label>
                <Label title="动作预设">
                  <Select
                    value={preset}
                    onValueChange={(v) => {
                      setPreset(v);
                      setActions(presets[v] ?? []);
                    }}
                  >
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="选择预设" />
                    </SelectTrigger>
                    <SelectContent>
                      {Object.keys(presets).map((p) => (
                        <SelectItem key={p} value={p}>
                          {p}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </Label>
                <div className="space-y-1.5">
                  <div className="flex items-baseline justify-between text-xs font-medium">
                    动作
                    <span className="text-[10px] font-normal text-muted-foreground">
                      {valid.length} 个动作 · 拆成 {sheets} 张图（每张最多 {MAX_ROWS} 行）
                    </span>
                  </div>
                  <div className="overflow-hidden rounded-md border">
                    <div className="grid grid-cols-[96px_52px_1fr_28px] gap-1 border-b bg-muted/50 px-1.5 py-1 text-[10px] text-muted-foreground">
                      <span>动画名</span>
                      <span>帧数</span>
                      <span>动作描述</span>
                      <span />
                    </div>
                    {actions.map((a, i) => (
                      <div key={i} className="grid grid-cols-[96px_52px_1fr_28px] items-center gap-1 border-b border-border/50 px-1.5 py-1 last:border-0">
                        <Input value={a.name} onChange={(e) => update(i, { name: e.target.value })} placeholder="idle" className="h-7 font-mono" />
                        <Input
                          type="number"
                          min={1}
                          max={16}
                          value={a.frames}
                          onChange={(e) => update(i, { frames: Number(e.target.value) })}
                          className="h-7 px-1.5 font-mono"
                        />
                        <Input value={a.description} onChange={(e) => update(i, { description: e.target.value })} placeholder="待机呼吸" className="h-7" />
                        <Button variant="ghost" size="icon-sm" onClick={() => setActions((l) => l.filter((_, n) => n !== i))}>
                          <X />
                        </Button>
                      </div>
                    ))}
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full border-dashed"
                    onClick={() => setActions((l) => [...l, { name: "", frames: 6, description: "" }])}
                  >
                    <Plus />
                    添加动作
                  </Button>
                </div>
                <Label title="游戏内高度" hint="纹素，16–256">
                  <Input type="number" min={16} max={256} value={height} onChange={(e) => setHeight(Number(e.target.value))} className="font-mono" />
                </Label>
              </>
            ) : (
              <>
                <Label title="关卡主题">
                  <Input value={theme} onChange={(e) => setTheme(e.target.value)} placeholder="例：日式和风森林，黄昏，薄雾，深青绿色和暮紫色" />
                </Label>
                <Label title="装饰物件">
                  <Input value={items} onChange={(e) => setItems(e.target.value)} placeholder="例：鸟居、石灯笼、灌木、倒木、岩石" />
                </Label>
              </>
            )}
            <Label title="画风">
              <Input value={style} onChange={(e) => setStyle(e.target.value)} />
            </Label>
          </div>
        </ScrollArea>
        <div className="border-t p-3">
          <Button size="lg" className="w-full" onClick={generate} disabled={busy}>
            {busy ? <Loader2 className="animate-spin" /> : <Sparkles />}
            生成提示词
          </Button>
        </div>
      </div>

      <div className="flex min-h-0 flex-col">
        <PanelHeader title={result ? `输出 · ${result.prompts.length} 条` : "输出"}>
          {result && <CopyButton text={allText} />}
        </PanelHeader>
        {!result ? (
          <div className="stage-dots flex flex-1 flex-col items-center justify-center gap-2 text-center text-xs text-muted-foreground">
            <Sparkles className="size-6" />
            填写左侧表单后点「生成提示词」
          </div>
        ) : (
          <ScrollArea className="min-h-0 flex-1">
            <div className="mx-auto max-w-4xl space-y-3 p-4">
              {result.prompts.map((p) => (
                <PromptCard
                  key={`${gen}-${p.file}`}
                  item={p}
                  model={model.trim()}
                  llmReady={Boolean(llm?.configured)}
                  onChange={(text) => updatePrompt(p.file, text)}
                />
              ))}
              {result.config && (
                <article className="overflow-hidden rounded-lg border bg-card">
                  <header className="flex items-center gap-2 border-b px-3 py-2">
                    <span className="text-xs font-semibold">对应的 sprite.json</span>
                    <Badge variant="secondary">生成图片后用它切图</Badge>
                    <div className="flex-1" />
                    <CopyButton text={JSON.stringify(result.config, null, 2)} />
                  </header>
                  <pre className="max-h-72 overflow-auto bg-background/60 p-3 font-mono text-[11.5px] leading-relaxed">
                    {JSON.stringify(result.config, null, 2)}
                  </pre>
                  <div className="flex items-center gap-2 border-t p-3">
                    <Input
                      value={assetName}
                      onChange={(e) => setAssetName(e.target.value)}
                      placeholder="素材名，如 archer"
                      className="max-w-60 font-mono"
                      onKeyDown={(e) => e.key === "Enter" && saveConfig()}
                    />
                    <Button onClick={saveConfig}>
                      <Save />
                      保存为素材配置
                    </Button>
                  </div>
                </article>
              )}
            </div>
          </ScrollArea>
        )}
      </div>
    </div>
  );
}

function PromptCard({ item, model, llmReady, onChange }: { item: PromptItem; model: string; llmReady: boolean; onChange: (text: string) => void }) {
  const [busy, setBusy] = useState(false);
  const [original, setOriginal] = useState<string | null>(null);
  const [instruction, setInstruction] = useState("");

  const refine = async () => {
    setBusy(true);
    try {
      const res = await api.refine(item.prompt, instruction, model);
      res.warnings.forEach((w) => toast.warning(w));
      if (original === null) setOriginal(item.prompt);
      onChange(res.prompt);
    } catch (e) {
      toast.error(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <article className="overflow-hidden rounded-lg border bg-card">
      <header className="flex flex-wrap items-center gap-2 border-b px-3 py-2">
        <span className="text-xs">
          保存为 <b className="font-mono">{item.file}</b>
        </span>
        <Badge variant="outline">比例 {item.aspect}</Badge>
        {item.rows?.map((r, i) => (
          <Badge key={r} variant="secondary" className="font-mono">
            {i + 1}·{r}
          </Badge>
        ))}
        {original !== null && <Badge variant="default">AI 已优化</Badge>}
        <div className="flex-1" />
        {original !== null && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              onChange(original);
              setOriginal(null);
            }}
          >
            <Undo2 />
            还原
          </Button>
        )}
        <CopyButton text={item.prompt} />
      </header>
      <p className="whitespace-pre-wrap p-3 text-xs leading-relaxed text-foreground/90">{item.prompt}</p>
      <div className="flex items-center gap-1.5 border-t bg-background/40 px-3 py-2">
        <Input
          value={instruction}
          onChange={(e) => setInstruction(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && llmReady && !busy && void refine()}
          placeholder="可选：给 AI 的修改要求，如「武器换成双刀」「更阴森」"
          className="h-7 flex-1"
          disabled={!llmReady}
        />
        <Tip tip={llmReady ? "用硅基流动润色这条提示词（保留绿幕/行帧等技术要求）" : "还没有配置硅基流动 API Key"}>
          <span>
            <Button variant="outline" size="sm" disabled={!llmReady || busy} onClick={() => void refine()}>
              {busy ? <Loader2 className="animate-spin" /> : <WandSparkles />}
              AI 优化
            </Button>
          </span>
        </Tip>
      </div>
    </article>
  );
}
