import { Fragment, useEffect, useMemo, useRef, useState, type ComponentType, type KeyboardEvent } from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { Search } from "lucide-react";
import { cn } from "@/lib/utils";

export interface Command {
  id: string;
  group: string;
  label: string;
  hint?: string;
  keywords?: string;
  icon?: ComponentType<{ className?: string }>;
  disabled?: boolean;
  run: () => void;
}

/** Substring match, falling back to a subsequence match ("sbp" finds "导出 sprite strip png"). */
function matches(c: Command, q: string): boolean {
  if (!q) return true;
  const hay = `${c.label} ${c.group} ${c.keywords ?? ""}`.toLowerCase();
  if (hay.includes(q)) return true;
  let i = 0;
  for (const ch of hay) {
    if (ch === q[i]) i++;
    if (i === q.length) return true;
  }
  return false;
}

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  commands: Command[];
}

export function CommandPalette({ open, onOpenChange, commands }: Props) {
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (open) {
      setQuery("");
      setActive(0);
    }
  }, [open]);

  const results = useMemo(() => {
    const q = query.trim().toLowerCase();
    return commands.filter((c) => !c.disabled && matches(c, q));
  }, [commands, query]);

  useEffect(() => setActive(0), [query]);
  useEffect(() => {
    listRef.current?.querySelector(`[data-index="${active}"]`)?.scrollIntoView({ block: "nearest" });
  }, [active]);

  const run = (c?: Command) => {
    if (!c) return;
    onOpenChange(false);
    setTimeout(c.run, 0); // let the dialog close and hand focus back first
  };

  const onKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((a) => Math.min(results.length - 1, a + 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((a) => Math.max(0, a - 1));
    } else if (e.key === "Enter") {
      e.preventDefault();
      run(results[active]);
    }
  };

  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/60 data-[state=open]:animate-in data-[state=open]:fade-in-0" />
        <DialogPrimitive.Content
          aria-describedby={undefined}
          className="fixed left-1/2 top-[14%] z-50 w-full max-w-xl -translate-x-1/2 overflow-hidden rounded-lg border bg-popover shadow-2xl data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-95"
        >
          <DialogPrimitive.Title className="sr-only">命令面板</DialogPrimitive.Title>
          <div className="flex items-center gap-2 border-b px-3">
            <Search className="size-4 text-muted-foreground" />
            <input
              autoFocus
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder="输入命令、素材名或动画名…"
              className="h-11 flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
            />
            <kbd className="rounded border px-1.5 font-mono text-[10px] text-muted-foreground">Esc</kbd>
          </div>
          <div ref={listRef} className="max-h-[min(440px,60vh)] overflow-y-auto p-1">
            {results.length === 0 && <p className="py-10 text-center text-xs text-muted-foreground">没有匹配的命令</p>}
            {results.map((c, i) => {
              const Icon = c.icon;
              const header = i === 0 || results[i - 1].group !== c.group;
              return (
                <Fragment key={c.id}>
                  {header && (
                    <div className="px-2 pb-1 pt-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">{c.group}</div>
                  )}
                  <button
                    data-index={i}
                    onMouseMove={() => active !== i && setActive(i)}
                    onClick={() => run(c)}
                    className={cn(
                      "flex w-full items-center gap-2.5 rounded px-2 py-1.5 text-left text-xs text-foreground/85",
                      i === active && "bg-accent text-foreground",
                    )}
                  >
                    {Icon ? <Icon className="size-3.5 shrink-0 text-muted-foreground" /> : <span className="size-3.5 shrink-0" />}
                    <span className="flex-1 truncate">{c.label}</span>
                    {c.hint && <span className="font-mono text-[10px] text-muted-foreground">{c.hint}</span>}
                  </button>
                </Fragment>
              );
            })}
          </div>
          <div className="flex items-center gap-3 border-t px-3 py-1.5 text-[10px] text-muted-foreground">
            <span>↑↓ 选择</span>
            <span>↵ 执行</span>
            <span>Esc 关闭</span>
            <span className="ml-auto">{results.length} 条</span>
          </div>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
