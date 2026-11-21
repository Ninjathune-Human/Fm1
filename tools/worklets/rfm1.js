// SPDX-License-Identifier: GPL-3.0-only
// Un firmware au format .rfm1 (docs/RFM1-FORMAT.md de RemoteFM1 for iOS, Quixotic7 : le firmware compilé en WebAssembly,
// derrière l'interface fm1core ABI 6) dans un AudioWorklet. Il parle le protocole de ChoralRoot à la page :
// load {wasm, flash, master} ; buttons, keys, tap, enc {role, n}, master 0..1023, midi {pkts} ; réponses ready,
// error, frame {fb, leds (42 octets : touches, boutons, vert de PLAY ; 2 allumé, 3 moyen, 4 faible, 1 lueur), load},
// flash {data}, midi {pkts}.
// L'horloge de l'appareil, comme celle de fm1core.h : tick(ms) à chaque milliseconde, frame() toutes les 15 ms (idle()
// sinon), audio() par blocs de 128 trames à 44 100 Hz.

const BLOC = 128, FS = 44100;
const clock = globalThis.performance ? () => globalThis.performance.now() : () => Date.now();
// fm1panel_t : décalages donnés par rfm1_layout (1..16), descripteur fm1core_t (18..33)
const P = { keys: 1, buttons: 2, keysTap: 3, buttonsTap: 4, enc: 5, master: 6, keyVel: 7, keyLean: 8, led: 9, playGreen: 10, lcd: 11, lcdWrites: 12, btnId: 13, encId: 14, encDir: 15, ready: 16 };
const D = { flashSize: 26, panel: 30, keymap: 31 };
const NKEY = 27, NBTN = 14, NENC = 7, NCOL = 11, NLINE = 4, LCD = 240 * 240;

class Rfm1 extends AudioWorkletProcessor {
  constructor() {
    super();
    this.ex = null; this.module = null; this.halted = false;
    this.fl = new Float32Array(1 << 14); this.fr = new Float32Array(1 << 14); this.w = 0; this.r = 0;
    this.ms = 0; this.audioFrames = 0;
    this.midiIn = []; this.lastPub = 0; this.sentWrites = -1; this.dirty = 0; this.dirtyAt = -1; this.lastSync = 0;
    this.busy = 0; this.frames = 0;
    this.port.onmessage = (e) => this.onMessage(e.data);
  }

  imports() {
    const dv = () => new DataView(this.ex.memory.buffer);
    const wasi = {
      fd_write: (fd, iov, n, out) => { let len = 0; for (let i = 0; i < n; i++) len += dv().getUint32(iov + 8 * i + 4, true); dv().setUint32(out, len, true); return 0; },
      clock_time_get: (id, prec, out) => { dv().setBigUint64(out, BigInt(Math.round(currentTime * 1e9)), true); return 0; },
      proc_exit: () => { this.halted = true; },
    };
    return { wasi_snapshot_preview1: new Proxy(wasi, { get: (t, k) => (k in t ? t[k] : () => 8) }) };   // EBADF
  }

