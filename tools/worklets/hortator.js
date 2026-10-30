// SPDX-License-Identifier: GPL-3.0-only
// Hortator (deadactive/hortator, GPL-3.0) dans un AudioWorklet, d'après sa page (web/sim/engine.js, worklet.js) :
// son simulateur, compilé par tools/worklets/hortator.sh. sim_render est l'horloge de l'appareil (l'audio par
// demi-tampon, l'interface toutes les 15 ms). Il parle au panneau dans le protocole Felucca : load {wasm, sectors,
// master}, buttons et keys en masques, enc {role, n}, master 0..1023, midi {data} ; frame {fb (ordre de la dalle),
// leds, sectors, load}. Ses boutons et ses molettes sont déjà dans l'ordre du panneau (panel.c B_FX.., EN_SELECT..).
const FLASH = 0x100000, SECTOR = 4096, PLAY = 10, HOLD_MS = 24;

class Hortator extends AudioWorkletProcessor {
  constructor() {
    super();
    this.ex = null; this.prevFb = null; this.lastFrame = 0; this.busy = 0; this.frames = 0;
    this.sectors = {}; this.buttons = 0; this.keys = 0; this.queue = []; this.ms = 0; this.nextOk = 0;
    this.port.onmessage = (e) => this.onMessage(e.data);
  }
  async onMessage(m) {
    if (m.type === "load") {
      try {
        const mod = await WebAssembly.compile(m.wasm), imports = {};
        for (const imp of WebAssembly.Module.imports(mod))      // aucune aujourd'hui (comme sa page : un bouchon)
          if (imp.kind === "function") (imports[imp.module] ??= {})[imp.name] = () => 0;
        const ex = (await WebAssembly.instantiate(mod, imports)).exports;
        ex._initialize?.();
        for (const [k, v] of Object.entries(m.sectors || {})) {  // les projets, les kits et les réglages gardés par la page
          const off = +k, b = v instanceof Uint8Array ? v : new Uint8Array(v);
          if (off % SECTOR === 0 && off >= 0 && off + SECTOR <= FLASH && b.length === SECTOR) this.sectors[off] = b;
        }
        ex.sim_master(m.master ?? 800);
        if (Object.keys(this.sectors).length) {
          ex.sim_flash_reset();
          for (const [off, b] of Object.entries(this.sectors)) new Uint8Array(ex.memory.buffer, ex.sim_flash(), FLASH).set(b, +off);
          ex.sim_init(0);
        } else ex.sim_init(1);                                   // une première fois : les démos
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
  // un changement des boutons ou des touches tient HOLD_MS du temps de l'appareil avant le suivant : l'interface les
  // lit une fois par image, un toucher bref garde sa pression puis son relâchement
  input() {
    const ex = this.ex;
    while (this.queue.length && this.ms >= this.nextOk) {
      const m = this.queue.shift(), mask = m.mask >>> 0;
      if (m.type === "buttons") {
        const d = (mask ^ this.buttons) >>> 0;
        for (let b = 0; b < 14; b++) if ((d >> b) & 1) ex.sim_btn(b, (mask >> b) & 1);
        this.buttons = mask;
      } else {
        const d = (mask ^ this.keys) >>> 0;
        for (let k = 0; k < 27; k++) if ((d >> k) & 1) ex.sim_key(k, (mask >> k) & 1);
        this.keys = mask;
      }
      this.nextOk = this.ms + HOLD_MS;
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
    const lb = ex.sim_leds() >>> 0;                            // PLAY allumé : son vert
    msg.leds = [((lb & ~(1 << PLAY)) | ((lb >> PLAY) & 1) << 14) >>> 0, ex.sim_key_leds() >>> 0];
    const bits = new Uint32Array(ex.memory.buffer, ex.sim_flash_dirty(), FLASH / SECTOR / 32);
    if (bits.some((x) => x)) {                                 // un projet ou un réglage écrit : la mémoire gardée, entière
      const flash = new Uint8Array(ex.memory.buffer, ex.sim_flash(), FLASH);
      for (let s = 0; s < FLASH / SECTOR; s++) if ((bits[s >> 5] >>> (s & 31)) & 1) this.sectors[s * SECTOR] = flash.slice(s * SECTOR, (s + 1) * SECTOR);
      ex.sim_flash_clean();
      msg.sectors = {};
      for (const [off, b] of Object.entries(this.sectors)) if (b.some((v) => v !== 0xFF)) msg.sectors[off] = b.slice();
    }
    if (this.frames >= sampleRate) { msg.load = this.busy / ((this.frames / sampleRate) * 1000); this.busy = this.frames = 0; }
    this.port.postMessage(msg, tr);
  }
  process(inputs, outputs) {
    const ex = this.ex;
    if (!ex) return true;
    const out = outputs[0], n = out[0].length, t0 = Date.now();
    this.input();
    ex.sim_render(n);
    const a = new Float32Array(ex.memory.buffer, ex.sim_audio(), 2 * n);
    for (let i = 0; i < n; i++) { out[0][i] = a[2 * i]; if (out[1]) out[1][i] = a[2 * i + 1]; }
    this.ms += (n / sampleRate) * 1000;
    this.busy += Date.now() - t0; this.frames += n;
    if (currentTime - this.lastFrame >= 1 / 30) { this.lastFrame = currentTime; this.publish(); }
    return true;
  }
}
registerProcessor("hortator", Hortator);
