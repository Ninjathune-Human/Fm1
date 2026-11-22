// Maquette du module sample et scratch, au format du FM-1.
// Le dessin du boîtier, des molettes, des touches et de l'écran reprend buildPanel() de index.html (dépôt Fm1),
// lui-même adapté de la page de l'émulateur DUB-1 (sbegueria/fm1-dub, GPL-3.0). Sortie : SVG statiques.
import fs from "fs";

const OUT = process.argv[2] || ".";
const r2 = (v) => (typeof v === "number" ? +v.toFixed(2) : v);
const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
class N { constructor(tag, attrs) { this.tag = tag; this.attrs = attrs || {}; this.kids = []; this.text = null; } }
const ser = (n) => {
  const st = [], at = [];
  for (const [k, v] of Object.entries(n.attrs)) {
    if (v === "" || v == null) continue;
    if (k.includes("-") && !/^(aria|data)-/.test(k)) st.push(`${k}: ${r2(v)}`); else at.push(` ${k}="${esc(r2(v))}"`);
  }
  const a = at.join("") + (st.length ? ` style="${esc(st.join("; "))}"` : "");
  return `<${n.tag}${a}>${n.text != null ? esc(n.text) : ""}${n.kids.map(ser).join("")}</${n.tag}>`;
};

// ------------------------------------------------------------------ couleurs (coloris Menthe, setSkin)
const hex = (c) => [1, 3, 5].map((i) => parseInt(c.slice(i, i + 2), 16));
const mix = (a, b, t) => { const A = hex(a), B = hex(b); return "#" + A.map((v, i) => Math.round(v + (B[i] - v) * t).toString(16).padStart(2, "0")).join(""); };
const lit = (c, t) => mix(c, "#ffffff", t), dk = (c, t) => mix(c, "#000000", t);
const SK = { body: "#1d1d1f", rubber: "#98c7ba", ink: "#c4c5c8", cap: "#24302d", slot: "#0c1c18" };
const T = { bg: "#0a1210", fg: "#eef7f3", mute: "#84a299", acc: "#a3d6c7" };   // thème Green de l'écran
const LCD_FONT = "'Barlow Semi Condensed', 'Arial Narrow', sans-serif";
const CAP_FONT = "'M PLUS Rounded 1c', 'Arial Rounded MT Bold', 'Helvetica Neue', Arial, sans-serif";

// ------------------------------------------------------------------ l'impression du panneau, matrice 5 x 7
const DOT57 = {
  A: "01110 10001 10001 10001 11111 10001 10001", B: "11110 10001 10001 11110 10001 10001 11110", C: "01110 10001 10000 10000 10000 10001 01110",
  D: "11100 10010 10001 10001 10001 10010 11100", E: "11111 10000 10000 11110 10000 10000 11111", F: "11111 10000 10000 11110 10000 10000 10000",
  G: "01110 10001 10000 10111 10001 10001 01111", H: "10001 10001 10001 11111 10001 10001 10001", I: "01110 00100 00100 00100 00100 00100 01110",
  K: "10001 10010 10100 11000 10100 10010 10001", L: "10000 10000 10000 10000 10000 10000 11111", M: "10001 11011 10101 10101 10001 10001 10001",
  N: "10001 10001 11001 10101 10011 10001 10001", O: "01110 10001 10001 10001 10001 10001 01110", P: "11110 10001 10001 11110 10000 10000 10000",
  R: "11110 10001 10001 11110 10100 10010 10001", S: "01111 10000 10000 01110 00001 00001 11110", T: "11111 00100 00100 00100 00100 00100 00100",
  U: "10001 10001 10001 10001 10001 10001 01110", V: "10001 10001 10001 10001 10001 01010 00100", X: "10001 10001 01010 00100 01010 10001 10001",
  Y: "10001 10001 10001 01010 00100 00100 00100", Z: "11111 00001 00010 00100 01000 10000 11111",
  1: "00100 01100 00100 00100 00100 00100 01110", 2: "01110 10001 00001 00010 00100 01000 11111", 3: "11111 00010 00100 00010 00001 10001 01110",
  4: "00010 00110 01010 10010 11111 00010 00010", " ": "00000 00000 00000 00000 00000 00000 00000",
};
const DOT_W = 2.52, DOT_H = 2.62;
function dotMatrixPath(s, cx, top) {
  const runs = []; let lo = Infinity, hi = -Infinity;
  [...s].forEach((ch, i) => (DOT57[ch] || "").split(" ").forEach((row, r) => {
    for (let c = 0; c < 5; c++) {
      if (row[c] !== "1") continue;
      const col = i * 6 + c, last = runs[runs.length - 1];
      if (last && last.r === r && last.c1 === col - 1) last.c1 = col; else runs.push({ r, c0: col, c1: col });
      lo = Math.min(lo, col); hi = Math.max(hi, col);
    }
  }));
  const x0 = cx - ((hi - lo + 1) * DOT_W) / 2 - lo * DOT_W, f = (v) => +v.toFixed(2);
  return runs.map(({ r, c0, c1 }) => `M${f(x0 + c0 * DOT_W)} ${f(top + r * DOT_H)}h${f((c1 - c0 + 1) * DOT_W)}v${DOT_H}h${f(-(c1 - c0 + 1) * DOT_W)}z`).join("");
}

