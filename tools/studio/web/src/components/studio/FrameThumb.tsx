import { useEffect, useRef } from "react";
import { cn } from "@/lib/utils";

interface Props {
  image: HTMLImageElement | null;
  cell: [number, number];
  row: number;
  frame: number;
  height: number;
  className?: string;
}

export function FrameThumb({ image, cell, row, frame, height, className }: Props) {
  const ref = useRef<HTMLCanvasElement>(null);
  const [cw, ch] = cell;
  useEffect(() => {
    const c = ref.current;
    if (!c || !image) return;
    c.width = cw;
    c.height = ch;
    const ctx = c.getContext("2d");
    if (!ctx) return;
    ctx.imageSmoothingEnabled = false;
    ctx.clearRect(0, 0, cw, ch);
    ctx.drawImage(image, frame * cw, row * ch, cw, ch, 0, 0, cw, ch);
  }, [image, cw, ch, row, frame]);
  return (
    <canvas
      ref={ref}
      style={{ width: Math.round((height * cw) / ch), height }}
      className={cn("checker pixelated rounded-sm", className)}
    />
  );
}
