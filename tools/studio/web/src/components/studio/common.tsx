import type { ReactNode } from "react";
import { CircleCheck, CircleX, FileQuestion, Mountain, PersonStanding, TriangleAlert, type LucideIcon } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import type { Health, Issue, Kind, QcReport } from "@/lib/types";
import { cn } from "@/lib/utils";

export const kindLabel = (k: Kind | null | undefined) => (k === "sprite" ? "角色" : k === "env" ? "环境" : "未配置");

export function worst(list: Issue[]): Health | undefined {
  if (list.some((i) => i.level === "error")) return "err";
  return list.length ? "warn" : undefined;
}

export function healthOf(qc: QcReport | null): Health | undefined {
  if (!qc) return undefined;
  return qc.errors ? "err" : qc.warnings ? "warn" : "ok";
}

export function PanelHeader({ title, children, className }: { title: ReactNode; children?: ReactNode; className?: string }) {
  return (
    <div className={cn("flex h-8 shrink-0 items-center justify-between gap-2 border-b px-3", className)}>
      <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">{title}</span>
      <div className="flex items-center gap-0.5">{children}</div>
    </div>
  );
}

export function HealthDot({ health, className }: { health?: Health; className?: string }) {
  return (
    <span
      className={cn(
        "size-1.5 shrink-0 rounded-full",
        !health && "bg-muted-foreground/25",
        health === "ok" && "bg-success",
        health === "warn" && "bg-warning",
        health === "err" && "bg-destructive",
        className,
      )}
    />
  );
}

export function KindIcon({ kind, className }: { kind: Kind | null; className?: string }) {
  const Icon = kind === "sprite" ? PersonStanding : kind === "env" ? Mountain : FileQuestion;
  return (
    <Icon
      className={cn(
        "size-3.5 shrink-0",
        kind === "sprite" ? "text-info" : kind === "env" ? "text-success" : "text-muted-foreground",
        className,
      )}
    />
  );
}

export function KindBadge({ kind }: { kind: Kind | null }) {
  return (
    <Badge variant="outline">
      <KindIcon kind={kind} />
      {kindLabel(kind)}
    </Badge>
  );
}

export function QcSummary({ qc }: { qc: QcReport | null }) {
  if (!qc) return null;
  if (!qc.errors && !qc.warnings) {
    return (
      <Badge variant="success">
        <CircleCheck />
        质检通过
      </Badge>
    );
  }
  return (
    <div className="flex items-center gap-1">
      {qc.errors > 0 && (
        <Badge variant="destructive">
          <CircleX />
          {qc.errors} 错误
        </Badge>
      )}
      {qc.warnings > 0 && (
        <Badge variant="warning">
          <TriangleAlert />
          {qc.warnings} 警告
        </Badge>
      )}
    </div>
  );
}

export function Tip({ tip, children, side }: { tip: ReactNode; children: ReactNode; side?: "top" | "bottom" | "left" | "right" }) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>{children}</TooltipTrigger>
      <TooltipContent side={side}>{tip}</TooltipContent>
    </Tooltip>
  );
}

export function EmptyState({ icon: Icon, title, text, action }: { icon: LucideIcon; title: string; text?: string; action?: ReactNode }) {
  return (
    <div className="stage-dots flex h-full min-h-0 flex-1 flex-col items-center justify-center gap-3 p-8 text-center">
      <div className="grid size-12 place-items-center rounded-xl border bg-card">
        <Icon className="size-5 text-muted-foreground" />
      </div>
      <div className="space-y-1">
        <p className="text-sm font-medium">{title}</p>
        {text && <p className="max-w-xs text-xs text-muted-foreground">{text}</p>}
      </div>
      {action}
    </div>
  );
}
