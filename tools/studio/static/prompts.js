// "提示词生成" tab: build Jimeng prompts (and a matching sprite.json) from a form.
"use strict";

const Prompts = (() => {
  const $ = (id) => document.getElementById(id);
  let presets = {};
  let lastConfig = null;

  function actionRow(action = { name: "", frames: 6, description: "" }) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><input class="a-name" placeholder="idle" value=""></td>
      <td><input class="a-frames" type="number" min="1" max="16" value=""></td>
      <td><input class="a-desc" placeholder="待机呼吸" value=""></td>
      <td><button class="ghost a-del" title="删除">✕</button></td>`;
    tr.querySelector(".a-name").value = action.name;
    tr.querySelector(".a-frames").value = action.frames;
    tr.querySelector(".a-desc").value = action.description;
    tr.querySelector(".a-del").onclick = () => tr.remove();
    return tr;
  }

  function fillActions(list) {
    const body = $("pr-actions");
    body.innerHTML = "";
    list.forEach((a) => body.appendChild(actionRow(a)));
  }

  function readActions() {
    return [...$("pr-actions").querySelectorAll("tr")].map((tr) => ({
      name: tr.querySelector(".a-name").value.trim(),
      frames: Number(tr.querySelector(".a-frames").value),
      description: tr.querySelector(".a-desc").value.trim(),
    })).filter((a) => a.name);
  }

  function card(item) {
    const el = document.createElement("article");
    el.className = "prompt-card";
    const rows = item.rows ? `<span class="badge">${item.rows.join(" / ")}</span>` : "";
    el.innerHTML = `
      <header><b></b><span class="badge">比例 ${item.aspect}</span>${rows}
        <button class="ghost copy">复制</button></header>
      <pre></pre>`;
    el.querySelector("b").textContent = `保存为 ${item.file}`;
    el.querySelector("pre").textContent = item.prompt;
    el.querySelector(".copy").onclick = async (e) => {
      await navigator.clipboard.writeText(item.prompt);
      e.target.textContent = "已复制 ✓";
      setTimeout(() => (e.target.textContent = "复制"), 1500);
    };
    return el;
  }

  function configCard(config) {
    const el = document.createElement("article");
    el.className = "prompt-card";
    el.innerHTML = `
      <header><b>对应的 sprite.json</b><span class="badge">生成图片后用它切图</span></header>
      <pre></pre>
      <div class="save-config">
        <input id="pr-asset-name" placeholder="素材名，如 archer">
        <button id="pr-save-config">保存为素材配置</button>
        <span class="status" id="pr-save-status"></span>
      </div>`;
    el.querySelector("pre").textContent = JSON.stringify(config, null, 2);
    el.querySelector("#pr-save-config").onclick = saveConfig;
    return el;
  }

  async function saveConfig() {
    const name = $("pr-asset-name").value.trim();
    const status = $("pr-save-status");
    try {
      await Api.put(`/api/assets/${encodeURIComponent(name)}/config`, { kind: "sprite", config: lastConfig });
      status.className = "status ok";
      status.textContent = `已保存。把图片按卡片上的文件名上传到「${name}」，再点处理。`;
      App.refreshAssets(name);
    } catch (err) {
      status.className = "status error";
      status.textContent = err.message;
    }
  }

  async function generate() {
    const kind = $("pr-kind").value;
    const body = { kind, style: $("pr-style").value.trim() };
    if (kind === "character") {
      Object.assign(body, {
        subject: $("pr-subject").value.trim(),
        actions: readActions(),
        target_height: Number($("pr-height").value),
      });
    } else {
      Object.assign(body, { theme: $("pr-theme").value.trim(), items: $("pr-items").value.trim() });
    }
    const status = $("pr-status");
    try {
      const res = await Api.post("/api/prompts", body);
      const out = $("pr-output");
      out.innerHTML = "";
      res.prompts.forEach((p) => out.appendChild(card(p)));
      lastConfig = res.config || null;
      if (lastConfig) out.appendChild(configCard(lastConfig));
      status.className = "status ok";
      status.textContent = `生成了 ${res.prompts.length} 条。每次生成都上传同一张参考图，角色更一致。`;
    } catch (err) {
      status.className = "status error";
      status.textContent = err.message;
    }
  }

  async function init() {
    presets = await Api.get("/api/presets");
    const select = $("pr-preset");
    Object.keys(presets).forEach((name) => select.add(new Option(name, name)));
    select.onchange = () => fillActions(presets[select.value]);
    fillActions(presets[select.value]);
    $("pr-style").value = "16位复古游戏风格，清晰像素颗粒，黑色描边";
    $("pr-add").onclick = () => $("pr-actions").appendChild(actionRow());
    $("pr-kind").onchange = () => {
      const isChar = $("pr-kind").value === "character";
      $("pr-character").hidden = !isChar;
      $("pr-environment").hidden = isChar;
    };
    $("pr-generate").onclick = generate;
  }

  return { init };
})();
