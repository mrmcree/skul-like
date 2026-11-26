import { useEffect, useRef } from "react";
import { CircleCheck, CircleX, ScanSearch, Terminal, Trash2, TriangleAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { Issue, LogLine, QcReport, Strip } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Tip } from "./common";

export type BottomTab = "issues" | "log";

interface Props {
  tab: BottomTab;
  onTab: (t: BottomTab) => void;
  qc: QcReport | null;
  strips: Strip[];
  log: LogLine[];
  onJump: (issue: Issue) => void;
  onClearLog: () => void;
}

export function BottomPanel({ tab, onTab, qc, strips, log, onJump, onClearLog }: Props) {
  const count = qc ? qc.errors + qc.warnings : 0;
  return (
    <Tabs value={tab} onValueChange={(v) => onTab(v as BottomTab)} className="h-full bg-card">
      <div className="flex h-8 shrink-0 items-center border-b px-1">
        <TabsList className="h-7 bg-transparent p-0">
          <TabsTrigger value="issues">
            <ScanSearch />
            质检问题
            {count > 0 && (
              <span
                className={cn(
                  "rounded px-1 text-[10px]",
                  qc!.errors ? "bg-destructive/20 text-destructive" : "bg-warning/20 text-warning",
                )}
              >
                {count}
              </span>
            )}
          </TabsTrigger>
          <TabsTrigger value="log">
            <Terminal />
            输出
          </TabsTrigger>
        </TabsList>
        <div className="flex-1" />
        {tab === "log" && (
          <Tip tip="清空输出">
            <Button variant="ghost" size="icon-sm" onClick={onClearLog}>
              <Trash2 />
            </Button>
          </Tip>
        )}
      </div>
      <TabsContent value="issues" className="min-h-0 flex-1">
        <IssueList qc={qc} strips={strips} onJump={onJump} />
      </TabsContent>
      <TabsContent value="log" className="min-h-0 flex-1">
        <LogView log={log} />
      </TabsContent>
    </Tabs>
  );
}

function IssueList({ qc, strips, onJump }: { qc: QcReport | null; strips: Strip[]; onJump: (i: Issue) => void }) {
  if (!qc) return <p className="p-4 text-xs text-muted-foreground">还没有质检结果。</p>;
  if (!qc.issues.length) {
    return (
      <p className="flex items-center gap-2 p-4 text-xs text-success">
        <CircleCheck className="size-4" />
        没有发现问题
      </p>
    );
  }
  const where = (i: Issue) => {
    if (i.row === null) return "整体";
    const name = strips[i.row]?.name ?? `行 ${i.row}`;
    return i.frame === null ? name : `${name} · 第 ${i.frame + 1} 帧`;
  };
  return (
    <ScrollArea className="h-full">
      <table className="w-full text-xs">
        <tbody>
          {qc.issues.map((i, n) => (
            <tr
              key={n}
              onClick={() => i.row !== null && onJump(i)}
              className={cn("border-b border-border/50", i.row !== null && "cursor-pointer hover:bg-accent")}
            >
              <td className="w-8 py-1.5 pl-3">
                {i.level === "error" ? (
                  <CircleX className="size-3.5 text-destructive" />
                ) : (
                  <TriangleAlert className="size-3.5 text-warning" />
                )}
              </td>
              <td className="w-48 truncate py-1.5 font-mono text-muted-foreground">{where(i)}</td>
              <td className="py-1.5">{i.message}</td>
              <td className="w-20 py-1.5 pr-3 text-right font-mono text-[10px] text-muted-foreground">{i.code}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </ScrollArea>
  );
}

function LogView({ log }: { log: LogLine[] }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (ref.current) ref.current.scrollTop = ref.current.scrollHeight;
  }, [log]);
  if (!log.length) return <p className="p-4 text-xs text-muted-foreground">处理日志会显示在这里。</p>;
  return (
    <div ref={ref} className="h-full overflow-auto bg-background/50 py-1 font-mono text-[11.5px] leading-5">
      {log.map((l, n) => (
        <div key={n} className="flex gap-3 px-3 hover:bg-accent/50">
          <span className="shrink-0 text-muted-foreground/60">{l.time}</span>
          <span
            className={cn(
              "whitespace-pre-wrap break-all",
              l.level === "error" && "text-destructive",
              l.level === "ok" && "text-success",
            )}
          >
            {l.text}
          </span>
        </div>
      ))}
    </div>
  );
}
