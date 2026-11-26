import * as React from "react";
import { cn } from "@/lib/utils";

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, type, ...props }, ref) => (
    <input
      ref={ref}
      type={type}
      className={cn(
        "flex h-8 w-full min-w-0 rounded-md border border-input bg-background px-2.5 text-xs outline-none transition-colors placeholder:text-muted-foreground/70 focus-visible:border-ring focus-visible:ring-1 focus-visible:ring-ring/40 disabled:opacity-50",
        className,
      )}
      {...props}
    />
  ),
);
Input.displayName = "Input";