// ------------------------------------------------------------------ un panneau : le FM-1 ou le module
export function panel({ P, kind, lcd, anim }) {
  const VW = 1640, VH = 990, id = (n) => P + n, url = (n) => `url(#${P}${n})`;
  const root = new N("svg", { xmlns: "http://www.w3.org/2000/svg", viewBox: `0 0 ${VW} ${VH}`, width: "100%", height: "100%", class: P + "dev" });
  const el = (tag, attrs, parent) => { const e = new N(tag, attrs); parent.kids.push(e); return e; };
  const txt = (parent, s, attrs) => { const e = el("text", attrs, parent); e.text = s; return e; };
  const defs = el("defs", {}, root), base = el("g", {}, root), live = el("g", {}, root), over = el("g", {}, root);
  const grad = (n, stops, attrs = { x1: 0, y1: 0, x2: 0, y2: 1 }, k = "linearGradient") => {
    const g = el(k, Object.assign({ id: id(n) }, attrs), defs);
    for (const [o, c, a = 1] of stops) el("stop", { offset: o, "stop-color": c, "stop-opacity": a }, g);
  };
  const blur = (n, sd) => { const f = el("filter", { id: id(n), x: "-50%", y: "-50%", width: "200%", height: "200%" }, defs); el("feGaussianBlur", { stdDeviation: sd }, f); };
  const b = SK.body, r = SK.rubber;
  grad("gBody", [[0, lit(b, 0.1)], [0.42, b], [1, dk(b, 0.45)]]);
  grad("gBodyX", [[0, "#ffffff", 0.06], [0.45, "#ffffff", 0], [1, "#000000", 0.38]], { x1: 0, y1: 0, x2: 1, y2: 0 });
  grad("gBodyEdge", [[0, lit(b, 0.45)], [0.06, lit(b, 0.08)], [0.5, dk(b, 0.3)], [1, "#000000"]]);
  grad("gPlate", [[0, lit(r, 0.09)], [0.5, r], [1, dk(r, 0.06)]]);
  grad("gPlateX", [[0, "#ffffff", 0.07], [0.55, "#ffffff", 0], [1, "#0b2a22", 0.12]], { x1: 0, y1: 0, x2: 1, y2: 0 });
  grad("gPlateEdge", [[0, "#ffffff", 0.75], [0.08, "#ffffff", 0.16], [0.6, "#ffffff", 0], [1, dk(r, 0.6), 0.55]]);
  grad("gWall", [[0, dk(r, 0.16)], [1, dk(r, 0.42)]]);
  grad("gCap", [[0, lit(r, 0.22)], [0.18, lit(r, 0.07)], [0.75, r], [1, dk(r, 0.07)]]);
  grad("gCapRim", [[0, "#ffffff", 0.85], [0.22, "#ffffff", 0.1], [0.75, "#ffffff", 0], [1, dk(r, 0.5), 0.35]]);
  grad("gKey", [[0, lit(r, 0.06)], [0.5, r], [1, dk(r, 0.06)]]);
  grad("gKeyRim", [[0, "#ffffff", 0.8], [0.35, "#ffffff", 0.06], [0.65, dk(r, 0.6), 0.05], [1, dk(r, 0.6), 0.5]], { x1: 0.2, y1: 0, x2: 0.8, y2: 1 });
  grad("gKeyDish", [[0, dk(r, 0.55), 0.16], [0.35, dk(r, 0.55), 0], [1, "#ffffff", 0.12]]);
  grad("gSlot", [[0, dk(SK.slot, 0.12)], [1, SK.slot]]);
  grad("gSlotLit", [[0, "#ffffff"], [1, "#f1fffb"]]);
  grad("gSpotG", [[0, "#7dffa0", 0.9], [0.45, "#7dffa0", 0.45], [1, "#7dffa0", 0]], {}, "radialGradient");
  grad("gSpotR", [[0, "#ff6a5c", 0.9], [0.45, "#ff6a5c", 0.45], [1, "#ff6a5c", 0]], {}, "radialGradient");
  grad("gKnobFace", [[0, "#3b3b3f"], [0.55, "#262629"], [1, "#1a1a1c"]], { x1: 0.15, y1: 0, x2: 0.85, y2: 1 });
  grad("gKnobSheen", [[0, "#ffffff", 0], [0.42, "#ffffff", 0.07], [0.5, "#ffffff", 0.11], [0.58, "#ffffff", 0.07], [1, "#ffffff", 0]], { x1: 0, y1: 0, x2: 1, y2: 1 });
  grad("gKnobChamfer", [[0, "#d8d8dc", 0.95], [0.35, "#8a8a90", 0.55], [0.65, "#1c1c1e", 0.2], [1, "#000000", 0.6]], { x1: 0.1, y1: 0, x2: 0.8, y2: 1 });
  grad("gKnobSkirt", [[0, "#2c2c30"], [0.5, "#121214"], [1, "#050506"]], { x1: 0, y1: 0, x2: 1, y2: 0 });
  grad("gBezel", [[0, "#3c3d40"], [0.35, "#141517"], [1, "#050506"]], { x1: 0, y1: 0, x2: 1, y2: 1 });
  grad("gBezelEdge", [[0, "#6e6f73"], [0.18, "#333437"], [0.6, "#141416"], [1, "#000000"]]);
  grad("gGlass", [[0, "#ffffff", 0.17], [0.35, "#ffffff", 0.075], [0.353, "#ffffff", 0], [1, "#ffffff", 0]], { x1: 0, y1: 0, x2: 0.78, y2: 1 });
  grad("gGlassTop", [[0, "#ffffff", 0.12], [1, "#ffffff", 0]], { cx: 0.22, cy: 0, r: 0.7 }, "radialGradient");
  grad("gVinyl", [[0, "#2a2a2d"], [0.5, "#111113"], [1, "#050506"]], { x1: 0.1, y1: 0, x2: 0.9, y2: 1 });
  grad("gVinylSheen", [[0, "#ffffff", 0], [0.46, "#ffffff", 0.09], [0.5, "#ffffff", 0.16], [0.54, "#ffffff", 0.09], [1, "#ffffff", 0]], { x1: 0, y1: 0, x2: 1, y2: 1 });
  grad("gLedHalo", [[0, "#ffffff", 0.95], [0.4, "#f4fffb", 0.5], [1, "#f4fffb", 0]], {}, "radialGradient");
  grad("gTouch", [[0, "#ffffff", 1], [0.18, "#f4fffb", 0.9], [0.45, T.acc, 0.35], [1, T.acc, 0]], {}, "radialGradient");
  blur("fShadow", 9); blur("fShadowS", 5); blur("fGlow", 7); blur("fGlowS", 3.5); blur("fSoft", 2.5);
  const noise = el("filter", { id: id("fNoise"), x: 0, y: 0, width: "100%", height: "100%" }, defs);
  el("feTurbulence", { type: "fractalNoise", baseFrequency: 0.9, numOctaves: 2, seed: 7, stitchTiles: "stitch" }, noise);
  el("feColorMatrix", { type: "matrix", values: "0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 0.9 -0.42" }, noise);
  el("rect", { x: 0, y: 0, width: VW, height: VH, rx: 96 }, el("clipPath", { id: id("cBody") }, defs));

  // le boîtier
  el("rect", { x: 0, y: 0, width: VW, height: VH, rx: 96, fill: url("gBody") }, base);
  el("rect", { x: 0, y: 0, width: VW, height: VH, rx: 96, fill: url("gBodyX") }, base);
  el("rect", { x: 0, y: 0, width: VW, height: VH, fill: "#ffffff", filter: url("fNoise"), opacity: 0.05, "clip-path": url("cBody") }, base);
  el("rect", { x: 1.5, y: 1.5, width: VW - 3, height: VH - 3, rx: 94.5, fill: "none", stroke: url("gBodyEdge"), "stroke-width": 3 }, base);
  el("rect", { x: 6, y: 6, width: VW - 12, height: VH - 12, rx: 90, fill: "none", stroke: "#ffffff", "stroke-opacity": 0.035, "stroke-width": 1.5 }, base);

  const label = (cx, top, s) => el("path", { d: dotMatrixPath(s, cx, top), fill: SK.ink }, base);
  const plate = (x, y, w, h, rx) => {
    el("rect", { x: x + 4, y: y + 12, width: w - 8, height: h, rx, fill: "#000000", opacity: 0.85, filter: url("fShadow") }, base);
    el("rect", { x, y: y + 4, width: w, height: h, rx, fill: dk(r, 0.45) }, base);
    el("rect", { x, y, width: w, height: h, rx, fill: url("gPlate") }, base);
    el("rect", { x, y, width: w, height: h, rx, fill: url("gPlateX") }, base);
    el("rect", { x: x + 1, y: y + 1, width: w - 2, height: h - 2, rx: rx - 1, fill: "none", stroke: url("gPlateEdge"), "stroke-width": 2 }, base);
  };
  const dot = (x, y) => el("circle", { cx: x, cy: y, r: 4.2, fill: dk(r, 0.8) }, base);

  // les molettes
  const KR = 34, KH = 11, KX = 3, KN = 18;
  const knob = (cx, cy, name, hasDot, lx = cx, ly = cy - 78, angle = 0) => {
    label(lx, ly, name);
    const top = cy - KH / 2, bot = cy + KH / 2;
    el("ellipse", { cx: cx + 9, cy: bot + 12, rx: KR + 4, ry: KR - 2, fill: "#000000", opacity: 0.85, filter: url("fShadow") }, base);
    el("circle", { cx: cx + 2, cy: bot + 2, r: KR + 1.5, fill: "#000000", opacity: 0.7, filter: url("fShadowS") }, base);
    const skirt = `M${cx - KR} ${top}A${KR} ${KR} 0 0 0 ${cx + KR} ${top}L${cx + KR + KX} ${bot}A${KR} ${KR} 0 0 1 ${cx - KR + KX} ${bot}Z`;
    el("path", { d: skirt, fill: url("gKnobSkirt") }, base);
    const cid = "cK" + name.replace(/[^A-Z0-9]/g, "");
    el("path", { d: skirt }, el("clipPath", { id: id(cid) }, defs));
    const g = el("g", {}, live), kg = el("g", { "clip-path": url(cid) }, g);
    let d = "", gl = "";
    for (let i = 0; i < KN; i++) {
      const a = ((i * 360) / KN + angle) * (Math.PI / 180), sn = Math.sin(a), cs = Math.cos(a);
      if (sn < 0.08) continue;
      const x = cx + KR * cs, y0 = top + KR * sn - 1, y1 = y0 + KH + 2;
      d += `M${x.toFixed(2)} ${y0.toFixed(2)}L${(x + KX).toFixed(2)} ${y1.toFixed(2)}`;
      if (cs > 0.1) { const xg = x - 2.1 * sn; gl += `M${xg.toFixed(2)} ${(y0 + 1.5).toFixed(2)}L${(xg + KX).toFixed(2)} ${(y1 - 1.5).toFixed(2)}`; }
    }
    el("path", { d, fill: "none", stroke: "#000000", "stroke-opacity": 0.85, "stroke-width": 3.2 }, kg);
    el("path", { d: gl, fill: "none", stroke: "#7c7c82", "stroke-width": 1.1 }, kg);
    el("circle", { cx, cy: top, r: KR, fill: url("gKnobFace") }, g);
    el("circle", { cx, cy: top, r: KR - 1, fill: url("gKnobSheen"), opacity: 0.55 }, g);
    el("circle", { cx, cy: top, r: KR - 1.2, fill: "none", stroke: url("gKnobChamfer"), "stroke-width": 2.4 }, g);
    el("circle", { cx, cy: top, r: KR - 4.5, fill: "none", stroke: "#000000", "stroke-opacity": 0.35, "stroke-width": 1 }, g);
    const ind = el("g", { transform: `rotate(${angle} ${cx} ${top})` }, g);
    if (hasDot) el("circle", { cx, cy: top - KR + 11, r: 4.2, fill: "#f6f6f6" }, ind);
    else {
      el("line", { x1: cx, y1: top - KR + 6, x2: cx, y2: top - KR + 19, stroke: "#000000", "stroke-opacity": 0.8, "stroke-width": 3.2, "stroke-linecap": "round" }, ind);
      el("line", { x1: cx + 1.3, y1: top - KR + 7, x2: cx + 1.3, y2: top - KR + 18.5, stroke: "#9a9aa0", "stroke-opacity": 0.55, "stroke-width": 1, "stroke-linecap": "round" }, ind);
    }
  };

  // les boutons : touches menthe dont la légende s'éclaire (hue : "green", "red" ; cls : une animation)
  const button = (cx, cy, w, h, name, two, hue, cls) => {
    const x = cx - w / 2, y = cy - h / 2, rx = 15;
    el("rect", { x: x + 6, y: y + 12, width: w - 6, height: h, rx, fill: dk(r, 0.72), opacity: 0.75, filter: url("fShadowS") }, base);
    el("rect", { x, y: y + 5, width: w, height: h, rx, fill: url("gWall") }, base);
    const g = el("g", {}, live);
    el("rect", { x, y, width: w, height: h, rx, fill: url("gCap") }, g);
    el("rect", { x: x + 1, y: y + 1, width: w - 2, height: h - 2, rx: rx - 1, fill: "none", stroke: url("gCapRim"), "stroke-width": 2 }, g);
    const lines = two ? [[cy - 8, name], [cy + 22, two]] : [[cy + 8, name]];
    const lc = hue === "green" ? "#8dffa4" : hue === "red" ? "#ff5246" : null, lg = hue === "green" ? "#5dff83" : "#ff4a3d";
    const t = (yy, s, fill, parent) => txt(parent, s, { x: cx, y: yy, "text-anchor": "middle", "font-family": CAP_FONT, "font-weight": 700, "font-size": 19, fill });
    for (const [yy, s] of lines) t(yy, s, SK.cap, g);
    if (two) el("rect", { x: cx - 26, y: cy - 4.5, width: 52, height: 2.2, rx: 1.1, fill: SK.cap }, g);
    if (lc) {                                            // allumé : la tache, le halo et la légende dans la couleur de la LED
      const lt = el("g", { class: cls || "" }, g);
      el("ellipse", { cx, cy, rx: w * 0.42, ry: h * 0.4, fill: url(hue === "green" ? "gSpotG" : "gSpotR"), opacity: 0.35 }, lt);
      const glow = el("g", { filter: url("fGlowS"), opacity: 0.5 }, lt);
      for (const [yy, s] of lines) { const e = t(yy, s, lg, glow); e.attrs.stroke = lg; e.attrs["stroke-width"] = 3; e.attrs["stroke-linejoin"] = "round"; }
      for (const [yy, s] of lines) t(yy, s, lc, lt);
      if (two) el("rect", { x: cx - 26, y: cy - 4.5, width: 52, height: 2.2, rx: 1.1, fill: lc }, lt);
    }
  };

  // les touches : pilules à fente lumineuse (lamp : intensité fixe, cls : une animation)
  const key = (cx, cy, h, slotY, slotH, cap, lamp = 0, cls) => {
    const w = 74, x = cx - w / 2, y = cy - h / 2, rx = w / 2;
    el("rect", { x: x + 6, y: y + 13, width: w - 4, height: h, rx, fill: dk(r, 0.72), opacity: 0.65, filter: url("fShadowS") }, base);
    el("rect", { x, y: y + 6, width: w, height: h, rx, fill: url("gWall") }, base);
    const g = el("g", {}, live);
    el("rect", { x, y, width: w, height: h, rx, fill: url("gKey") }, g);
    el("rect", { x: x + 7, y: y + 7, width: w - 14, height: h - 14, rx: rx - 7, fill: url("gKeyDish") }, g);
    el("rect", { x: x + 2, y: y + 2, width: w - 4, height: h - 4, rx: rx - 2, fill: "none", stroke: url("gKeyRim"), "stroke-width": 3.2 }, g);
    el("rect", { x: cx - 5, y: slotY, width: 10, height: slotH, rx: 5, fill: url("gSlot") }, g);
    if (lamp || cls) {
      const lg = el("g", cls ? { class: cls, opacity: 0 } : { opacity: lamp }, g);
      el("rect", { x: cx - 13, y: slotY - 12, width: 26, height: slotH + 24, rx: 13, fill: "#ffffff", filter: url("fGlow"), opacity: 0.85 }, lg);
      el("rect", { x: cx - 5, y: slotY, width: 10, height: slotH, rx: 5, fill: url("gSlotLit") }, lg);
    }
    if (cap) txt(g, cap, { x: cx, y: slotY + slotH + 29, "text-anchor": "middle", "font-family": CAP_FONT, "font-weight": 700, "font-size": 16.5, fill: "#294740" });
  };

  // l'écran : un verre dans un cadre noir poli ; W la largeur du cadre (390 sur le FM-1)
  const screen = (W, content) => {
    el("rect", { x: 426, y: 82, width: W, height: 390, rx: 52, fill: "#000000", opacity: 0.9, filter: url("fShadow") }, base);
    el("rect", { x: 422, y: 70, width: W, height: 390, rx: 50, fill: url("gBezel") }, base);
    el("rect", { x: 423, y: 71, width: W - 2, height: 388, rx: 49, fill: "none", stroke: url("gBezelEdge"), "stroke-width": 2 }, base);
    el("rect", { x: 434, y: 82, width: W - 24, height: 366, rx: 40, fill: "#060607" }, base);
    el("rect", { x: 465, y: 113, width: W - 86, height: 304, rx: 8, fill: "#000000" }, base);
    const pw = W - 90, px = (pw / 300) * 240;               // 1,25 unité par pixel, comme le FM-1 (240 x 240)
    const s = el("svg", { x: 467, y: 115, width: pw, height: 300, viewBox: `0 0 ${Math.round(px)} 240`, overflow: "hidden" }, live);
    content(s, Math.round(px));
    el("rect", { x: 422, y: 70, width: W, height: 390, rx: 50, fill: url("gGlass") }, over);   // le reflet du verre
    el("rect", { x: 422, y: 70, width: W, height: 390, rx: 50, fill: url("gGlassTop") }, over);
  };

  // la platine : un puits poli, la couronne de 32 LED, le disque et son macaron menthe
  const platter = (PX, PY, RW, RL, RD) => {
    const k = RD / 140;
    el("circle", { cx: PX + 5, cy: PY + 10, r: RW + 2, fill: "#000000", opacity: 0.9, filter: url("fShadow") }, base);
    el("circle", { cx: PX, cy: PY, r: RW, fill: url("gBezel") }, base);
    el("circle", { cx: PX, cy: PY, r: RW - 1, fill: "none", stroke: url("gBezelEdge"), "stroke-width": 2 }, base);
    el("circle", { cx: PX, cy: PY, r: RW - 10, fill: "#060607" }, base);
    const ring = el("g", {}, live), lit = el("g", { class: anim ? P + "ring" : "", style: `transform-origin: ${PX}px ${PY}px` }, live);
    for (let i = 0; i < 32; i++) {
      const a = (i / 32) * Math.PI * 2 - Math.PI / 2;
      el("circle", { cx: PX + RL * Math.cos(a), cy: PY + RL * Math.sin(a), r: 3.6, fill: "#1a2622" }, ring);
    }
    [[0, 1], [-1, 0.55], [-2, 0.28], [-3, 0.12]].forEach(([q, o]) => {
      const a = (q / 32) * Math.PI * 2 - Math.PI / 2, x = PX + RL * Math.cos(a), y = PY + RL * Math.sin(a);
      el("circle", { cx: x, cy: y, r: 12, fill: url("gLedHalo"), opacity: o * 0.8 }, lit);
      el("circle", { cx: x, cy: y, r: 3.6, fill: "#ffffff", opacity: o }, lit);
    });
    const disc = el("g", { class: anim ? P + "spin" : "", style: `transform-origin: ${PX}px ${PY}px` }, live);
    el("circle", { cx: PX, cy: PY, r: RD, fill: url("gVinyl") }, disc);
    for (let rr = 66 * k; rr < RD - 4; rr += 5.5) el("circle", { cx: PX, cy: PY, r: rr, fill: "none", stroke: "#ffffff", "stroke-opacity": Math.round(rr) % 3 ? 0.035 : 0.06, "stroke-width": 1 }, disc);
    el("circle", { cx: PX, cy: PY, r: 58 * k, fill: url("gCap") }, disc);
    el("circle", { cx: PX, cy: PY, r: 58 * k - 1, fill: "none", stroke: url("gCapRim"), "stroke-width": 2 }, disc);
    el("rect", { x: PX - 3, y: PY - 52 * k, width: 6, height: 22 * k, rx: 3, fill: SK.cap }, disc);
    txt(disc, "33", { x: PX, y: PY + 36 * k, "text-anchor": "middle", "font-family": CAP_FONT, "font-weight": 700, "font-size": 15 * k, fill: "#294740" });
    el("circle", { cx: PX, cy: PY, r: RD, fill: url("gVinylSheen") }, live);
    el("circle", { cx: PX, cy: PY, r: 6, fill: "#c9cacd" }, live);
    el("circle", { cx: PX - 1.5, cy: PY - 1.5, r: 2.2, fill: "#ffffff", opacity: 0.8 }, live);
  };

  if (kind === "fm1") {
    knob(135, 147, "MASTER", true, 136.5, 69, 40); knob(308, 147, "SELECT", false, 310.5, 69);
    knob(135, 320, "PRESETS", false, 136.5, 241); knob(308, 320, "ALGORITHM", false, 310.5, 241);
    [925, 1107, 1290, 1475].forEach((x, i) => knob(x, 147, "KNOB" + (i + 1), false, x - 1, 69));
    plate(95, 420, 252, 82, 20);
    button(156, 457, 94, 58, "OCT-"); button(286, 457, 94, 58, "OCT+");
    plate(875, 272, 652, 228, 34);
    const ROW1 = ["FX", "SEL", "ENV", "LFO", "EDIT", "GLO"], ROW2 = ["HOME", "SAVE", "ARP", "SEQ", "PLAY", "REC"];
    const BX = [945, 1048, 1151, 1253, 1356, 1459];
    dot(1202, 384);
    for (let i = 0; i < 6; i++) { button(BX[i], 329, 82, 80, ROW1[i]); if (ROW2[i] === "PLAY") button(BX[i], 435, 82, 80, "PLAY", "STOP", "green", anim ? P + "beat" : ""); else button(BX[i], 435, 82, 80, ROW2[i]); }
    plate(62, 560, 1516, 365, 50);
    for (const x of [448, 727, 1095, 1373]) dot(x, 741);
    const WHITE = 16, BLACK_AFTER = [0, 1, 2, 4, 5, 7, 8, 9, 11, 12, 14], BL = ["OP1", "OP2", "OP3", "OP4", "OP5", "OP6", "PIT", "GLD", "MONO", "POLY", ""];
    for (let i = 0; i < WHITE; i++) key(123 + 93 * i, 825, 152, 781, 85, null, 0, anim && i % 4 === 0 ? P + "kick" : null);
    BLACK_AFTER.forEach((a, k) => key(123 + 93 * (a + 0.5), 659, 150, 621, 43, BL[k]));
    screen(390, (s, w) => lcdFm1(s, w));
  } else if (kind === "module2") {
    // le module, version courte : MASTER et SELECT à leur place, quatre touches, l'écran tactile ; la platine en haut à
    // droite ; en bas, les 16 pads et une grande zone XY
    knob(135, 147, "MASTER", true, 136.5, 69, 40); knob(308, 147, "SELECT", false, 310.5, 69);
    plate(95, 262, 252, 228, 34);
    button(156, 319, 100, 80, "EDIT"); button(286, 319, 100, 80, "SEND");
    button(156, 425, 100, 80, "PLAY", "STOP", "green", anim ? P + "beat" : ""); button(286, 425, 100, 80, "REC");
    plate(62, 560, 810, 365, 50);
    dot(448, 741);
    for (let j = 0; j < 16; j++) {
      const col = j % 8, row = j >> 3, cx = 123 + 93 * col, cy = row ? 825 : 659, slotY = row ? 787 : 621;
      key(cx, cy, row ? 152 : 150, slotY, 43, String(j + 1), 0, anim ? `${P}pad ${P}pad${j}` : null);
    }
    // la zone XY, agrandie
    const X0 = 902, Y0 = 560, XW = 676, XH = 365;
    el("rect", { x: X0 + 4, y: Y0 + 10, width: XW, height: XH, rx: 44, fill: "#000000", opacity: 0.9, filter: url("fShadow") }, base);
    el("rect", { x: X0, y: Y0, width: XW, height: XH, rx: 44, fill: url("gBezel") }, base);
    el("rect", { x: X0 + 1, y: Y0 + 1, width: XW - 2, height: XH - 2, rx: 43, fill: "none", stroke: url("gBezelEdge"), "stroke-width": 2 }, base);
    el("rect", { x: X0 + 12, y: Y0 + 12, width: XW - 24, height: XH - 24, rx: 34, fill: T.bg }, base);
    el("rect", { x: X0 + 12, y: Y0 + 12, width: XW - 24, height: XH - 24, rx: 34 }, el("clipPath", { id: id("cXY") }, defs));
    const xy = el("g", { "clip-path": url("cXY") }, live);
    for (let i = 1; i < 12; i++) el("line", { x1: X0 + 12 + ((XW - 24) * i) / 12, y1: Y0 + 20, x2: X0 + 12 + ((XW - 24) * i) / 12, y2: Y0 + XH - 20, stroke: T.acc, "stroke-opacity": i === 6 ? 0.22 : 0.07, "stroke-width": 1 }, xy);
    for (let i = 1; i < 6; i++) el("line", { x1: X0 + 20, y1: Y0 + 12 + ((XH - 24) * i) / 6, x2: X0 + XW - 20, y2: Y0 + 12 + ((XH - 24) * i) / 6, stroke: T.acc, "stroke-opacity": 0.07, "stroke-width": 1 }, xy);
    const small = (s, x, y, anchor, fill = T.mute) => txt(xy, s, { x, y, "text-anchor": anchor, "font-family": LCD_FONT, "font-weight": 600, "font-size": 16, fill, "letter-spacing": 1 });
    small("FILTER", X0 + 30, Y0 + 44, "start", T.acc); small("RES", X0 + 30, Y0 + 66, "start");
    small("LOW-PASS", X0 + 30, Y0 + XH - 30, "start"); small("HIGH-PASS", X0 + XW - 30, Y0 + XH - 30, "end");
    small("2 FINGERS  ECHO", X0 + XW - 30, Y0 + 44, "end");
    const pt = el("g", { class: anim ? P + "drift2" : "" }, xy);
    const tx = X0 + XW * 0.6, ty = Y0 + XH * 0.45;
    el("line", { x1: X0 + 14, y1: ty, x2: X0 + XW - 14, y2: ty, stroke: T.acc, "stroke-opacity": 0.45, "stroke-width": 1.4 }, pt);
    el("line", { x1: tx, y1: Y0 + 14, x2: tx, y2: Y0 + XH - 14, stroke: T.acc, "stroke-opacity": 0.45, "stroke-width": 1.4 }, pt);
    el("circle", { cx: tx, cy: ty, r: 58, fill: url("gTouch"), opacity: 0.55 }, pt);
    el("circle", { cx: tx, cy: ty, r: 10, fill: "#ffffff" }, pt);
    el("rect", { x: X0 + 12, y: Y0 + 12, width: XW - 24, height: XH * 0.4, rx: 34, fill: url("gGlass"), opacity: 0.6 }, over);
    // la platine, plus grande, en haut à droite
    const PX = 1336, PY = 272, RW = 206, RL = 192, RD = 174;
    platter(PX, PY, RW, RL, RD);
    screen(616, (s, w) => lcdEdit(s, w, anim ? P : null));
  } else {
    // le module : la même colonne de molettes, un écran plus large, KNOB1-4 et les touches resserrés à droite ;
    // en bas, 16 pads (deux rangées de huit), la zone XY et la platine
    knob(135, 147, "MASTER", true, 136.5, 69, 40); knob(308, 147, "SELECT", false, 310.5, 69);
    knob(135, 320, "SAMPLE", false, 136.5, 241); knob(308, 320, "ZOOM", false, 310.5, 241);
    plate(95, 420, 252, 82, 20);
    button(156, 457, 94, 58, "BANK-"); button(286, 457, 94, 58, "BANK+");
    const W = 616;
    const KX4 = [1118, 1250, 1382, 1514];
    KX4.forEach((x, i) => knob(x, 147, "KNOB" + (i + 1), false, x - 1, 69));
    plate(1070, 272, 512, 228, 34);
    const ROW1 = ["FX", "SRC", "CHOP", "REV", "EDIT", "SEND"], ROW2 = ["HOME", "SAVE", "ROLL", "CUT", "PLAY", "REC"];
    const BX = [1116, 1200, 1284, 1368, 1452, 1536];
    dot(1326, 384);
    for (let i = 0; i < 6; i++) {
      button(BX[i], 329, 74, 80, ROW1[i]);
      if (ROW2[i] === "PLAY") button(BX[i], 435, 74, 80, "PLAY", "STOP", "green", anim ? P + "beat" : "");
      else button(BX[i], 435, 74, 80, ROW2[i]);
    }
    // les pads : la plaque, deux rangées de huit, numérotées ; une LED court sur la tranche jouée
    plate(62, 560, 810, 365, 50);
    dot(448, 741);
    for (let j = 0; j < 16; j++) {
      const col = j % 8, row = j >> 3, cx = 123 + 93 * col, cy = row ? 825 : 659, slotY = row ? 787 : 621;
      key(cx, cy, row ? 152 : 150, slotY, 43, String(j + 1), j === 4 ? 0.28 : 0, anim ? `${P}pad ${P}pad${j}` : null);
    }
    // la zone XY : un verre sensible, comme celui de l'écran, encastré dans le boîtier
    const X0 = 900, Y0 = 590, XW = 292, XH = 322;
    label(X0 + XW / 2, 560, "FILTER XY");
    el("rect", { x: X0 + 4, y: Y0 + 10, width: XW, height: XH, rx: 34, fill: "#000000", opacity: 0.9, filter: url("fShadow") }, base);
    el("rect", { x: X0, y: Y0, width: XW, height: XH, rx: 34, fill: url("gBezel") }, base);
    el("rect", { x: X0 + 1, y: Y0 + 1, width: XW - 2, height: XH - 2, rx: 33, fill: "none", stroke: url("gBezelEdge"), "stroke-width": 2 }, base);
    el("rect", { x: X0 + 12, y: Y0 + 12, width: XW - 24, height: XH - 24, rx: 24, fill: T.bg }, base);
    el("rect", { x: X0 + 12, y: Y0 + 12, width: XW - 24, height: XH - 24, rx: 24 }, el("clipPath", { id: id("cXY") }, defs));
    const xy = el("g", { "clip-path": url("cXY") }, live);
    for (let i = 1; i < 6; i++) {
      el("line", { x1: X0 + 12 + ((XW - 24) * i) / 6, y1: Y0 + 20, x2: X0 + 12 + ((XW - 24) * i) / 6, y2: Y0 + XH - 20, stroke: T.acc, "stroke-opacity": i === 3 ? 0.22 : 0.07, "stroke-width": 1 }, xy);
      el("line", { x1: X0 + 20, y1: Y0 + 12 + ((XH - 24) * i) / 6, x2: X0 + XW - 20, y2: Y0 + 12 + ((XH - 24) * i) / 6, stroke: T.acc, "stroke-opacity": 0.07, "stroke-width": 1 }, xy);
    }
    const small = (s, x, y, anchor) => txt(xy, s, { x, y, "text-anchor": anchor, "font-family": LCD_FONT, "font-weight": 600, "font-size": 15, fill: T.mute, "letter-spacing": 1 });
    small("LOW-PASS", X0 + 26, Y0 + XH - 26, "start"); small("HIGH-PASS", X0 + XW - 26, Y0 + XH - 26, "end"); small("RES", X0 + 26, Y0 + 40, "start");
    const pt = el("g", { class: anim ? P + "drift" : "" }, xy);
    const tx = X0 + XW * 0.63, ty = Y0 + XH * 0.42;
    el("line", { x1: X0 + 14, y1: ty, x2: X0 + XW - 14, y2: ty, stroke: T.acc, "stroke-opacity": 0.45, "stroke-width": 1.4 }, pt);
    el("line", { x1: tx, y1: Y0 + 14, x2: tx, y2: Y0 + XH - 14, stroke: T.acc, "stroke-opacity": 0.45, "stroke-width": 1.4 }, pt);
    el("circle", { cx: tx, cy: ty, r: 46, fill: url("gTouch"), opacity: 0.55 }, pt);
    el("circle", { cx: tx, cy: ty, r: 9, fill: "#ffffff" }, pt);
    el("rect", { x: X0 + 12, y: Y0 + 12, width: XW - 24, height: XH * 0.4, rx: 24, fill: url("gGlass"), opacity: 0.6 }, over);

    // la platine : un puits poli, la couronne de 32 LED, le disque et son macaron menthe
    label(1404, 560, "SCRATCH");
    platter(1404, 748, 168, 156, 140);
    screen(W, (s, w) => (lcd === "capture" ? lcdCapture : lcd === "send" ? lcdSend : lcdEdit)(s, w, anim ? P : null));
  }
  return { svg: ser(root), P };
}