  // démarre le firmware (neuf) sur la flash donnée : la suite de la section 7 du format
  async start(flash, master) {
    const instance = await WebAssembly.instantiate(this.module, this.imports());      // (un Module : l'instance directe)
    const ex = (this.ex = instance.exports);
    this.halted = false;
    if (ex._initialize) ex._initialize();
    if (ex.rfm1_version() !== 1) throw new Error("version du format inconnue");
    const d = ex.rfm1_get(6);
    if (!d) throw new Error("le module ne parle pas l'ABI 6");
    const L = [];
    for (let i = 0; ; i++) { const v = ex.rfm1_layout(i); if (v < 0) break; L.push(v); }
    const u32 = (a) => new DataView(ex.memory.buffer).getUint32(a, true);
    this.L = L; this.panel = u32(d + L[D.panel]); this.keymap = u32(d + L[D.keymap]);
    this.flashSize = u32(d + L[D.flashSize]);
    const stage = (bytes) => {
      if (!bytes || !bytes.byteLength) { ex.rfm1_flash_stage(0, 0); return; }
      const p = ex.rfm1_alloc(bytes.byteLength);
      new Uint8Array(ex.memory.buffer, p, bytes.byteLength).set(new Uint8Array(bytes));
      ex.rfm1_flash_stage(p, bytes.byteLength);
      ex.rfm1_free(p);
    };
    stage(flash);
    const path = Uint8Array.from("fm1core:staged\0", (c) => c.charCodeAt(0));   // (pas de TextEncoder dans le fil audio)
    const pp = ex.rfm1_alloc(path.length);
    new Uint8Array(ex.memory.buffer, pp, path.length).set(path);
    ex.rfm1_options(pp, 0, 0, 1);
    ex.rfm1_boot_options(-1, 0, -1);
    this.bufAudio = ex.rfm1_alloc(BLOC * 4);
    this.bufMidi = ex.rfm1_alloc(4);
    this.u8(P.ready)[0] = 2;
    if (master != null) this.setMaster(master);
    ex.rfm1_init(0);
    this.ms = 0; this.audioFrames = 0; this.w = this.r = 0;
    this.dirty = ex.rfm1_flash_dirty(); this.dirtyAt = -1; this.sentWrites = -1;
    this.buttonsHeld = 0; this.keysHeld = 0;
  }

  // les champs de fm1panel_t, à nouveau pris dans la mémoire (qui peut avoir été réallouée)
  at(k) { return this.panel + this.L[k]; }
  u8(k, n = 1) { return new Uint8Array(this.ex.memory.buffer, this.at(k), n); }
  i32(k, n = 1) { return new Int32Array(this.ex.memory.buffer, this.at(k), n); }
  u32(k) { return new Uint32Array(this.ex.memory.buffer, this.at(k), 1); }
  setMaster(v) { this.i32(P.master)[0] = v | 0; }

  async onMessage(m) {
    if (m.type === "load") {
      try {
        this.module = await WebAssembly.compile(m.wasm);
        await this.start(m.flash instanceof ArrayBuffer ? m.flash : null, m.master);
        this.port.postMessage({ type: "ready" });
      } catch (err) {
        this.ex = null;
        this.port.postMessage({ type: "error", message: String((err && err.message) || err) });
      }
      return;
    }
    if (!this.ex) return;
    switch (m.type) {
      case "keys": this.keysHeld = m.mask >>> 0; this.u32(P.keys)[0] = this.keysHeld; break;
      case "buttons": this.buttonsHeld = m.mask >>> 0; this.u32(P.buttons)[0] = this.matrix(this.buttonsHeld); break;
      case "tap": this.u32(P.keysTap)[0] |= m.keys >>> 0; this.u32(P.buttonsTap)[0] |= this.matrix(m.buttons >>> 0); break;
      case "enc": {
        const role = m.role | 0;
        if (role < 0 || role >= NENC) break;
        const id = this.u8(P.encId, NENC)[role], dir = new Int8Array(this.ex.memory.buffer, this.at(P.encDir), NENC)[role];
        this.i32(P.enc, NENC)[id] += dir * (m.n | 0);
        break;
      }
      case "master": this.setMaster(m.value); break;
      case "midi": for (const p of m.pkts) this.midiIn.push(p >>> 0); break;
    }
  }

  // un masque de boutons dans l'ordre du panneau (FX .. OCT+) → les bits de la matrice du firmware (btn_id)
  matrix(mask) {
    const id = this.u8(P.btnId, NBTN);
    let out = 0;
    for (let i = 0; i < NBTN; i++) if ((mask >>> i) & 1) out |= 1 << id[i];
    return out >>> 0;
  }

  // un pas d'une milliseconde de l'appareil
  step() {
    const ex = this.ex;
    ex.rfm1_tick(this.ms);
    if (this.ms % 15 === 0) ex.rfm1_frame(); else ex.rfm1_idle();
    this.ms++;
    const due = Math.floor((this.ms * FS) / 1000);
    while (this.audioFrames + BLOC <= due) {
      ex.rfm1_audio(this.bufAudio, BLOC);
      const s = new Int16Array(ex.memory.buffer, this.bufAudio, BLOC * 2);
      for (let i = 0; i < BLOC; i++, this.w++) { this.fl[this.w & 16383] = s[2 * i] / 32768; this.fr[this.w & 16383] = s[2 * i + 1] / 32768; }
      this.audioFrames += BLOC;
    }
  }

