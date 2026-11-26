import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";

const SHORTCUTS: [string, string][] = [
  ["Ctrl + K", "命令面板"],
  ["空格", "播放 / 暂停"],
  ["← / →", "上一帧 / 下一帧"],
  ["↑ / ↓", "上一个 / 下一个动画"],
  ["Ctrl + 滚轮", "缩放视口"],
  ["Ctrl + Enter", "处理当前素材"],
  ["Ctrl + S", "保存配置（配置编辑器内）"],
  ["右键", "素材、动画、帧和视口的快捷菜单"],
  ["?", "显示这个列表"],
];

export function ShortcutsDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (o: boolean) => void }) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogTitle>键盘快捷键</DialogTitle>
        <div className="divide-y divide-border/60 rounded-md border">
          {SHORTCUTS.map(([key, what]) => (
            <div key={key} className="flex items-center justify-between px-3 py-2 text-xs">
              <span className="text-muted-foreground">{what}</span>
              <kbd className="rounded border bg-background px-1.5 py-0.5 font-mono text-[11px]">{key}</kbd>
            </div>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  );
}