// ------------------------------------------------------------------ l'écran, en pixels du LCD (240 de haut)
const mk = (parent) => {
  const el = (tag, attrs) => { const e = new N(tag, attrs); parent.kids.push(e); return e; };
  const text = (s, x, y, wgt, size, fill, anchor = "start", extra = {}) => { const e = el("text", Object.assign({ x, y, "font-family": LCD_FONT, "font-weight": wgt, "font-size": size, fill, "text-anchor": anchor }, extra)); e.text = s; return e; };
  const sub = (tag, attrs) => { const e = el(tag, attrs); return mk(e); };
  return { el, text, sub, node: parent };
};
// l'en-tête aux quatre colonnes de FM-1+VA : nom, barre, valeur ; la colonne choisie en blanc
function header(c, w, cols, sel = 0) {
  const cw = w / 4;
  cols.forEach(([lab, val, bar], k) => {
    const x = k * cw, act = k === sel;
    c.text(lab, x + cw / 2, 14, 600, 11, act ? "#ffffff" : T.mute, "middle");
    if (bar != null) {
      c.el("rect", { x: x + 10, y: 20, width: cw - 20, height: 4, fill: T.fg, opacity: 0.2 });
      c.el("rect", { x: x + 10, y: 20, width: (cw - 20) * bar, height: 4, fill: act ? "#ffffff" : T.acc });
      c.text(val, x + cw / 2, 45, 600, 20, act ? "#ffffff" : T.fg, "middle");
    } else c.text(val, x + cw / 2, 42, 600, 15, act ? "#ffffff" : T.fg, "middle");
  });
  c.el("rect", { x: 0, y: 54, width: w, height: 1, fill: T.mute, opacity: 0.3 });
}
function battery(c, w) {
  c.el("rect", { x: w - 36, y: 214, width: 24, height: 12, rx: 2.5, fill: "none", stroke: T.mute, "stroke-width": 1.4 });
  c.el("rect", { x: w - 11.5, y: 218, width: 2, height: 4, fill: T.mute });
  for (let i = 0; i < 3; i++) c.el("rect", { x: w - 33 + i * 7, y: 217, width: 5, height: 6, fill: T.mute });
}
// une forme d'onde de boucle de batterie, déterministe : des attaques qui décroissent, un peu de bruit
function loopEnv(n, seed = 3) {
  let s = seed; const rnd = () => ((s = (s * 16807) % 2147483647) / 2147483647);
  const hits = [0, 0.125, 0.25, 0.3125, 0.375, 0.5, 0.625, 0.6875, 0.75, 0.875, 0.9375];
  const amp = [1, 0.55, 0.85, 0.4, 0.6, 1, 0.5, 0.45, 0.85, 0.55, 0.4];
  return Array.from({ length: n }, (_, i) => {
    const t = i / n; let v = 0.06 + 0.05 * rnd();
    hits.forEach((h, k) => { const d = t - h; if (d >= 0) v += amp[k] * Math.exp(-d * (k % 2 ? 60 : 22)); });
    return Math.min(1, v * (0.85 + 0.3 * rnd()));
  });
}
function wave(c, x0, y0, w, h, env, colorAt) {
  const mid = y0 + h / 2, n = env.length, step = w / n;
  env.forEach((v, i) => { const hh = Math.max(1, v * (h / 2 - 2)); c.el("rect", { x: x0 + i * step, y: mid - hh, width: Math.max(1, step * 0.62), height: hh * 2, fill: colorAt(i / n) }); });
}

