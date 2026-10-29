// La base des worklets pour les firmwares écrits pour une page Emscripten (frodhes, chipbox) : leur boucle principale
// rend la main par emscripten_sleep. Compilés par tools/worklets/asyncify.sh, ces appels deviennent une coroutine
// Asyncify : à chaque quantum, la boucle reprend jusqu'à son prochain emscripten_sleep, puis l'audio est tiré par
// blocs. Le panneau leur parle en protocole Felucca : load {wasm, sectors, master}, buttons et keys en masques,
// enc {role, n}, master 0..1023 ; frame {fb (ordre de la dalle), leds, sectors, load}.
// Un profil (frodhes.js, chipbox.js) fournit : restore, keep, block, button, keys, enc, master, et LIT.
const BTN = [12, 13, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11];   // bouton n (ordre Dinghy) → bit du panneau
const ENC = [0, 1, 6, 2, 3, 4, 5];                            // rôle du panneau (SELECT ALGORITHM PRESETS K1..K4) → Dinghy
const PLAY = 12, FIFO = 1 << 14, MASK = FIFO - 1, PILE = 1 << 17;
const RUN = 0, UNWOUND = 1, REWINDING = 2, ENDED = 3;

export class Coroutine extends AudioWorkletProcessor {
  constructor() {
    super();
    this.ex = null; this.state = ENDED; this.wake = 0; this.buttons = 0;
    this.fl = new Float32Array(FIFO); this.fr = new Float32Array(FIFO); this.w = 0; this.r = 0;
    this.lastFrame = 0; this.lastKeep = 0; this.prevFb = null; this.busy = 0; this.frames = 0;
    this.port.onmessage = (e) => this.onMessage(e.data);
  }
  now() { return currentTime * 1000; }
  imports() {
    const dv = () => new DataView(this.ex.memory.buffer);
    const wasi = {
      fd_write: (fd, iov, n, out) => { let len = 0; for (let i = 0; i < n; i++) len += dv().getUint32(iov + 8 * i + 4, true); dv().setUint32(out, len, true); return 0; },
      environ_sizes_get: (a, b) => { dv().setUint32(a, 0, true); dv().setUint32(b, 0, true); return 0; },
      proc_exit: () => { this.state = ENDED; throw new Error("fin du firmware"); },
    };
    return {
      env: { emscripten_get_now: () => this.now(), emscripten_sleep: (ms) => this.sleep(ms) },
      wasi_snapshot_preview1: new Proxy(wasi, { get: (t, k) => (k in t ? t[k] : () => 0) }),
    };
  }
  sleep(ms) {                                           // la boucle rend la main : on déroule sa pile
    const ex = this.ex;
    if (this.state === REWINDING) { ex.asyncify_stop_rewind(); this.state = RUN; return; }
    this.wake = this.now() + ms;
    new Int32Array(ex.memory.buffer, this.data, 1)[0] = this.data + 8;
    ex.asyncify_start_unwind(this.data);
    this.state = UNWOUND;
  }
  run() {                                               // la boucle, jusqu'à son prochain emscripten_sleep
    const ex = this.ex;
    try { ex.__main_void(); } catch (err) { this.state = ENDED; return; }
    if (this.state === UNWOUND) ex.asyncify_stop_unwind(); else this.state = ENDED;
  }
  resume() {
    if (this.state !== UNWOUND || this.now() < this.wake) return;
    this.ex.asyncify_start_rewind(this.data);
    this.state = REWINDING;
    this.run();
  }
  async onMessage(m) {
    if (m.type === "load") {
      try {
        const { instance } = await WebAssembly.instantiate(m.wasm, this.imports());
        const ex = (this.ex = instance.exports);
        if (ex._initialize) ex._initialize();
        this.data = ex.malloc(8 + PILE);                 // la pile d'Asyncify : [début, fin], puis ses octets
        new Int32Array(ex.memory.buffer, this.data, 2).set([this.data + 8, this.data + 8 + PILE]);
        this.master(ex, m.master ?? 900);
        this.restore(ex, m.sectors || {});
        this.state = RUN;
        this.run();
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
        if (was !== now) this.button(ex, i, now);
      }
      this.buttons = m.mask;
    } else if (m.type === "keys") this.keys(ex, m.mask >>> 0);
    else if (m.type === "enc") { if (ENC[m.role] !== undefined) this.enc(ex, ENC[m.role], m.n | 0); }
    else if (m.type === "master") this.master(ex, m.value);
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
    for (let i = 0; i < 14; i++) if (l[i] === this.LIT) b |= i === PLAY ? 1 << 14 : 1 << BTN[i];
    for (let i = 0; i < 27; i++) if (l[14 + i] === this.LIT) k |= 1 << i;
    msg.leds = [b, k >>> 0];
    if (this.frames >= sampleRate) { msg.load = this.busy / ((this.frames / sampleRate) * 1000); this.busy = this.frames = 0; }
    this.port.postMessage(msg, tr);
  }
  process(inputs, outputs) {
    const ex = this.ex;
    if (!ex) return true;
    const out = outputs[0], n = out[0].length, t0 = Date.now();
    this.resume();
    while (this.w - this.r < n) {                      // des blocs de 256 trames, entrelacés
      const a = this.block(ex);
      for (let i = 0; i < a.length; i += 2, this.w++) { this.fl[this.w & MASK] = a[i]; this.fr[this.w & MASK] = a[i + 1]; }
    }
    for (let i = 0; i < n; i++, this.r++) { out[0][i] = this.fl[this.r & MASK]; if (out[1]) out[1][i] = this.fr[this.r & MASK]; }
    this.busy += Date.now() - t0; this.frames += n;
    if (currentTime - this.lastFrame >= 1 / 60) { this.lastFrame = currentTime; this.publish(); }
    if (currentTime - this.lastKeep >= 1) {
      this.lastKeep = currentTime;
      const s = this.keep(ex);
      if (s) this.port.postMessage({ type: "frame", sectors: s });
    }
    return true;
  }
}
