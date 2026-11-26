import { useState, type FormEvent } from "react";
import { ClipboardCopy, Copy, FolderOpen, Play, Plus, RefreshCw, Search, Upload } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  ContextMenu, ContextMenuContent, ContextMenuItem, ContextMenuLabel, ContextMenuSeparator, ContextMenuTrigger,
} from "@/components/ui/context-menu";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { AssetSummary, Health } from "@/lib/types";
import { cn, NAME_RE } from "@/lib/utils";
import { HealthDot, KindIcon, PanelHeader, Tip } from "./common";

interface Props {
  assets: AssetSummary[];
  current: string | null;
  health: Record<string, Health>;
  processing: boolean;
  onOpen: (name: string) => void;
  onNew: (name: string) => void;
  onRefresh: () => void;
  onProcess: (name: string) => void;
  onShowRaw: (name: string) => void;
  onCopy: (text: string) => void;
}

export function AssetExplorer({ assets, current, health, processing, onOpen, onNew, onRefresh, onProcess, onShowRaw, onCopy }: Props) {
  const [query, setQuery] = useState("");
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");

  let all = assets;
  if (current && !assets.some((a) => a.name === current)) {
    all = [{ name: current, kind: null, raw_images: [] }, ...assets]; // new, not saved yet
  }
  const q = query.trim().toLowerCase();
  const list = q ? all.filter((a) => a.name.toLowerCase().includes(q)) : all;
  const groups: [string, AssetSummary[]][] = [
    ["角色 / 敌人", list.filter((a) => a.kind === "sprite")],
    ["关卡环境", list.filter((a) => a.kind === "env")],
    ["未配置", list.filter((a) => !a.kind)],
  ];

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const n = name.trim();
    if (!NAME_RE.test(n)) {
      toast.error("名称只能包含字母、数字、中文、下划线和横线（最多 40 个字符）");
      return;
    }
    onNew(n);
    setName("");
    setCreating(false);
  };

  return (
    <div className="flex h-full flex-col bg-card">
      <PanelHeader title="素材">
        <Tip tip="新建素材">
          <Button variant="ghost" size="icon-sm" onClick={() => setCreating((v) => !v)}>
            <Plus />
          </Button>
        </Tip>
        <Tip tip="刷新">
          <Button variant="ghost" size="icon-sm" onClick={onRefresh}>
            <RefreshCw />
          </Button>
        </Tip>
      </PanelHeader>
      <div className="space-y-2 p-2">
        <div className="relative">
          <Search className="absolute left-2 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
          <Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="搜索素材…" className="h-7 pl-7" />
        </div>
        {creating && (
          <form onSubmit={submit} className="flex gap-1">
            <Input
              autoFocus
              value={name}
              onChange={(e) => setName(e.target.value)}
              onKeyDown={(e) => e.key === "Escape" && setCreating(false)}
              placeholder="新素材名，如 archer"
              className="h-7 font-mono"
            />
            <Button size="sm" type="submit">
              新建
            </Button>
          </form>
        )}
      </div>
      <ScrollArea className="min-h-0 flex-1">
        <div className="px-1.5 pb-2">
          {groups.map(([label, items]) =>
            items.length === 0 ? null : (
              <div key={label} className="mb-2">
                <div className="flex items-center gap-1.5 px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                  {label}
                  <span className="font-normal opacity-60">{items.length}</span>
                </div>
                {items.map((a) => (
                  <ContextMenu key={a.name}>
                    <ContextMenuTrigger asChild>
                      <button
                        onClick={() => onOpen(a.name)}
                        className={cn(
                          "flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-xs text-muted-foreground transition-colors hover:bg-accent hover:text-foreground",
                          current === a.name && "bg-accent text-foreground ring-1 ring-inset ring-primary/40",
                        )}
                      >
                        <KindIcon kind={a.kind} />
                        <span className="flex-1 truncate font-mono">{a.name}</span>
                        {a.raw_images.length > 0 && <span className="text-[10px] opacity-60">{a.raw_images.length}</span>}
                        <HealthDot health={health[a.name]} />
                      </button>
                    </ContextMenuTrigger>
                    <ContextMenuContent>
                      <ContextMenuLabel className="font-mono">{a.name}</ContextMenuLabel>
                      <ContextMenuSeparator />
                      <ContextMenuItem onSelect={() => onOpen(a.name)}>
                        <FolderOpen />
                        打开
                      </ContextMenuItem>
                      <ContextMenuItem disabled={!a.kind || processing} onSelect={() => onProcess(a.name)}>
                        <Play />
                        处理
                      </ContextMenuItem>
                      <ContextMenuItem onSelect={() => onShowRaw(a.name)}>
                        <Upload />
                        上传原图
                      </ContextMenuItem>
                      <ContextMenuSeparator />
                      <ContextMenuItem onSelect={() => onCopy(a.name)}>
                        <Copy />
                        复制名称
                      </ContextMenuItem>
                      <ContextMenuItem onSelect={() => onCopy(`assets/raw/${a.name}`)}>
                        <ClipboardCopy />
                        复制原图目录
                      </ContextMenuItem>
                    </ContextMenuContent>
                  </ContextMenu>
                ))}
              </div>
            ),
          )}
          {list.length === 0 && <p className="px-2 py-8 text-center text-xs text-muted-foreground">没有匹配的素材</p>}
        </div>
      </ScrollArea>
    </div>
  );
}