function lcdFm1(s, w) {                               // FM-1+VA, la page d'accueil
  const c = mk(s);
  c.el("rect", { x: 0, y: 0, width: w, height: 240, fill: T.bg });
  header(c, w, [["BRIGHT", "68", 0.68], ["FDBK", "4", 0.57], ["ATK", "3", 0.03], ["REL", "39", 0.39]]);
  c.text("Knobs: Preset", 10, 70, 500, 13, T.mute);
  let d = ""; for (let i = 0; i <= 220; i++) { const y = 138 - 34 * Math.sin(i / 220 * Math.PI * 6) * Math.exp(-i / 260); d += (i ? "L" : "M") + (10 + i) + " " + y.toFixed(1); }
  c.el("path", { d, fill: "none", stroke: T.acc, "stroke-width": 1.6 });
  c.text("001 PIANO 1", 10, 226, 600, 18, T.fg);
  battery(c, w);
}

function lcdEdit(s, w, P) {                           // ÉDITION : la tranche 5 sur 16 de S01
  const c = mk(s);
  c.el("rect", { x: 0, y: 0, width: w, height: 240, fill: T.bg });
  header(c, w, [["START", "1.20s", 0.24], ["LENGTH", "480ms", 0.12], ["PITCH", "+0", 0.5], ["GAIN", "92", 0.92]]);
  c.text("Slice 05 / 16  ·  auto chop", 10, 70, 500, 13, T.mute);
  c.text("120 BPM", w - 10, 70, 600, 13, T.acc, "end");
  const X0 = 10, W0 = w - 20, Y0 = 80, H0 = 112, sel = 4;
  c.el("rect", { x: X0 + (W0 * sel) / 16, y: Y0, width: W0 / 16, height: H0, fill: T.acc, opacity: 0.14 });
  const env = loopEnv(Math.round(W0 / 1.6));
  wave(c, X0, Y0, W0, H0, env, (t) => (Math.floor(t * 16) === sel ? "#ffffff" : T.acc));
  for (let k = 0; k <= 16; k++) {
    const x = X0 + (W0 * k) / 16;
    c.el("rect", { x: x - 0.5, y: Y0, width: 1, height: H0, fill: T.mute, opacity: k % 4 ? 0.22 : 0.45 });
  }
  for (const k of [sel, sel + 1]) {                 // les poignées du début et de la fin
    const x = X0 + (W0 * k) / 16;
    c.el("path", { d: `M${x - 5} ${Y0 - 1}h10l-5 7z`, fill: "#ffffff" });
    c.el("rect", { x: x - 0.75, y: Y0, width: 1.5, height: H0, fill: "#ffffff", opacity: 0.9 });
  }
  if (P) { const ph = c.sub("g", { class: P + "head" }); ph.el("rect", { x: X0 - 0.75, y: Y0 - 2, width: 1.6, height: H0 + 4, fill: "#ffffff" }); ph.el("rect", { x: X0 - 4, y: Y0 - 2, width: 8, height: H0 + 4, fill: "#ffffff", opacity: 0.12 }); }
  // la vue d'ensemble : ce que montre le zoom
  c.el("rect", { x: X0, y: 200, width: W0, height: 3, rx: 1.5, fill: T.mute, opacity: 0.3 });
  c.el("rect", { x: X0, y: 200, width: W0, height: 3, rx: 1.5, fill: T.acc, opacity: 0.9 });
  c.text("S01 BREAK", 10, 226, 600, 18, T.fg);
  c.text("MIC  ·  4.0s", 104, 226, 500, 13, T.mute);
  battery(c, w);
}

