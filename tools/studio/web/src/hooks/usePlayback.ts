import { useEffect, useState } from "react";

/** Current frame of a looping animation advanced at `fps` while `playing`. */
export function usePlayback(frames: number, fps: number, playing: boolean) {
  const [frame, setFrame] = useState(0);

  useEffect(() => {
    if (frames > 0 && frame >= frames) setFrame(0);
  }, [frames, frame]);

  useEffect(() => {
    if (!playing || frames <= 0) return;
    let raf = 0;
    let last = 0;
    let acc = 0;
    const period = 1 / Math.max(1, fps);
    const tick = (t: number) => {
      if (last) acc += (t - last) / 1000;
      last = t;
      if (acc >= period) {
        const n = Math.floor(acc / period);
        acc -= n * period;
        setFrame((f) => (f + n) % frames);
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [playing, fps, frames]);

  return [frame, setFrame] as const;
}
