// SPDX-License-Identifier: GPL-3.0-only
// GATOR (npi3pak/fm1-gator, GPL-3.0) dans un AudioWorklet : son simulateur d'hôte compilé par tools/worklets/gator.sh.
// Le son est l'horloge de l'appareil : un bloc à la fois, une image d'interface toutes les 15 ms. Protocole Felucca :
// load {wasm, sectors, master}, buttons et keys en masques (l'ordre du panneau), enc {role, n}, master 0..1023,
// midi {data} ; frame {fb (ordre de la dalle), leds, sectors, load}. sectors.store : ses deux emplacements de mémoire
// (fw_store), longueurs puis données, gardés par la page.
const FRAMES = 44100 * 15 / 1000;

class Gator extends AudioWorkletProcessor {
  constructor() {
    super();
    this.ex = null; this.prevFb = null; this.lastFrame = 0; this.busy = 0; this.frames = 0;
    this.buttons = 0; this.keys = 0; this.queue = []; this.toFrame = 0;
    this.buf = null; this.at = 0; this.prevStore = null;
    this.port.onmessage = (e) => this.onMessage(e.data);
  }
  store() {                                    // longueurs (Uint32 par emplacement) puis les données
    const ex = this.ex, n = ex.sim_store_size(), lens = new Uint8Array(ex.memory.buffer, ex.sim_store_len(), 8);
    const out = new Uint8Array(8 + n);
    out.set(lens, 0); out.set(new Uint8Array(ex.memory.buffer, ex.sim_store(), n), 8);
    return out;
  }
  async onMessage(m) {
    if (m.type === "load") {
      try {
        const mod = await WebAssembly.compile(m.wasm), imports = {};
        for (const imp of WebAssembly.Module.imports(mod))      // WASI (stdio du simulateur) : des bouchons
          if (imp.kind === "function") (imports[imp.module] ??= {})[imp.name] = () => 0;
        const ex = (await WebAssembly.instantiate(mod, imports)).exports;
        ex._initialize?.();
        const kept = m.sectors && m.sectors.store, n = ex.sim_store_size();
        if (kept && kept.length === 8 + n) {
          new Uint8Array(ex.memory.buffer, ex.sim_store_len(), 8).set(kept.subarray(0, 8));
          new Uint8Array(ex.memory.buffer, ex.sim_store(), n).set(kept.subarray(8));
        }
        ex.sim_master(m.master ?? 800);
        ex.sim_init();
        this.ex = ex;
        this.prevStore = this.store();
        this.port.postMessage({ type: "ready", rate: 44100 });
      } catch (err) {
        this.ex = null;
        this.port.postMessage({ type: "error", message: String((err && err.message) || err) });
      }
      return;
    }
    const ex = this.ex;
    if (!ex) return;
    if (m.type === "buttons" || m.type === "keys") this.queue.push(m);
    else if (m.type === "enc") ex.sim_enc(m.role, m.n | 0);
    else if (m.type === "master") ex.sim_master(m.value | 0);
    else if (m.type === "midi") ex.sim_midi(m.data[0] | 0, m.data[1] | 0, m.data[2] | 0);
  }
  // un changement des boutons ou des touches par image : un toucher bref garde sa pression jusqu'à l'image suivante
  input() {
    const ex = this.ex, m = this.queue.shift();
    if (!m) return;
    const mask = m.mask >>> 0;
    if (m.type === "buttons") {
      const d = (mask ^ this.buttons) >>> 0;
      for (let b = 0; b < 14; b++) if ((d >> b) & 1) ex.sim_btn(b, (mask >> b) & 1);
      this.buttons = mask;
    } else {
      const d = (mask ^ this.keys) >>> 0;
      for (let k = 0; k < 27; k++) if ((d >> k) & 1) ex.sim_key(k, (mask >> k) & 1);
      this.keys = mask;
    }
  }
  publish() {
    const ex = this.ex, msg = { type: "frame" }, tr = [];
    const fb = new Uint16Array(ex.memory.buffer, ex.sim_fb(), 240 * 240);
    let changed = !this.prevFb;
    if (!changed) for (let i = 0; i < fb.length; i++) if (fb[i] !== this.prevFb[i]) { changed = true; break; }
    if (changed) {
      this.prevFb = fb.slice();
      const f = fb.slice();                                    // l'ordre d'octets de la dalle, comme Felucca le donne
      for (let i = 0; i < f.length; i++) { const v = f[i]; f[i] = ((v >> 8) | (v << 8)) & 0xFFFF; }
      msg.fb = f; tr.push(f.buffer);
    }
    msg.leds = Array.from(new Uint32Array(ex.memory.buffer, ex.sim_leds(), 2));
    const s = this.store();
    if (s.some((v, i) => v !== this.prevStore[i])) { this.prevStore = s; msg.sectors = { store: s.slice() }; }
    if (this.frames >= sampleRate) { msg.load = this.busy / ((this.frames / sampleRate) * 1000); this.busy = this.frames = 0; }
    this.port.postMessage(msg, tr);
  }
  process(inputs, outputs) {
    const ex = this.ex;
    if (!ex) return true;
    const out = outputs[0], n = out[0].length, t0 = Date.now();
    for (let i = 0; i < n; i++) {
      if (!this.buf || this.at >= this.buf.length) {
        const bl = ex.sim_block();
        this.toFrame -= bl;
        if (this.toFrame <= 0) { this.toFrame += FRAMES; this.input(); ex.sim_frame(); }
        this.buf = new Float32Array(ex.memory.buffer, ex.sim_render(), 2 * bl).slice(); this.at = 0;
      }
      out[0][i] = this.buf[this.at]; if (out[1]) out[1][i] = this.buf[this.at + 1];
      this.at += 2;
    }
    this.busy += Date.now() - t0; this.frames += n;
    if (currentTime - this.lastFrame >= 1 / 30) { this.lastFrame = currentTime; this.publish(); }
    return true;
  }
}
registerProcessor("gator", Gator);
