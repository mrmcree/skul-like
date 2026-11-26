import * as React from "react";
import * as ResizablePrimitive from "react-resizable-panels";
import { cn } from "@/lib/utils";

export function ResizablePanelGroup({ className, ...props }: React.ComponentProps<typeof ResizablePrimitive.PanelGroup>) {
  return (
    <ResizablePrimitive.PanelGroup
      className={cn("flex h-full w-full data-[panel-group-direction=vertical]:flex-col", className)}
      {...props}
    />
  );
}

export const ResizablePanel = ResizablePrimitive.Panel;

export function ResizableHandle({ className, ...props }: React.ComponentProps<typeof ResizablePrimitive.PanelResizeHandle>) {
  return (
    <ResizablePrimitive.PanelResizeHandle
      className={cn(
        "relative flex w-px items-center justify-center bg-border transition-colors outline-none",
        "after:absolute after:inset-y-0 after:left-1/2 after:w-1.5 after:-translate-x-1/2",
        "hover:bg-primary/60 data-[resize-handle-state=drag]:bg-primary",
        "data-[panel-group-direction=vertical]:h-px data-[panel-group-direction=vertical]:w-full",
        "data-[panel-group-direction=vertical]:after:left-0 data-[panel-group-direction=vertical]:after:h-1.5 data-[panel-group-direction=vertical]:after:w-full data-[panel-group-direction=vertical]:after:-translate-y-1/2 data-[panel-group-direction=vertical]:after:translate-x-0",
        className,
      )}
      {...props}
    />
  );
}
