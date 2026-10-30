// SPDX-License-Identifier: GPL-3.0-only
// Ravel (De-Pattern/Ravel_FM1, GPL-3.0) dans un AudioWorklet. Sa page fait tourner ravel.wasm sur le fil principal
// (web/emu/index.html : rv_run(ms) avance l'appareil de ms millisecondes et rend l'audio qui va avec, dans une file
// que lit un ScriptProcessor) ; ici, la même file, remplie à chaque quantum. Il parle au panneau dans le protocole
// Felucca : load {wasm, sectors, master}, buttons et keys en masques, enc {role, n}, master 0..1023 ;
// frame {fb (ordre de la dalle), leds, sectors, load}.
const BTN = [12, 13, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11];   // bouton n de Ravel (ordre Dinghy) → bit du panneau
const ENC = [0, 1, 6, 2, 3, 4, 5];                            // rôle du panneau (SELECT ALGORITHM PRESETS K1..K4) → Ravel
const PLAY = 12, FIFO = 1 << 14, MASK = FIFO - 1;

class Ravel extends AudioWorkletProcessor {
  constructor() {
    super();
    this.ex = null; this.lastFrame = 0; this.prevFb = null; this.writes = 0; this.busy = 0; this.frames = 0;
    this.fl = new Float32Array(FIFO); this.fr = new Float32Array(FIFO); this.w = 0; this.r = 0;
    this.port.onmessage = (e) => this.onMessage(e.data);
  }
  async onMessage(m) {
    if (m.type === "load") {
      try {
        const { instance } = await WebAssembly.instantiate(m.wasm, {});
        const ex = (this.ex = instance.exports);
        const slots = (m.sectors && m.sectors.slots) || [];   // les projets et les banques de sons, gardés par la page
        for (let o = 0; o < Math.min(slots.length, ex.rv_store_slots()); o++) {
          const s = slots[o];
          if (!s) continue;
          const n = Math.min(s.length, ex.rv_store_max());
          new Uint8Array(ex.memory.buffer, ex.rv_store(o), n).set(s.subarray(0, n));
          ex.rv_store_set_len(o, n);
        }
        ex.rv_boot();
        ex.rv_set_master(Math.round(((m.master ?? 900) / 1023) * 4096));
        this.writes = ex.rv_store_writes();
        this.port.postMessage({ type: "ready" });
      } catch (err) {
        this.ex = null;
        this.port.postMessage({ type: "error", message: String((err && err.message) || err) });
      }
      return;
    }
    const ex = this.ex;
    if (!ex) return;
    if (m.type === "buttons") {
      let r = 0;
      for (let i = 0; i < 14; i++) if ((m.mask >> BTN[i]) & 1) r |= 1 << i;
      ex.rv_set_buttons(r >>> 0);
    } else if (m.type === "keys") ex.rv_set_keys(m.mask >>> 0);
    else if (m.type === "enc") { if (ENC[m.role] !== undefined) ex.rv_enc(ENC[m.role], m.n | 0); }
    else if (m.type === "master") ex.rv_set_master(Math.round((m.value / 1023) * 4096));
  }
  run(ms) {
    const ex = this.ex, n = ex.rv_run(ms), a = new Float32Array(ex.memory.buffer, ex.rv_audio(), 2 * n);
    for (let i = 0; i < n; i++, this.w++) { this.fl[this.w & MASK] = a[2 * i]; this.fr[this.w & MASK] = a[2 * i + 1]; }
    const wr = ex.rv_store_writes();
    if (wr !== this.writes) { this.writes = wr; this.keep(); }
    return n;
  }
  keep() {                                                 // un projet ou un son gardé : toute la mémoire, à la page
    const ex = this.ex, slots = [];
    for (let o = 0; o < ex.rv_store_slots(); o++) {
      const n = ex.rv_store_len(o);
      slots.push(n >= 0 ? new Uint8Array(ex.memory.buffer, ex.rv_store(o), n).slice() : null);
    }
    this.port.postMessage({ type: "frame", sectors: { slots } });
  }
  publish() {
    const ex = this.ex, msg = { type: "frame" }, tr = [];
    const fb = new Uint16Array(ex.memory.buffer, ex.rv_fb(), 240 * 240);
    let changed = !this.prevFb;
    if (!changed) for (let i = 0; i < fb.length; i++) if (fb[i] !== this.prevFb[i]) { changed = true; break; }
    if (changed) {
      this.prevFb = fb.slice();
      const f = fb.slice();
      for (let i = 0; i < f.length; i++) { const v = f[i]; f[i] = ((v >> 8) | (v << 8)) & 0xFFFF; }
      msg.fb = f; tr.push(f.buffer);
    }
    const lb = ex.rv_leds_buttons();
    let b = 0;
    for (let i = 0; i < 14; i++) if ((lb >> i) & 1) b |= i === PLAY ? 1 << 14 : 1 << BTN[i];
    msg.leds = [b, ex.rv_leds_keys() >>> 0];
    if (this.frames >= sampleRate) { msg.load = this.busy / ((this.frames / sampleRate) * 1000); this.busy = this.frames = 0; }
    this.port.postMessage(msg, tr);
  }
  process(inputs, outputs) {
    const ex = this.ex;
    if (!ex) return true;
    const out = outputs[0], n = out[0].length, t0 = Date.now();
    while (this.w - this.r < n) if (!this.run(4)) break;    // (rien rendu : silence plutôt qu'une boucle sans fin)
    for (let i = 0; i < n; i++) {
      const ok = this.r < this.w, l = ok ? this.fl[this.r & MASK] : 0, r = ok ? this.fr[this.r & MASK] : 0;
      if (ok) this.r++;
      out[0][i] = l; if (out[1]) out[1][i] = r;
    }
    this.busy += Date.now() - t0; this.frames += n;
    if (currentTime - this.lastFrame >= 1 / 30) { this.lastFrame = currentTime; this.publish(); }
    return true;
  }
}
registerProcessor("ravel", Ravel);
