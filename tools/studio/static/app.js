// Asset Studio main page: asset list, player, QC, config, raw uploads, processing.
"use strict";

const Api = {
  async request(method, url, body, raw) {
    const opts = { method, headers: {} };
    if (raw) {
      opts.body = raw;
    } else if (body !== undefined) {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(body);
    }
    const res = await fetch(url, opts);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const detail = Array.isArray(data.detail) ? data.detail.map((d) => d.msg).join("; ") : data.detail;
      throw new Error(detail || `请求失败 (${res.status})`);
    }
    return data;
  },
  get: (url) => Api.request("GET", url),
  post: (url, body) => Api.request("POST", url, body),
  put: (url, body) => Api.request("PUT", url, body),
  upload: (url, file) => Api.request("POST", url, undefined, file),
};

const App = (() => {
  const $ = (id) => document.getElementById(id);
  const state = { assets: [], current: null, info: null, qc: null };
  let player;

  // ---------- helpers ----------
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const assetUrl = (name) => `/api/assets/${encodeURIComponent(name)}`;
  const kindLabel = (k) => ({ sprite: "角色", env: "环境" }[k] || "未配置");

  function issuesAt(row, frame) {
    if (!state.qc) return [];
    return state.qc.issues.filter((i) => i.row === row && (frame === undefined || i.frame === frame || i.frame === null));
  }
  function worst(list) {
    if (list.some((i) => i.level === "error")) return "err";
    return list.length ? "warn" : "";
  }

  // ---------- asset list ----------
  async function refreshAssets(select) {
    state.assets = await Api.get("/api/assets");
    const ul = $("asset-list");
    ul.innerHTML = "";
    state.assets.forEach((a) => {
      const li = document.createElement("li");
      li.dataset.name = a.name;
      li.innerHTML = `<span class="dot" id="dot-${esc(a.name)}"></span><span>${esc(a.name)}</span><span class="kind">${kindLabel(a.kind)}</span>`;
      li.onclick = () => openAsset(a.name);
      ul.appendChild(li);
    });
    const target = select || state.current;
    if (target) await openAsset(target);
  }

  async function openAsset(name) {
    state.current = name;
    document.querySelectorAll("#asset-list li").forEach((li) => li.classList.toggle("active", li.dataset.name === name));
    $("no-asset").hidden = true;
    $("asset-view").hidden = false;
    $("asset-title").textContent = name;
    state.info = await Api.get(assetUrl(name));
    $("asset-kind").textContent = kindLabel(state.info.kind);
    showConfig();
    showRaw();
    await refreshQc();
    showOutput();
  }

  // ---------- QC ----------
  async function refreshQc() {
    state.qc = state.info.kind ? await Api.get(`${assetUrl(state.current)}/qc`) : null;
    renderQc();
  }

  function renderQc() {
    const qc = state.qc;
    const summary = $("qc-summary");
    const dot = document.getElementById(`dot-${state.current}`);
    if (!qc) {
      summary.innerHTML = "";
      if (dot) dot.className = "dot";
      return;
    }
    const cls = qc.errors ? "err" : qc.warnings ? "warn" : "ok";
    summary.innerHTML = qc.errors || qc.warnings
      ? `<span class="err">${qc.errors} 错误</span> · <span class="warn">${qc.warnings} 警告</span>`
      : `<span class="ok">质检通过 ✓</span>`;
    if (dot) dot.className = `dot ${cls}`;
    const strips = state.info.config && state.info.config.strips;
    const body = $("qc-body");
    body.innerHTML = "";
    qc.issues.forEach((i) => {
      const tr = document.createElement("tr");
      const where = i.row === null ? "整体" : `${strips ? strips[i.row].name : "行 " + i.row}${i.frame === null ? "" : " 第 " + (i.frame + 1) + " 帧"}`;
      tr.innerHTML = `<td class="lvl-${i.level}">${i.level === "error" ? "错误" : "警告"}</td><td>${esc(where)}</td><td>${esc(i.message)}</td>`;
      if (i.row !== null) {
        tr.className = "jump";
        tr.onclick = () => jumpTo(i.row, i.frame);
      }
      body.appendChild(tr);
    });
    $("qc-empty").hidden = qc.issues.length > 0;
  }

  function jumpTo(row, frame) {
    switchSub("play");
    selectRow(row);
    if (frame !== null && frame !== undefined) {
      player.playing = false;
      $("pl-play").textContent = "▶";
      player.goTo(frame);
    }
  }

  // ---------- player / gallery ----------
  function showOutput() {
    const info = state.info;
    const isSprite = info.kind === "sprite" && info.sheet_url;
    const isEnv = info.kind === "env" && info.outputs && info.outputs.length;
    $("sprite-player").hidden = !isSprite;
    $("env-gallery").hidden = !isEnv;
    $("no-output").hidden = isSprite || isEnv;
    if (isSprite) loadSheet();
    if (isEnv) renderGallery();
  }

  function loadSheet() {
    const { config, sheet_url, sheet_mtime } = state.info;
    const img = new Image();
    img.onload = () => {
      player.load(img, config.cell, config.anchor, config.strips.map((s) => ({ name: s.name, frames: s.frames })));
      renderRows();
      selectRow(Math.min(player.row, config.strips.length - 1));
    };
    img.src = `${sheet_url}?t=${sheet_mtime}`;
  }

  function renderRows() {
    const ul = $("row-list");
    ul.innerHTML = "";
    player.rows.forEach((r, i) => {
      const li = document.createElement("li");
      const flag = worst(issuesAt(i));
      li.innerHTML = `<span>${esc(r.name)}</span><span class="count">${r.frames} 帧 ${flag ? `<span class="flag lvl-${flag === "err" ? "error" : "warning"}">●</span>` : ""}</span>`;
      li.onclick = () => selectRow(i);
      ul.appendChild(li);
    });
  }

  function selectRow(i) {
    player.setRow(i);
    document.querySelectorAll("#row-list li").forEach((li, n) => li.classList.toggle("active", n === i));
    renderStrip();
  }

  function renderStrip() {
    const strip = $("frame-strip");
    strip.innerHTML = "";
    for (let f = 0; f < player.frameCount(); f++) {
      const div = document.createElement("div");
      div.className = `thumb ${worst(issuesAt(player.row, f))}`;
      div.title = issuesAt(player.row, f).map((i) => i.message).join("\n");
      div.appendChild(player.thumbnail(f, 1));
      const label = document.createElement("span");
      label.textContent = f + 1;
      div.appendChild(label);
      div.onclick = () => { player.playing = false; $("pl-play").textContent = "▶"; player.goTo(f); };
      strip.appendChild(div);
    }
  }

  function onFrame(row, frame) {
    $("pl-info").textContent = `${player.rows[row] ? player.rows[row].name : ""} ${frame + 1}/${player.frameCount()}`;
    document.querySelectorAll("#frame-strip .thumb").forEach((t, i) => t.classList.toggle("current", i === frame));
  }

  function renderGallery() {
    const box = $("env-gallery");
    box.innerHTML = "";
    state.info.outputs.forEach((o) => {
      const card = document.createElement("div");
      card.className = "env-card";
      card.innerHTML = `<img alt=""><div class="meta"><b>${esc(o.name)}</b> · 游戏内 ${o.size[0]}×${o.size[1]} · 纹素 ${o.texels ? o.texels.join("×") : "?"}</div>`;
      card.querySelector("img").src = `${o.url}?t=${Date.now()}`;
      box.appendChild(card);
    });
  }

  // ---------- config / raw / process ----------
  function showConfig() {
    const { kind, config } = state.info;
    $("cfg-kind").value = kind || "sprite";
    $("cfg-text").value = config ? JSON.stringify(config, null, 2) : "";
    $("cfg-status").textContent = config ? "" : "还没有配置。可以在「提示词生成」里一键生成，或手动粘贴。";
  }

  async function saveConfig() {
    const status = $("cfg-status");
    try {
      const config = JSON.parse($("cfg-text").value);
      await Api.put(`${assetUrl(state.current)}/config`, { kind: $("cfg-kind").value, config });
      status.className = "status ok";
      status.textContent = "已保存";
      await refreshAssets(state.current);
    } catch (err) {
      status.className = "status error";
      status.textContent = err instanceof SyntaxError ? `JSON 格式错误：${err.message}` : err.message;
    }
  }

  function showRaw() {
    const asset = state.assets.find((a) => a.name === state.current);
    const grid = $("raw-grid");
    grid.innerHTML = "";
    (asset ? asset.raw_images : []).forEach((file) => {
      const fig = document.createElement("figure");
      fig.innerHTML = `<img alt="" loading="lazy"><figcaption>${esc(file)}</figcaption>`;
      fig.querySelector("img").src = `/files/raw/${encodeURIComponent(state.current)}/${encodeURIComponent(file)}?t=${Date.now()}`;
      grid.appendChild(fig);
    });
  }

  async function uploadFiles(files) {
    const log = $("log");
    for (const file of files) {
      try {
        await Api.upload(`${assetUrl(state.current)}/upload?filename=${encodeURIComponent(file.name)}`, file);
        log.textContent += `已上传 ${file.name}\n`;
      } catch (err) {
        log.textContent += `上传失败 ${file.name}：${err.message}\n`;
      }
    }
    $("log-box").open = true;
    await refreshAssets(state.current);
    switchSub("raw");
  }

  async function processCurrent() {
    const btn = $("btn-process");
    btn.disabled = true;
    btn.textContent = "处理中…（可能要 1-2 分钟）";
    try {
      const res = await Api.post(`${assetUrl(state.current)}/process`);
      $("log").textContent = res.log || "(没有输出)";
      $("log-box").open = !res.ok;
      state.info = await Api.get(assetUrl(state.current));
      state.qc = res.qc;
      renderQc();
      showOutput();
    } catch (err) {
      $("log").textContent = err.message;
      $("log-box").open = true;
    } finally {
      btn.disabled = false;
      btn.textContent = "处理";
    }
  }

  // ---------- tabs & wiring ----------
  function switchSub(name) {
    document.querySelectorAll("#sub-tabs button").forEach((b) => b.classList.toggle("active", b.dataset.sub === name));
    document.querySelectorAll(".sub-page").forEach((p) => p.classList.toggle("active", p.id === `sub-${name}`));
  }

  function wireControls() {
    $("pl-play").onclick = () => { player.playing = !player.playing; $("pl-play").textContent = player.playing ? "⏸" : "▶"; };
    $("pl-prev").onclick = () => { player.playing = false; $("pl-play").textContent = "▶"; player.step(-1); };
    $("pl-next").onclick = () => { player.playing = false; $("pl-play").textContent = "▶"; player.step(1); };
    $("pl-fps").oninput = (e) => (player.fps = Number(e.target.value) || 10);
    $("pl-zoom").onchange = (e) => { player.zoom = Number(e.target.value); player.draw(); };
    $("pl-bg").onchange = (e) => { player.background = e.target.value; player.draw(); };
    $("pl-onion").onchange = (e) => { player.onion = e.target.checked; player.draw(); };
    $("pl-anchor").onchange = (e) => { player.showAnchor = e.target.checked; player.draw(); };
    $("pl-flip").onchange = (e) => { player.flip = e.target.checked; player.draw(); };
    document.addEventListener("keydown", (e) => {
      if (e.target.matches("input, textarea, select") || $("asset-view").hidden) return;
      if (e.key === " ") { e.preventDefault(); $("pl-play").click(); }
      if (e.key === "ArrowLeft") $("pl-prev").click();
      if (e.key === "ArrowRight") $("pl-next").click();
    });
  }

  function wireUpload() {
    const zone = $("dropzone");
    zone.ondragover = (e) => { e.preventDefault(); zone.classList.add("over"); };
    zone.ondragleave = () => zone.classList.remove("over");
    zone.ondrop = (e) => { e.preventDefault(); zone.classList.remove("over"); uploadFiles([...e.dataTransfer.files]); };
    $("raw-input").onchange = (e) => uploadFiles([...e.target.files]);
  }

  function init() {
    player = new SheetPlayer($("player-canvas"), onFrame);
    document.querySelectorAll("#main-tabs button").forEach((b) => (b.onclick = () => {
      document.querySelectorAll("#main-tabs button").forEach((x) => x.classList.toggle("active", x === b));
      document.querySelectorAll(".tab-page").forEach((p) => p.classList.toggle("active", p.id === `tab-${b.dataset.tab}`));
    }));
    document.querySelectorAll("#sub-tabs button").forEach((b) => (b.onclick = () => switchSub(b.dataset.sub)));
    $("refresh-assets").onclick = () => refreshAssets();
    $("new-asset").onsubmit = async (e) => {
      e.preventDefault();
      const name = e.target.name.value.trim();
      // The folder is created on the first upload or config save; just open an empty asset.
      state.current = name;
      document.querySelectorAll("#asset-list li").forEach((li) => li.classList.remove("active"));
      $("asset-view").hidden = false;
      $("no-asset").hidden = true;
      $("asset-title").textContent = name;
      state.info = { name, kind: null, config: null };
      showConfig();
      showRaw();
      showOutput();
      switchSub("raw");
      e.target.reset();
    };
    $("btn-process").onclick = processCurrent;
    $("btn-qc").onclick = refreshQc;
    $("cfg-save").onclick = saveConfig;
    wireControls();
    wireUpload();
    refreshAssets();
    Prompts.init();
  }

  return { init, refreshAssets };
})();

App.init();
