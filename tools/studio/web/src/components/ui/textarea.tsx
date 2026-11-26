import * as React from "react";
import { cn } from "@/lib/utils";

export const Textarea = React.forwardRef<HTMLTextAreaElement, React.TextareaHTMLAttributes<HTMLTextAreaElement>>(
  ({ className, ...props }, ref) => (
    <textarea
      ref={ref}
      className={cn(
        "flex min-h-16 w-full rounded-md border border-input bg-background px-2.5 py-2 text-xs leading-relaxed outline-none transition-colors placeholder:text-muted-foreground/70 focus-visible:border-ring focus-visible:ring-1 focus-visible:ring-ring/40",
        className,
      )}
      {...props}
    />
  ),
);
Textarea.displayName = "Textarea";
