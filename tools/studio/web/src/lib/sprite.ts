// Pixel-perfect sprite-sheet rendering: one row = one animation, cells of config.cell,
// feet at config.anchor. Onion skin, anchor cross, mirror and texel grid.

export type Background = "checker" | "dark" | "light" | "forest";

export interface ViewOptions {
  zoom: number;
  background: Background;
  onion: boolean;
  anchor: boolean;
  flip: boolean;
  grid: boolean;
  compare: boolean;
}

export const defaultView: ViewOptions = {
  zoom: 4, background: "checker", onion: false, anchor: true, flip: false, grid: false, compare: false,
};

export const ZOOMS = [1, 2, 3, 4, 6, 8, 12];

export const BACKGROUNDS: Record<Background, string> = {
  checker: "棋盘格", dark: "深色", light: "浅色", forest: "森林",
};

type Vec = [number, number];

function paintBackground(ctx: CanvasRenderingContext2D, w: number, h: number, z: number, anchor: Vec, bg: Background) {
  if (bg === "checker") {
    const s = 4 * z;
    for (let y = 0; y < h; y += s) {
      for (let x = 0; x < w; x += s) {
        ctx.fillStyle = (x / s + y / s) % 2 ? "#2b2836" : "#363143";
        ctx.fillRect(x, y, s, s);
      }
    }
    return;
  }
  const colors = { dark: "#1d1a24", light: "#c9c4d4", forest: "#3a4a52" };
  ctx.fillStyle = colors[bg];
  ctx.fillRect(0, 0, w, h);
  if (bg === "forest") {
    ctx.fillStyle = "#5d7a2e"; // a grass line at the feet
    ctx.fillRect(0, (anchor[1] + 1) * z, w, h);
  }
}

export function drawSprite(
  canvas: HTMLCanvasElement, image: HTMLImageElement | null, cell: Vec, anchor: Vec,
  row: number, frame: number, frames: number, opts: ViewOptions,
) {
  const [cw, ch] = cell;
  const z = opts.zoom;
  const w = cw * z;
  const h = ch * z;
  if (canvas.width !== w || canvas.height !== h) {
    canvas.width = w;
    canvas.height = h;
  }
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  ctx.imageSmoothingEnabled = false;
  ctx.clearRect(0, 0, w, h);
  paintBackground(ctx, w, h, z, anchor, opts.background);
  if (!image || frames <= 0) return;

  const drawCell = (f: number, alpha: number) => {
    ctx.save();
    ctx.globalAlpha = alpha;
    if (opts.flip) {
      ctx.translate(w, 0);
      ctx.scale(-1, 1);
    }
    ctx.drawImage(image, f * cw, row * ch, cw, ch, 0, 0, w, h);
    ctx.restore();
  };
  if (opts.onion && frames > 1) drawCell((frame - 1 + frames) % frames, 0.3);
  drawCell(frame, 1);

  if (opts.grid && z >= 4) {
    ctx.strokeStyle = "rgba(255,255,255,.07)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    for (let x = 0; x <= cw; x++) { ctx.moveTo(x * z + 0.5, 0); ctx.lineTo(x * z + 0.5, h); }
    for (let y = 0; y <= ch; y++) { ctx.moveTo(0, y * z + 0.5); ctx.lineTo(w, y * z + 0.5); }
    ctx.stroke();
  }
  if (opts.anchor) {
    const ax = (opts.flip ? cw - anchor[0] : anchor[0]) * z;
    const ay = anchor[1] * z;
    ctx.strokeStyle = "rgba(127,179,255,.9)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(ax - 6 * z, ay + 0.5); ctx.lineTo(ax + 6 * z, ay + 0.5);
    ctx.moveTo(ax + 0.5, ay - 6 * z); ctx.lineTo(ax + 0.5, ay + 2 * z);
    ctx.stroke();
  }
}

// ---------- export helpers (native 1x pixels, for copy / download) ----------

export function frameCanvas(image: HTMLImageElement, cell: Vec, row: number, frame: number, scale = 1, flip = false) {
  const [cw, ch] = cell;
  const c = document.createElement("canvas");
  c.width = cw * scale;
  c.height = ch * scale;
  const ctx = c.getContext("2d")!;
  ctx.imageSmoothingEnabled = false;
  if (flip) {
    ctx.translate(c.width, 0);
    ctx.scale(-1, 1);
  }
  ctx.drawImage(image, frame * cw, row * ch, cw, ch, 0, 0, c.width, c.height);
  return c;
}

export function stripCanvas(image: HTMLImageElement, cell: Vec, row: number, frames: number, scale = 1) {
  const [cw, ch] = cell;
  const c = document.createElement("canvas");
  c.width = cw * frames * scale;
  c.height = ch * scale;
  const ctx = c.getContext("2d")!;
  ctx.imageSmoothingEnabled = false;
  ctx.drawImage(image, 0, row * ch, cw * frames, ch, 0, 0, c.width, c.height);
  return c;
}

function toBlob(c: HTMLCanvasElement): Promise<Blob> {
  return new Promise((resolve, reject) =>
    c.toBlob((b) => (b ? resolve(b) : reject(new Error("无法生成 PNG"))), "image/png"),
  );
}

export async function copyCanvas(c: HTMLCanvasElement) {
  if (!navigator.clipboard || typeof ClipboardItem === "undefined") throw new Error("这个浏览器不支持复制图片");
  await navigator.clipboard.write([new ClipboardItem({ "image/png": toBlob(c) })]);
}

export async function downloadCanvas(c: HTMLCanvasElement, filename: string) {
  const url = URL.createObjectURL(await toBlob(c));
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
