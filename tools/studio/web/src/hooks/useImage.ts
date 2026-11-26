import { useEffect, useState } from "react";

/** Loads an image; keeps the previous one on screen until the new one is ready. */
export function useImage(src: string | null) {
  const [image, setImage] = useState<HTMLImageElement | null>(null);
  useEffect(() => {
    if (!src) {
      setImage(null);
      return;
    }
    let live = true;
    const img = new Image();
    img.onload = () => live && setImage(img);
    img.onerror = () => live && setImage(null);
    img.src = src;
    return () => {
      live = false;
    };
  }, [src]);
  return image;
}