function lcdCapture(s, w, P) {                        // CAPTURE : la source, le niveau, l'enregistrement en cours
  const c = mk(s);
  c.el("rect", { x: 0, y: 0, width: w, height: 240, fill: T.bg });
  header(c, w, [["SOURCE", "MIC", null], ["INPUT", "+6", 0.62], ["THRESH", "-30", 0.3], ["LENGTH", "2 BARS", null]]);
  const chips = [["MIC", true], ["FM-1", false], ["FILE", false]];
  let x = 10;
  for (const [lab, on] of chips) {
    const cw = lab.length * 8 + 18;
    c.el("rect", { x, y: 60, width: cw, height: 16, rx: 8, fill: on ? T.acc : "none", stroke: on ? "none" : T.mute, "stroke-opacity": 0.6, "stroke-width": 1 });
    c.text(lab, x + cw / 2, 72, 600, 11, on ? T.bg : T.mute, "middle", { "letter-spacing": 0.6 });
    x += cw + 6;
  }
  c.el("circle", { cx: w - 82, cy: 68, r: 4.5, fill: "#ff5246", class: P ? P + "rec" : "" });
  c.text("REC  0:03.4", w - 10, 72, 600, 13, "#ffffff", "end");
  const X0 = 10, W0 = w - 52, Y0 = 84, H0 = 108, done = 0.82;
  const env = loopEnv(Math.round(W0 / 1.6), 11).map((v, i, a) => (i / a.length < done ? v : 0));
  wave(c, X0, Y0, W0, H0, env, (t) => (t < done ? T.acc : T.mute));
  c.el("rect", { x: X0 + W0 * done, y: Y0 - 2, width: 1.6, height: H0 + 4, fill: "#ff5246" });
  c.el("rect", { x: X0, y: Y0 + H0 / 2, width: W0, height: 1, fill: T.mute, opacity: 0.25 });
  for (let k = 0; k <= 2; k++) c.el("rect", { x: X0 + (W0 * k) / 2 - 0.5, y: Y0, width: 1, height: H0, fill: T.mute, opacity: 0.3 });
  // le niveau d'entrée, en segments
  const MX = w - 30;
  for (let i = 0; i < 18; i++) {
    const y = Y0 + H0 - (i + 1) * 6, on = i < 13;
    c.el("rect", { x: MX, y, width: 18, height: 4, rx: 1, fill: i >= 15 ? "#ff5246" : i >= 12 ? "#ffd77a" : T.acc, opacity: on ? 1 : 0.16 });
  }
  c.el("rect", { x: MX - 3, y: Y0 + H0 - 30 * 6 / 5 - 2, width: 24, height: 1.4, fill: "#ffffff", opacity: 0.8 });   // le seuil
  c.text("→ S02  new sample", 10, 226, 600, 18, T.fg);
  battery(c, w);
}

