// SPDX-License-Identifier: GPL-3.0-only
// VECTOR37 (genkigenki/Vector37, GPL-3.0) dans un AudioWorklet : sa version FM-1 sur le FM-1 simulé de ses tests,
// compilée par tools/worklets/vector37.sh. sim_render est l'horloge de l'appareil (le son, et sa boucle principale
// toutes les 15 ms). Il parle au panneau dans le protocole Felucca : load {wasm, master}, buttons et keys en masques
// (l'ordre du panneau), enc {role, n}, master 0..1023, midi {data} ; frame {fb (ordre de la dalle), leds, load}.
// Rien n'est gardé : pas de sectors.
const FRAMES = 44100 * 15 / 1000;                // une boucle de l'appareil

class Vector37 extends AudioWorkletProcessor {
  constructor() {
    super();
    this.ex = null; this.prevFb = null; this.lastFrame = 0; this.busy = 0; this.frames = 0;
    this.buttons = 0; this.keys = 0; this.queue = []; this.toLoop = 0;
    this.port.onmessage = (e) => this.onMessage(e.data);
  }
  async onMessage(m) {
    if (m.type === "load") {
      try {
        const mod = await WebAssembly.compile(m.wasm), imports = {};
        for (const imp of WebAssembly.Module.imports(mod))      // (aucun attendu ; des bouchons si la chaîne en ajoute)
          if (imp.kind === "function") (imports[imp.module] ??= {})[imp.name] = () => 0;
        const ex = (await WebAssembly.instantiate(mod, imports)).exports;
        ex._initialize?.();
        ex.sim_master(m.master ?? 800);              // (avant l'allumage : le niveau lu au démarrage, sans saut)
        ex.sim_init();
        this.ex = ex;
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
  // un changement des boutons ou des touches par boucle de l'appareil : il lit ses touches une fois par boucle, un
  // toucher bref garde sa pression jusqu'à la boucle suivante, puis son relâchement
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
    msg.leds = Array.from(new Uint32Array(ex.memory.buffer, ex.sim_leds(), 8));
    if (this.frames >= sampleRate) { msg.load = this.busy / ((this.frames / sampleRate) * 1000); this.busy = this.frames = 0; }
    this.port.postMessage(msg, tr);
  }
  process(inputs, outputs) {
    const ex = this.ex;
    if (!ex) return true;
    const out = outputs[0], n = out[0].length, t0 = Date.now();
    this.toLoop -= n;
    if (this.toLoop <= 0) { this.toLoop += FRAMES; this.input(); }
    ex.sim_render(n);
    out[0].set(new Float32Array(ex.memory.buffer, ex.sim_out_l(), n));
    if (out[1]) out[1].set(new Float32Array(ex.memory.buffer, ex.sim_out_r(), n));
    this.busy += Date.now() - t0; this.frames += n;
    if (currentTime - this.lastFrame >= 1 / 30) { this.lastFrame = currentTime; this.publish(); }
    return true;
  }
}
registerProcessor("vector37", Vector37);
