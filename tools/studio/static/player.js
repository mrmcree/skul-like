// Sprite-sheet animation player: one row = one animation, cells of config.cell size,
// feet at config.anchor. Pixel-perfect (no smoothing), with onion skin and anchor marker.
"use strict";

class SheetPlayer {
  constructor(canvas, onFrame) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.onFrame = onFrame || (() => {});
    this.image = null;
    this.cell = [64, 64];
    this.anchor = [32, 60];
    this.rows = [];          // [{name, frames}]
    this.row = 0;
    this.frame = 0;
    this.playing = true;
    this.fps = 10;
    this.zoom = 3;
    this.background = "dark";
    this.onion = false;
    this.showAnchor = true;
    this.flip = false;
    this._last = 0;
    this._acc = 0;
    requestAnimationFrame((t) => this._tick(t));
  }

  load(image, cell, anchor, rows) {
    this.image = image;
    this.cell = cell;
    this.anchor = anchor;
    this.rows = rows;
    this.setRow(Math.min(this.row, rows.length - 1));
  }

  setRow(row) {
    this.row = Math.max(0, row);
    this.frame = 0;
    this._acc = 0;
    this.draw();
  }

  frameCount() {
    return this.rows[this.row] ? this.rows[this.row].frames : 0;
  }

  step(delta) {
    const n = this.frameCount();
    if (!n) return;
    this.frame = (this.frame + delta + n) % n;
    this.draw();
  }

  goTo(frame) {
    this.frame = frame;
    this.draw();
  }

  _tick(time) {
    const dt = this._last ? (time - this._last) / 1000 : 0;
    this._last = time;
    if (this.playing && this.image && this.frameCount()) {
      this._acc += dt;
      const period = 1 / Math.max(1, this.fps);
      while (this._acc >= period) {
        this._acc -= period;
        this.frame = (this.frame + 1) % this.frameCount();
        this.draw();
      }
    }
    requestAnimationFrame((t) => this._tick(t));
  }

  _paintBackground(w, h) {
    const ctx = this.ctx;
    const colors = { dark: "#1d1a24", light: "#c9c4d4", forest: "#3a4a52" };
    if (this.background === "checker") {
      const s = 8 * this.zoom;
      for (let y = 0; y < h; y += s) {
        for (let x = 0; x < w; x += s) {
          ctx.fillStyle = ((x + y) / s) % 2 ? "#2b2836" : "#363143";
          ctx.fillRect(x, y, s, s);
        }
      }
      return;
    }
    ctx.fillStyle = colors[this.background] || colors.dark;
    ctx.fillRect(0, 0, w, h);
    if (this.background === "forest") {
      ctx.fillStyle = "#5d7a2e";   // a grass line at the feet
      ctx.fillRect(0, (this.anchor[1] + 1) * this.zoom, w, h);
    }
  }

  _drawCell(frame, alpha) {
    const [cw, ch] = this.cell;
    const z = this.zoom;
    const ctx = this.ctx;
    ctx.save();
    ctx.globalAlpha = alpha;
    if (this.flip) {
      ctx.translate(cw * z, 0);
      ctx.scale(-1, 1);
    }
    ctx.drawImage(this.image, frame * cw, this.row * ch, cw, ch, 0, 0, cw * z, ch * z);
    ctx.restore();
  }

  draw() {
    const [cw, ch] = this.cell;
    const z = this.zoom;
    if (this.canvas.width !== cw * z || this.canvas.height !== ch * z) {
      this.canvas.width = cw * z;
      this.canvas.height = ch * z;
    }
    const ctx = this.ctx;
    ctx.imageSmoothingEnabled = false;
    this._paintBackground(cw * z, ch * z);
    if (!this.image || !this.frameCount()) return;
    if (this.onion && this.frameCount() > 1) {
      const prev = (this.frame - 1 + this.frameCount()) % this.frameCount();
      this._drawCell(prev, 0.3);
    }
    this._drawCell(this.frame, 1);
    if (this.showAnchor) {
      const ax = (this.flip ? cw - this.anchor[0] : this.anchor[0]) * z;
      const ay = this.anchor[1] * z;
      ctx.strokeStyle = "rgba(127,179,255,.9)";
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(ax - 6 * z, ay + 0.5); ctx.lineTo(ax + 6 * z, ay + 0.5);
      ctx.moveTo(ax + 0.5, ay - 6 * z); ctx.lineTo(ax + 0.5, ay + 2 * z);
      ctx.stroke();
    }
    this.onFrame(this.row, this.frame);
  }

  // Small canvas of one frame, for the thumbnail strip.
  thumbnail(frame, scale) {
    const [cw, ch] = this.cell;
    const c = document.createElement("canvas");
    c.width = cw * scale;
    c.height = ch * scale;
    const ctx = c.getContext("2d");
    ctx.imageSmoothingEnabled = false;
    ctx.drawImage(this.image, frame * cw, this.row * ch, cw, ch, 0, 0, cw * scale, ch * scale);
    return c;
  }
}