  // les LED, 42 octets comme ChoralRoot : [0..26] touches, [27..40] boutons (ordre du panneau), [41] le vert de PLAY
  leds() {
    const ex = this.ex, led = new Uint8Array(ex.memory.buffer, this.at(P.led), NCOL * NLINE);
    const km = new Int8Array(ex.memory.buffer, this.keymap, 6 * NCOL), where = new Map();
    for (let r = 0; r < 6; r++) for (let c = 0; c < NCOL; c++) if (km[r * NCOL + c] >= 0 && r >= 1 && r <= 4) where.set(km[r * NCOL + c], c * NLINE + r - 1);
    const level = (v) => (v >= 176 ? 2 : v >= 96 ? 3 : v >= 40 ? 4 : v ? 1 : 0);
    const out = new Uint8Array(42), id = this.u8(P.btnId, NBTN);
    for (let k = 0; k < NKEY; k++) { const w = where.get(14 + k); out[k] = w === undefined ? 0 : level(led[w]); }
    for (let i = 0; i < NBTN; i++) { const w = where.get(id[i]); out[27 + i] = w === undefined ? 0 : level(led[w]); }
    out[41] = this.u8(P.playGreen)[0] >= 176 ? 1 : 0;
    return out;
  }

  publish() {
    const ex = this.ex, msg = { type: "frame", leds: this.leds(), layout: 0 }, transfer = [];
    if (this.frames >= 22050) {
      msg.load = Math.round((100 * this.busy) / ((this.frames / sampleRate) * 1000));
      this.busy = this.frames = 0;
    }
    const writes = this.u32(P.lcdWrites)[0];
    if (writes !== this.sentWrites) {
      this.sentWrites = writes;
      msg.fb = new Uint16Array(ex.memory.buffer, this.at(P.lcd), LCD).slice();   // l'ordre de la dalle : celui que la page attend
      transfer.push(msg.fb.buffer);
    }
    const d = ex.rfm1_flash_dirty();                      // la flash : gardée une seconde après la dernière écriture
    if (d !== this.dirty) { this.dirty = d; this.dirtyAt = currentTime; }
    else if (this.dirtyAt >= 0 && currentTime - this.dirtyAt > 1) {
      this.dirtyAt = -1;
      if (ex.rfm1_flash_sync()) {
        const f = new Uint8Array(ex.memory.buffer, ex.rfm1_flash(), this.flashSize).slice();
        this.port.postMessage({ type: "flash", data: f.buffer }, [f.buffer]);
      } else this.dirtyAt = currentTime;                  // un enregistrement encore différé par le firmware : plus tard
    }
    this.port.postMessage(msg, transfer);
  }

  process(inputs, outputs) {
    const ex = this.ex;
    if (!ex) return true;
    const out = outputs[0], n = out[0].length, t0 = clock();
    if (this.halted || ex.rfm1_halted()) {               // le firmware a redémarré : on le rallume sur sa flash
      const f = new Uint8Array(ex.memory.buffer, ex.rfm1_flash(), this.flashSize).slice();
      this.ex = null;
      this.start(f.buffer, null).catch(() => {});      // (this.ex revient dès que la nouvelle instance est prête)
      return true;
    }
    while (this.midiIn.length && ex.rfm1_midi_in(this.midiIn[0])) this.midiIn.shift();
    while (this.w - this.r < n) this.step();
    for (let i = 0; i < n; i++, this.r++) { out[0][i] = this.fl[this.r & 16383]; if (out[1]) out[1][i] = this.fr[this.r & 16383]; }
    let pkts = null;
    for (let k = 0; k < 64 && ex.rfm1_midi_out_take(this.bufMidi); k++) (pkts ||= []).push(new DataView(ex.memory.buffer).getUint32(this.bufMidi, true));
    if (pkts) this.port.postMessage({ type: "midi", pkts });
    this.busy += clock() - t0; this.frames += n;
    if (currentTime - this.lastPub >= 1 / 60) { this.lastPub = currentTime; this.publish(); }
    return true;
  }
}

registerProcessor("rfm1", Rfm1);
