// SPDX-License-Identifier: GPL-3.0-only
// zp12 (zvenson/zp12, GPL-3.0) dans un AudioWorklet, d'après son sim/worklet.js : zp12.wasm est son firmware sur un
// FM-1 simulé (sim/sim.c). Il parle au panneau dans le protocole Felucca (load {wasm, sectors, master}, buttons et
// keys en masques, enc {role, n}, master 0..1023, midi {data} ; frame {fb dans l'ordre de la dalle, leds, sectors,
// load}), pour garder ce que le sien laisse de côté : ses échantillons, hors de sa réserve (sim_store). La flash
// gardée : les pièces de sa sauvegarde (web/zp12link.js PARTS.zp12), secteur par secteur. Et {type: "zp12"} : ce que
// son lien USB fait pour l'éditeur web (lire, effacer, écrire la flash ; RELOAD, ASSIGN), pour web/zp12link.js.
const STORE_LO = 0xC4000, SECT = 4096, HOLD_MS = 24;
const PARTS = [[0xC4000, 0xDC000], [0xE5000, 0xE9000], [0xEA000, 0xFC000]];
const BTN = (b) => (b < 12 ? b + 2 : b - 12);                 // bouton du panneau (FX..REC, OCT- OCT+) → ordre Dinghy
const ENC = [0, 1, 6, 2, 3, 4, 5];                            // rôle du panneau (SELECT ALGORITHM PRESETS K1..K4) → zp12
const inParts = (a, n) => PARTS.some(([lo, hi]) => a >= lo && a + n <= hi);

class Zp12 extends AudioWorkletProcessor {
  constructor() {
    super();
    this.ex = null; this.prevFb = null; this.lastFrame = 0; this.busy = 0; this.frames = 0;
    this.buttons = 0; this.keys = 0; this.queue = []; this.ms = 0; this.nextOk = 0; this.writes = 0; this.dirty = false;
    this.port.onmessage = (e) => this.onMessage(e.data);
  }
  flash() { return new Uint8Array(this.ex.memory.buffer, this.ex.sim_store() - STORE_LO, 0x100000); }   // (la vue change avec la mémoire)
  async onMessage(m) {
    if (m.type === "load") {
      try {
        const ex = (this.ex = (await WebAssembly.instantiate(m.wasm, {})).instance.exports), f = this.flash();
        const s = m.sectors;
        if (s instanceof ArrayBuffer) { if (s.byteLength === ex.sim_store_size()) f.set(new Uint8Array(s), STORE_LO); }   // (une sauvegarde d'avant : sa réserve seule)
        else for (const [k, v] of Object.entries(s || {})) {
          const off = +k, b = v instanceof Uint8Array ? v : new Uint8Array(v);
          if (off % SECT === 0 && b.length === SECT && inParts(off, SECT)) f.set(b, off);
        }
        ex.sim_master(m.master ?? 700);
        if (ex.sim_init(44100) !== 0) throw new Error("sim_init failed");
        this.writes = ex.sim_store_writes();
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
    else if (m.type === "enc") { if (ENC[m.role] !== undefined) ex.sim_enc(ENC[m.role], m.n | 0); }
    else if (m.type === "master") ex.sim_master(m.value | 0);
    else if (m.type === "midi") ex.sim_midi(m.data[0] | 0, m.data[1] | 0, m.data[2] | 0);
    else if (m.type === "zp12") this.link(m);
  }
  // le lien de l'éditeur web, dans la flash simulée (la flash du FM-1 : un bit effacé à 1, programmé vers 0)
  link(m) {
    const ex = this.ex, f = this.flash();
    let value = 0, error = null;
    if (m.op === "kit") value = ex.sim_zl_kit();
    else if (m.op === "read") value = Array.from(f.subarray(m.a, m.a + m.n));
    else if (m.op === "erase") { if (m.a % SECT || !inParts(m.a, SECT)) error = "erase"; else { f.fill(0xff, m.a, m.a + SECT); this.dirty = true; } }
    else if (m.op === "write") {
      if (!inParts(m.a, m.data.length)) error = "write";
      else { for (let i = 0; i < m.data.length; i++) f[m.a + i] &= m.data[i]; this.dirty = true; }
    } else if (m.op === "reload") value = ex.sim_zl_reload();
    else if (m.op === "assign") value = ex.sim_zl_assign(m.a >>> 0);
    this.port.postMessage({ type: "zp12-done", id: m.id, value, error });
  }
  // un changement des boutons ou des touches tient HOLD_MS du temps de l'appareil avant le suivant
  input() {
    const ex = this.ex;
    while (this.queue.length && this.ms >= this.nextOk) {
      const m = this.queue.shift(), mask = m.mask >>> 0;
      if (m.type === "buttons") {
        const d = (mask ^ this.buttons) >>> 0;
        for (let b = 0; b < 14; b++) if ((d >> b) & 1) ex.sim_button(BTN(b), (mask >> b) & 1);
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
    const fb = new Uint16Array(ex.memory.buffer, ex.sim_screen(), 240 * 240);
    let changed = !this.prevFb;
    if (!changed) for (let i = 0; i < fb.length; i++) if (fb[i] !== this.prevFb[i]) { changed = true; break; }
    if (changed) {
      this.prevFb = fb.slice();
      const out = fb.slice();                                // l'ordre d'octets de la dalle, comme Felucca le donne
      for (let i = 0; i < out.length; i++) { const v = out[i]; out[i] = ((v >> 8) | (v << 8)) & 0xFFFF; }
      msg.fb = out; tr.push(out.buffer);
    }
    const lb = ex.sim_leds_buttons() >>> 0;
    let b = 0;
    for (let i = 0; i < 14; i++) if ((lb >> BTN(i)) & 1) b |= i === 10 ? 1 << 14 : 1 << i;   // PLAY allumé : son vert
    msg.leds = [b >>> 0, ex.sim_leds_keys() >>> 0, 0, ex.sim_glow_keys() >>> 0];
    const w = ex.sim_store_writes();
    if (w !== this.writes || this.dirty) {                  // ses réglages ou ses échantillons écrits : la flash gardée
      this.writes = w; this.dirty = false;
      const f = this.flash(), sectors = {};
      for (const [lo, hi] of PARTS) for (let a = lo; a < hi; a += SECT) { const s = f.subarray(a, a + SECT); if (s.some((v) => v !== 0xff)) sectors[a] = s.slice(); }
      msg.sectors = sectors;
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
    out[0].set(new Float32Array(ex.memory.buffer, ex.sim_out_l(), n));
    if (out[1]) out[1].set(new Float32Array(ex.memory.buffer, ex.sim_out_r(), n));
    this.ms += (n / sampleRate) * 1000;
    this.busy += Date.now() - t0; this.frames += n;
    if (currentTime - this.lastFrame >= 1 / 30) { this.lastFrame = currentTime; this.publish(); }
    return true;
  }
}
registerProcessor("zp12", Zp12);
