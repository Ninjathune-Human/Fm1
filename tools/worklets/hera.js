// HERA (benbadio/hera-fm1, GPL-3.0) dans un AudioWorklet. Sa page fait tourner hera.wasm sur le fil principal
// (web/hera.js : web_step sur un minuteur, web_audio dans un ScriptProcessor) ; ici, chaque quantum avance l'horloge
// du firmware puis rend son audio. Il parle au panneau dans le protocole Felucca : load {wasm, sectors, master},
// buttons et keys en masques, enc {role, n}, master 0..1023 ; frame {fb (ordre de la dalle), leds, sectors, load}.
const BTN = [12, 13, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11];   // bouton n de HERA (ordre Dinghy) → bit du panneau
const ENC = [0, 1, 6, 2, 3, 4, 5];                            // rôle du panneau (SELECT ALGORITHM PRESETS K1..K4) → HERA
const PLAY = 12;

class Hera extends AudioWorkletProcessor {
  constructor() {
    super();
    this.ex = null; this.buttons = 0; this.gain = 0.88; this.lastFrame = 0; this.lastKeep = 0;
    this.prevFb = null; this.kept = null; this.busy = 0; this.frames = 0;
    this.port.onmessage = (e) => this.onMessage(e.data);
  }
  store() { const ex = this.ex; return new Uint8Array(ex.memory.buffer, ex.web_store(), ex.web_store_len()); }
  async onMessage(m) {
    if (m.type === "load") {
      try {
        const { instance } = await WebAssembly.instantiate(m.wasm, {});
        const ex = (this.ex = instance.exports);
        ex.web_init();
        const s = m.sectors && m.sectors.store;            // les 64 patterns et les réglages, gardés par la page
        if (s && s.length === ex.web_store_len()) { this.store().set(s); ex.web_reload(); }
        this.kept = this.store().slice();
        if (m.master != null) this.gain = m.master / 1023;
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
      for (let i = 0; i < 14; i++) {
        const was = (this.buttons >> BTN[i]) & 1, now = (m.mask >> BTN[i]) & 1;
        if (was !== now) ex.web_button(i, now);
      }
      this.buttons = m.mask;
    } else if (m.type === "keys") ex.web_keys(m.mask >>> 0);
    else if (m.type === "enc") { if (ENC[m.role] !== undefined) ex.web_enc(ENC[m.role], m.n | 0); }
    else if (m.type === "master") this.gain = m.value / 1023;   // sa page règle le volume après le firmware
  }
  publish() {
    const ex = this.ex, msg = { type: "frame" }, tr = [];
    const fb = new Uint16Array(ex.memory.buffer, ex.web_fb(), 240 * 240);
    let changed = !this.prevFb;
    if (!changed) for (let i = 0; i < fb.length; i++) if (fb[i] !== this.prevFb[i]) { changed = true; break; }
    if (changed) {
      this.prevFb = fb.slice();
      const f = fb.slice();
      for (let i = 0; i < f.length; i++) { const v = f[i]; f[i] = ((v >> 8) | (v << 8)) & 0xFFFF; }
      msg.fb = f; tr.push(f.buffer);
    }
    const l = new Uint8Array(ex.memory.buffer, ex.web_leds(), 41);
    let b = 0, k = 0;
    for (let i = 0; i < 14; i++) if (l[i]) b |= i === PLAY ? 1 << 14 : 1 << BTN[i];
    for (let i = 0; i < 27; i++) if (l[14 + i]) k |= 1 << i;
    msg.leds = [b, k >>> 0];
    if (this.frames >= sampleRate) { msg.load = this.busy / ((this.frames / sampleRate) * 1000); this.busy = this.frames = 0; }
    this.port.postMessage(msg, tr);
  }
  keep() {                                                 // un SAVE a changé la mémoire : à la page, qui la garde
    const now = this.store(), was = this.kept;
    for (let i = 0; i < now.length; i++)
      if (now[i] !== was[i]) {
        this.kept = now.slice();
        this.port.postMessage({ type: "frame", sectors: { store: this.kept.slice() } });
        return;
      }
  }
  process(inputs, outputs) {
    const ex = this.ex;
    if (!ex) return true;
    const out = outputs[0], n = out[0].length, t0 = Date.now();
    ex.web_step(Math.floor(currentTime * 1000) + 1);
    ex.web_audio(n);
    const a = new Int32Array(ex.memory.buffer, ex.web_audio_buf(), 2 * n), g = this.gain / 32768;
    for (let i = 0; i < n; i++) { out[0][i] = a[2 * i] * g; if (out[1]) out[1][i] = a[2 * i + 1] * g; }
    this.busy += Date.now() - t0; this.frames += n;
    if (currentTime - this.lastFrame >= 1 / 30) { this.lastFrame = currentTime; this.publish(); }
    if (currentTime - this.lastKeep >= 1) { this.lastKeep = currentTime; this.keep(); }
    return true;
  }
}
registerProcessor("hera", Hera);