function lcdSend(s, w) {                              // ENVOI : la banque qui part dans Pigeon
  const c = mk(s);
  c.el("rect", { x: 0, y: 0, width: w, height: 240, fill: T.bg });
  header(c, w, [["TO", "PIGEON", null], ["SONG", "S01", null], ["PADS", "1–16", null], ["SIZE", "412K", 0.82]]);
  c.text("Replaces Pigeon's whole bank", 10, 70, 500, 13, T.mute);
  c.text("FM1-A", w - 10, 70, 600, 13, T.acc, "end");
  // la chanson : le sample long
  const Y0 = 82;
  c.el("rect", { x: 10, y: Y0, width: 120, height: 112, rx: 6, fill: "none", stroke: T.acc, "stroke-opacity": 0.5 });
  c.text("SONG 1", 18, Y0 + 16, 600, 11, T.mute);
  wave(c, 16, Y0 + 24, 108, 56, loopEnv(64), () => T.acc);
  c.text("S01 BREAK", 18, Y0 + 100, 600, 13, T.fg);
  // les 16 pads : les tranches
  const GX = 142, GW = w - GX - 10, cw = (GW - 3 * 5) / 4, ch = (112 - 3 * 5) / 4;
  for (let k = 0; k < 16; k++) {
    const x = GX + (k % 4) * (cw + 5), y = Y0 + (k >> 2) * (ch + 5);
    c.el("rect", { x, y, width: cw, height: ch, rx: 4, fill: T.acc, opacity: k === 4 ? 0.3 : 0.12 });
    const env = loopEnv(22, 20 + k);
    wave(c, x + 22, y + 3, cw - 26, ch - 6, env, () => (k === 4 ? "#ffffff" : T.acc));
    c.text(String(k + 1).padStart(2, "0"), x + 5, y + ch / 2 + 4, 600, 11, k === 4 ? "#ffffff" : T.mute);
  }
  c.text("SEND", 10, 226, 600, 18, "#ffffff");
  c.text("to push the bank to FM1-A", 52, 226, 500, 13, T.mute);
  battery(c, w);
}

// ------------------------------------------------------------------ les fichiers
const write = (name, s) => fs.writeFileSync(`${OUT}/${name}`, s);
write("module.svg", panel({ P: "m_", kind: "module", lcd: "edit", anim: true }).svg);
write("module2.svg", panel({ P: "m_", kind: "module2", anim: true }).svg);
write("fm1.svg", panel({ P: "f_", kind: "fm1", anim: true }).svg);
for (const [k, fn] of [["capture", lcdCapture], ["edit", lcdEdit], ["send", lcdSend]]) {
  const root = new N("svg", { xmlns: "http://www.w3.org/2000/svg", viewBox: "0 0 440 240", width: "100%", height: "100%" });
  fn(root, 440, "e_");
  write(`lcd-${k}.svg`, ser(root));
}
console.log("ok");
