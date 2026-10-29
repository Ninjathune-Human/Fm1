"use strict";
// the 32 algorithms: for each operator (0 = OP1), the operators that modulate it; the carriers; feedback [dst, src]
const ALG = (() => {
  const A = (m, c, fb) => {
    const mods = [[], [], [], [], [], []];
    for (const [dst, src] of m) mods[dst - 1].push(src - 1);
    return { mods, car: c.map((x) => x - 1), fb: [fb[0] - 1, fb[1] - 1] };
  };
  const s = (a, b) => [a, b];
  return [
    A([s(1, 2), s(3, 4), s(4, 5), s(5, 6)], [1, 3], [6, 6]),
    A([s(1, 2), s(3, 4), s(4, 5), s(5, 6)], [1, 3], [2, 2]),
    A([s(1, 2), s(2, 3), s(4, 5), s(5, 6)], [1, 4], [6, 6]),
    A([s(1, 2), s(2, 3), s(4, 5), s(5, 6)], [1, 4], [6, 4]),
    A([s(1, 2), s(3, 4), s(5, 6)], [1, 3, 5], [6, 6]),
    A([s(1, 2), s(3, 4), s(5, 6)], [1, 3, 5], [6, 5]),
    A([s(1, 2), s(3, 4), s(3, 5), s(5, 6)], [1, 3], [6, 6]),
    A([s(1, 2), s(3, 4), s(3, 5), s(5, 6)], [1, 3], [4, 4]),
    A([s(1, 2), s(3, 4), s(3, 5), s(5, 6)], [1, 3], [2, 2]),
    A([s(1, 2), s(2, 3), s(4, 5), s(4, 6)], [1, 4], [3, 3]),
    A([s(1, 2), s(2, 3), s(4, 5), s(4, 6)], [1, 4], [6, 6]),
    A([s(1, 2), s(3, 4), s(3, 5), s(3, 6)], [1, 3], [2, 2]),
    A([s(1, 2), s(3, 4), s(3, 5), s(3, 6)], [1, 3], [6, 6]),
    A([s(1, 2), s(3, 4), s(4, 5), s(4, 6)], [1, 3], [6, 6]),
    A([s(1, 2), s(3, 4), s(4, 5), s(4, 6)], [1, 3], [2, 2]),
    A([s(1, 2), s(1, 3), s(3, 4), s(1, 5), s(5, 6)], [1], [6, 6]),
    A([s(1, 2), s(1, 3), s(3, 4), s(1, 5), s(5, 6)], [1], [2, 2]),
    A([s(1, 2), s(1, 3), s(1, 4), s(4, 5), s(5, 6)], [1], [3, 3]),
    A([s(1, 2), s(2, 3), s(4, 6), s(5, 6)], [1, 4, 5], [6, 6]),
    A([s(1, 3), s(2, 3), s(4, 5), s(4, 6)], [1, 2, 4], [3, 3]),
    A([s(1, 3), s(2, 3), s(4, 6), s(5, 6)], [1, 2, 4, 5], [3, 3]),
    A([s(1, 2), s(3, 6), s(4, 6), s(5, 6)], [1, 3, 4, 5], [6, 6]),
    A([s(2, 3), s(4, 6), s(5, 6)], [1, 2, 4, 5], [6, 6]),
    A([s(3, 6), s(4, 6), s(5, 6)], [1, 2, 3, 4, 5], [6, 6]),
    A([s(4, 6), s(5, 6)], [1, 2, 3, 4, 5], [6, 6]),
    A([s(2, 3), s(4, 5), s(4, 6)], [1, 2, 4], [6, 6]),
    A([s(2, 3), s(4, 5), s(4, 6)], [1, 2, 4], [3, 3]),
    A([s(1, 2), s(3, 4), s(4, 5)], [1, 3, 6], [5, 5]),
    A([s(3, 4), s(5, 6)], [1, 2, 3, 5], [6, 6]),
    A([s(3, 4), s(4, 5)], [1, 2, 3, 6], [5, 5]),
    A([s(5, 6)], [1, 2, 3, 4, 5], [6, 6]),
    A([], [1, 2, 3, 4, 5, 6], [6, 6]),
  ];
})();


// FM-1+VA emulator: the sound engine, in an AudioWorklet.
// A reimplementation written from Baud Girl's FM-1+VA manual (Version 102); not her firmware.
// Three engines (FM 6-op on the DX7 model, Virtual Analog, 8-Bit), the shared LFO and envelope,
// the seven effects in the preset's order, and the Note Engine.
"use strict";
const SR = sampleRate;
const TAU = 2 * Math.PI;
const BLK = 32;                                    // control block, in samples
const clamp = (x, a, b) => (x < a ? a : x > b ? b : x);
const mtof = (n) => 440 * Math.pow(2, (n - 69) / 12);
const lin = (a, b, t) => a + (b - a) * t;

// ------------------------------------------------------------------ tables
const SN = 4096, SINT = new Float32Array(SN + 1);
for (let i = 0; i <= SN; i++) SINT[i] = Math.sin(TAU * i / SN);
function sin1(ph) {                                // ph in cycles
  ph -= Math.floor(ph);
  const x = ph * SN, i = x | 0, a = SINT[i];
  return a + (SINT[i + 1] - a) * (x - i);
}
function blep(t, dt) {
  if (t < dt) { t /= dt; return t + t - t * t - 1; }
  if (t > 1 - dt) { t = (t - 1) / dt; return t * t + t + t + 1; }
  return 0;
}
let rng = 22222;
const rnd = () => { rng = (rng * 1664525 + 1013904223) >>> 0; return rng / 4294967296; };

// ------------------------------------------------------------------ DX7 scaling (after MSFA)
const LEVLUT = [0, 5, 9, 13, 17, 20, 23, 25, 27, 29, 31, 33, 35, 37, 39, 41, 42, 43, 45, 46];
const scaleLevel = (l) => (l >= 20 ? 28 + l : LEVLUT[l | 0]);
const VELDATA = [0, 70, 86, 97, 106, 114, 121, 126, 132, 138, 142, 148, 152, 156, 160, 163, 166, 170, 173, 174, 178, 181,
  184, 186, 189, 190, 194, 196, 198, 200, 202, 205, 206, 209, 211, 214, 216, 218, 220, 222, 224, 225, 227, 229, 230, 232,
  233, 235, 237, 238, 240, 241, 242, 243, 244, 246, 246, 248, 249, 250, 251, 252, 253, 254];
function scaleVelocity(vel, sens) {
  const v = VELDATA[clamp(vel | 0, 0, 127) >> 1] - 239;
  return ((sens * v + 7) >> 3) << 4;
}
const EXPSCALE = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 14, 16, 19, 23, 27, 33, 39, 47, 56, 66, 80, 94, 110, 126, 142, 158, 174,
  190, 206, 222, 238, 250];
function scaleCurve(group, depth, curve) {
  let s;
  if (curve === 0 || curve === 3) s = (group * depth * 329) >> 12;
  else s = (EXPSCALE[Math.min(group, EXPSCALE.length - 1)] * depth * 329) >> 15;
  return curve < 2 ? -s : s;
}
function keyScale(note, bp, ld, rd, lc, rc) {
  const off = note - bp - 17;
  if (off >= 0) return scaleCurve(((off + 1) / 3) | 0, rd, rc);
  return scaleCurve((-(off - 1) / 3) | 0, ld, lc);
}
const rateScale = (note, rs) => (rs * clamp(((note / 3) | 0) - 7, 0, 31)) >> 3;
const envInc = (q) => (4 + (q & 3)) * Math.pow(2, (q >> 2) - 16) * (BLK / 64);   // octaves per block
const PITCHTAB = [-128, -116, -104, -95, -85, -76, -68, -61, -56, -52, -49, -46, -43, -41, -39, -37, -35, -33, -32, -31,
  -30, -29, -28, -27, -26, -25, -24, -23, -22, -21, -20, -19, -18, -17, -16, -15, -14, -13, -12, -11, -10, -9, -8, -7, -6,
  -5, -4, -3, -2, -1, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27,
  28, 29, 30, 31, 32, 33, 34, 35, 38, 40, 43, 46, 49, 53, 58, 65, 73, 82, 92, 103, 115, 127];
const PMSTAB = [0, 10, 20, 33, 55, 92, 153, 255], AMSTAB = [0, 66, 109, 255];
const lfoHz = (speed) => {
  let sr = speed === 0 ? 1 : (165 * speed) >> 6;
  sr *= sr < 160 ? 11 : 11 + ((sr - 160) >> 4);
  return sr * 25190424 / 4294967296;
};

// ------------------------------------------------------------------ shared pieces
// Attack and Decay of the preset Envelope: 5 ms at 1, doubling about every nine steps, 10 s at 100; 0 is immediate
const adTime = (v) => (v <= 0 ? 0 : 0.005 * Math.pow(2, v / 9.1));
const relTime = (v) => 0.1 * Math.pow(20, v / 100);                // 0.1 s at 0, 2 s at 100
const cutHz = (i) => 20 * Math.pow(1000, i / 127);                  // cutoff index 0..127 -> 20 Hz..20 kHz

class ADSR {                                       // the preset Envelope (and the gate when it is Off)
  constructor() { this.v = 0; this.st = 0; }
  start(legato) { if (!legato) this.st = 1; else if (this.st >= 4) this.st = 1; }
  release() { if (this.st && this.st < 4) this.st = 4; }
  // one control block; on: the preset Envelope's rows, or null for a plain gate
  step(on, a, d, s, r, dt) {
    const sus = s / 100;
    switch (this.st) {
      case 1: { const t = on ? adTime(a) : 0.002; this.v = t > 0 ? this.v + dt / t : 1; if (this.v >= 1) { this.v = 1; this.st = on ? 2 : 3; } break; }
      case 2: { const t = adTime(d); if (s <= 0 && t === 0) { this.v = 0; this.st = 3; break; }
        const k = t > 0 ? Math.exp(-dt * 4.6 / t) : 0; this.v = sus + (this.v - sus) * k;
        if (Math.abs(this.v - sus) < 1e-3) { this.v = sus; this.st = 3; } break; }
      case 3: if (on) { if (s <= 0) { const t = Math.max(adTime(d), 0.05); this.v *= Math.exp(-dt * 4.6 / t); } else this.v = sus; } break;
      case 4: { const t = relTime(r); this.v *= Math.exp(-dt * 6.9 / t); if (this.v < 1e-4) { this.v = 0; this.st = 5; } break; }
    }
    return this.v;
  }
  get done() { return this.st === 5; }
}

class SVF {                                        // the TPT state variable filter
  constructor() { this.a1 = 1; this.a2 = 0; this.a3 = 0; this.k = 2; this.ic1 = 0; this.ic2 = 0; }
  set(fc, k) {
    const g = Math.tan(Math.PI * clamp(fc, 16, SR * 0.45) / SR);
    this.k = k; this.a1 = 1 / (1 + g * (g + k)); this.a2 = g * this.a1; this.a3 = g * this.a2;
  }
  run(x, mode) {
    const v3 = x - this.ic2, v1 = this.a1 * this.ic1 + this.a2 * v3, v2 = this.ic2 + this.a2 * this.ic1 + this.a3 * v3;
    this.ic1 = 2 * v1 - this.ic1; this.ic2 = 2 * v2 - this.ic2;
    return mode === 0 ? v2 : mode === 1 ? v1 : x - this.k * v1 - v2;
  }
  reset() { this.ic1 = this.ic2 = 0; }
}

// the voice filter of a Virtual Analog preset, and of an FM preset with its Filter On: LP12, LP24, BP, HP
class VoiceFilter {
  constructor() { this.a = new SVF(); this.b = new SVF(); this.t = 0; this.fenv = 0; }
  start() { this.a.reset(); this.b.reset(); this.t = 0; }
  // cutoff in Hz from the rows, the note, its velocity and the LFO; dt one control block
  control(f, note, vel, lfo, dt) {
    const dec = 0.005 * Math.pow(2, f.decay / 10), att = dec * Math.pow(f.shape / 100, 1.6);
    this.t += dt;
    let e;
    if (this.t < att) e = this.t / att;
    else e = Math.pow(Math.exp(-(this.t - att) * 4.6 / dec), 1 + f.shape / 50);
    this.fenv = e;
    let oct = Math.log2(cutHz(f.cutoff));
    oct += (f.env / 100) * 7 * e + (f.vel / 100) * 3 * (vel / 127) + (f.kt / 100) * (note - 60) / 12 + (f.lfo / 100) * 3 * lfo;
    const fc = Math.pow(2, oct), res = f.res / 100;
    this.type = f.type;
    if (f.type === 1) { this.a.set(fc, 2 - 1.2 * res); this.b.set(fc, 2 - 1.96 * res); }
    else this.a.set(fc, 2 - 1.96 * res);
  }
  run(x) {
    switch (this.type) {
      case 0: return this.a.run(x, 0);
      case 1: return this.b.run(this.a.run(x, 0), 0);
      case 2: return this.a.run(x, 1);
      default: return this.a.run(x, 2);
    }
  }
}

// ------------------------------------------------------------------ the FM voice
class FMVoice {
  constructor(eng) {
    this.eng = eng; this.kind = "fm"; this.active = false;
    this.ph = new Float64Array(6); this.o = new Float64Array(6); this.E = new Float64Array(6); this.st = new Int8Array(6);
    this.T = [new Float64Array(6), new Float64Array(6), new Float64Array(6), new Float64Array(6)];
    this.q = [new Int8Array(6), new Int8Array(6), new Int8Array(6), new Int8Array(6)];
    this.inc = new Float64Array(6); this.g0 = new Float64Array(6); this.g1 = new Float64Array(6);
    this.env = new ADSR(); this.filt = new VoiceFilter(); this.y1 = 0; this.y2 = 0;
  }
  start(p, note, vel, legato) {
    const fm = p.fm;
    const was = this.active;
    this.p = p; this.vel = vel; this.gate = true; this.active = true; this.age = this.eng.clock++;
    if (legato && was) { this.note = note; for (let i = 0; i < 6; i++) if (this.st[i] >= 4) this.st[i] = 3; this.env.start(true); return this.retune(); }
    this.note = note; this.pitch = note; this.glideFrom = note; this.alg = ALG[clamp(fm.alg - 1, 0, 31)];
    for (let i = 0; i < 6; i++) {
      const op = fm.ops[i];
      let outlev = scaleLevel(op.ol) + keyScale(note, op.bp, op.ld, op.rd, op.lc, op.rc);
      outlev = Math.min(127, outlev) << 5;
      outlev = Math.max(0, outlev + scaleVelocity(vel, op.vel));
      const rs = rateScale(note, op.rs);
      for (let j = 0; j < 4; j++) {
        this.T[j][i] = Math.max(16, ((scaleLevel(op.l[j]) >> 1) << 6) + outlev - 4256) / 256;
        this.q[j][i] = Math.min(63, ((op.r[j] * 41) >> 6) + rs);
      }
      this.E[i] = this.T[3][i];
      this.st[i] = 0;
      this.g0[i] = this.g1[i] = Math.pow(2, this.E[i] - 14);
      if (fm.sync) this.ph[i] = 0;
      this.o[i] = 0;
    }
    this.y1 = this.y2 = 0;
    this.peg = PITCHTAB[fm.peg.l[3]] / 32; this.pst = 0;
    this.env.start(false); this.filt.start(); this.lfoT = 0;
    this.retune();
  }
  retune() {
    const fm = this.p.fm;
    this.ratio = fm.ops.map((op) => {
      if (op.fixed) return -Math.pow(10, (op.coarse & 3) + op.fine / 100);
      return (op.coarse === 0 ? 0.5 : op.coarse) * (1 + op.fine / 100) * Math.pow(2, (op.detune - 7) * 1.6 / 1200);
    });
  }
  release() { this.gate = false; for (let i = 0; i < 6; i++) this.st[i] = 4; this.env.release(); }
  kill() { this.active = false; }
  control(eng, dt) {
    const p = this.p, fm = p.fm, lfo = eng.lfoOut(this, dt);
    // operator envelopes
    let loud = 0;
    for (let i = 0; i < 6; i++) {
      let s = this.st[i];
      const j = s === 4 ? 3 : Math.min(s, 2);
      if (s !== 3 && s !== 5) {
        const T = this.T[j][i], q = this.q[j][i], E = this.E[i];
        if (T > E) { const ne = E + (17 - Math.floor(E)) * envInc(q); if (ne >= T) { this.E[i] = T; s = s === 4 ? 5 : s + 1; } else this.E[i] = ne; }
        else { const ne = E - envInc(q); if (ne <= T) { this.E[i] = T; s = s === 4 ? 5 : s + 1; } else this.E[i] = ne; }
        this.st[i] = s;
      }
      const op = fm.ops[i], am = eng.amd(p) * (AMSTAB[op.ams] / 255) * 6 * lfo.amp;
      const live = p.fm.ops[i].on !== 0;
      this.g0[i] = this.g1[i];
      this.g1[i] = live ? Math.pow(2, this.E[i] - am - 14) : 0;
    }
    for (const c of this.alg.car) loud = Math.max(loud, this.g1[c]);
    // pitch envelope
    const pr = fm.peg;
    {
      const s = this.pst, j = s === 4 ? 3 : Math.min(s, 2);
      if (s !== 3 && s !== 5) {
        const tgt = PITCHTAB[pr.l[j]] / 32, sp = 0.025 * Math.pow(2, pr.r[j] / 8) * dt;
        if (Math.abs(tgt - this.peg) <= sp) { this.peg = tgt; this.pst = s === 4 ? 5 : s + 1; }
        else this.peg += tgt > this.peg ? sp : -sp;
      }
      if (!this.gate && this.pst < 4) this.pst = 4;
    }
    // glide, then the frequencies
    const gt = eng.glideTime(p);
    if (gt > 0 && this.pitch !== this.note) {
      const k = Math.exp(-dt * 4 / gt);
      this.pitch = this.note + (this.pitch - this.note) * k;
      if (Math.abs(this.pitch - this.note) < 0.01) this.pitch = this.note;
    } else this.pitch = this.note;
    const semis = this.pitch + (fm.transpose - 24) + this.peg * 12 + lfo.pitch * 12 * (PMSTAB[p.lfo.pms] / 255) * eng.pmd(p) + eng.tune + eng.bend;
    const base = mtof(semis);
    for (let i = 0; i < 6; i++) { const r = this.ratio[i]; this.inc[i] = (r < 0 ? -r : base * r) / SR; }
    // preset Envelope (Off: a plain gate) and the filter
    const e = p.env;
    this.amp0 = this.amp1 === undefined ? 0 : this.amp1;
    this.amp1 = e.on ? this.env.step(true, e.a, e.d, e.s, e.r, dt) : 1;
    this.useFilt = fm.filt.on;
    if (this.useFilt) this.filt.control(fm.filt, this.note, this.vel, lfo.raw, dt);
    if ((this.st.every((s) => s === 5) || (!this.gate && loud < 2e-4)) || (e.on && this.env.done)) this.active = false;
  }
  render(out, n) {
    const alg = this.alg, mods = alg.mods, car = alg.car, nc = car.length, fbd = alg.fb[0], fbs = alg.fb[1];
    const fb = this.p.fm.fb, fbAmt = fb ? Math.pow(2, fb - 9) : 0;
    const ph = this.ph, o = this.o, inc = this.inc, g0 = this.g0, g1 = this.g1, flt = this.useFilt;
    const a0 = this.amp0, a1 = this.amp1;
    for (let s = 0; s < n; s++) {
      const t = (s + 1) / n;
      for (let i = 5; i >= 0; i--) {
        const g = g0[i] + (g1[i] - g0[i]) * t;
        ph[i] += inc[i];
        if (g < 1e-6) { o[i] = 0; continue; }
        let m = 0;
        const md = mods[i];
        for (let k = 0; k < md.length; k++) m += o[md[k]];
        if (i === fbd) m += fbAmt * (this.y1 + this.y2);
        o[i] = sin1(ph[i] + m) * g;
      }
      this.y2 = this.y1; this.y1 = o[fbs];
      let y = 0;
      for (let k = 0; k < nc; k++) y += o[car[k]];
      y *= 0.5 * (a0 + (a1 - a0) * t);
      if (flt) y = this.filt.run(y);
      out[s] += y;
    }
    for (let i = 0; i < 6; i++) if (ph[i] > 1e6) ph[i] -= Math.floor(ph[i]);
  }
}

// ------------------------------------------------------------------ the Virtual Analog voice
class VAVoice {
  constructor(eng) {
    this.eng = eng; this.kind = "va"; this.active = false;
    this.ph = new Float64Array(7); this.dr = new Float64Array(7); this.dt = new Float64Array(7); this.dtim = new Float64Array(7);
    this.inc = new Float64Array(7); this.env = new ADSR(); this.filt = new VoiceFilter(); this.sub = 0;
  }
  start(p, note, vel, legato) {
    this.p = p; this.vel = vel; this.gate = true; this.age = this.eng.clock++;
    if (legato && this.active) { this.note = note; this.env.start(true); return; }
    this.active = true; this.note = note; this.pitch = note;
    for (let i = 0; i < 7; i++) { this.ph[i] = i ? rnd() : 0; this.dr[i] = 0; this.dt[i] = rnd() * 2 - 1; this.dtim[i] = 0; }
    this.sub = 0; this.pwt = rnd();
    this.env.v = 0; this.env.start(false); this.filt.start(); this.lfoT = 0; this.amp1 = 0;
  }
  release() { this.gate = false; this.env.release(); }
  control(eng, dt) {
    const p = this.p, va = p.va, lfo = eng.lfoOut(this, dt);
    const gt = eng.glideTime(p);
    if (gt > 0 && this.pitch !== this.note) { this.pitch = this.note + (this.pitch - this.note) * Math.exp(-dt * 4 / gt); if (Math.abs(this.pitch - this.note) < 0.01) this.pitch = this.note; }
    else this.pitch = this.note;
    // drift: a few cents through the first half, wonky above it
    const d = va.drift / 100, cents = d <= 0.5 ? 12 * d : 6 + (d - 0.5) * 2 * 90, rate = 0.25 + (d > 0.5 ? (d - 0.5) * 2 * 5 : 0);
    const semis = this.pitch + lfo.pitch * 12 * (PMSTAB[p.lfo.pms] / 255) * eng.pmd(p) + eng.tune + eng.bend;
    const spread = va.detune / 100 * 0.6;            // semitones, at the outer copies
    const OFF = [0, -1, -0.66, -0.33, 0.33, 0.66, 1];
    for (let i = 0; i < 7; i++) {
      this.dtim[i] -= dt;
      if (this.dtim[i] <= 0) { this.dtim[i] = (0.5 + rnd()) / rate; this.dt[i] = rnd() * 2 - 1; }
      this.dr[i] += (this.dt[i] - this.dr[i]) * Math.min(1, dt * rate * 2);
      const st = semis + OFF[i] * spread + this.dr[i] * cents / 100;
      this.inc[i] = mtof(st) / SR;
    }
    this.subInc = mtof(semis - 12 + this.dr[0] * cents / 100) / SR;
    this.pwt += dt * 0.7;
    this.width = 0.5 + 0.42 * (va.pwm / 100) * Math.sin(TAU * this.pwt);
    this.filt.control(va.filt, this.note, this.vel, lfo.raw, dt);
    // loudness: Level (0.74 dB a step), Velocity to Level, the LFO, the Envelope (Off: a gate and Release)
    const e = p.env;
    const lv = va.level <= 0 ? 0 : 3.2 * Math.pow(10, -(99 - va.level) * 0.74 / 20);
    const vl = 1 - (va.vel2lvl / 7) * 0.9 * (1 - this.vel / 127);
    const am = 1 - eng.amd(p) * 0.9 * lfo.amp;
    let ev;
    if (e.on) ev = this.env.step(true, e.a, e.d, e.s, e.r, dt);
    else ev = this.env.step(false, 0, 0, 100, e.r, dt);
    this.amp0 = this.amp1; this.amp1 = ev * lv * vl * am;
    if (this.env.done) this.active = false;
  }
  render(out, n) {
    const va = this.p.va, w = va.wave, sup = va.super / 100, cnt = sup > 0 ? 7 : 1;
    const ph = this.ph, inc = this.inc, width = this.width;
    const mainG = 1 - 0.35 * sup, cpG = sup * 0.42, subG = va.sub / 100 * 0.8, nzG = va.noise / 100 * 0.6;
    const f = this.filt, a0 = this.amp0, a1 = this.amp1;
    for (let s = 0; s < n; s++) {
      let x = 0;
      for (let i = 0; i < cnt; i++) {
        const dt = inc[i];
        let t = ph[i] + dt; if (t >= 1) t -= 1; ph[i] = t;
        let y;
        if (w === 0) y = sin1(t);
        else if (w === 1) y = 2 * t - 1 - blep(t, dt);
        else if (w === 2) y = 4 * Math.abs(t - 0.5) - 1;
        else { let t2 = t - width + 1; t2 -= Math.floor(t2); y = (t < width ? 1 : -1) + blep(t, dt) - blep(t2, dt); }
        x += i === 0 ? y * mainG : y * cpG;
      }
      if (subG > 0) { this.sub += this.subInc; if (this.sub >= 1) this.sub -= 1; let t2 = this.sub + 0.5; t2 -= Math.floor(t2); x += subG * ((this.sub < 0.5 ? 1 : -1) + blep(this.sub, this.subInc) - blep(t2, this.subInc)); }
      if (nzG > 0) x += nzG * (rnd() * 2 - 1);
      out[s] += f.run(x) * (a0 + (a1 - a0) * (s + 1) / n);
    }
  }
}

// ------------------------------------------------------------------ the 8-Bit engine
// waves: 0..3 pulse 12.5/25/50/75, 4 triangle, 5 noise, 6 metal, 7..14 the Game Boy wave channel's 32 x 4-bit tables
const DUTY = [0.125, 0.25, 0.5, 0.75];
const TRI32 = Array.from({ length: 32 }, (_, i) => (i < 16 ? 15 - i : i - 16));
const GBW = (() => {
  const q = (f) => Array.from({ length: 32 }, (_, i) => clamp(Math.round(f(i)), 0, 15));
  return [
    q((i) => i >> 1),                                                                   // GB Saw
    q((i) => 7.5 + 7.5 * Math.sin(TAU * i / 32)),                                        // GB Sine
    q((i) => 15 * Math.abs(Math.sin(Math.PI * i / 32))),                                 // GB Half
    q((i) => 7.5 + 7.5 * (0.55 * Math.sin(TAU * i / 32) + 0.3 * Math.sin(2 * TAU * i / 32) + 0.25 * Math.sin(4 * TAU * i / 32)) / 0.95), // GB Organ
    q((i) => (i & 15)),                                                                  // GB Twin
    q((i) => (i < 16 ? 15 - i * 0.35 : (i - 16) * 0.35)),                               // GB Bass
    q((i) => 7.5 + 7.5 * (0.6 * Math.sin(TAU * i / 32) + 0.3 * Math.sin(5 * TAU * i / 32) + 0.25 * Math.sin(7 * TAU * i / 32)) / 1.0), // GB Bell
    q((i) => (i < 3 ? 15 : 12 - i * 0.38)),                                              // GB Buzz
  ];
})();
// duty sequences: widths (as 0..3) per console frame (60 Hz); a trailing -1 holds the last
const DUTYSEQ = [null,
  [0, 1], [1, 2], [0, 2], [0, 1, 2, 3, 2, 1], [1, 1, 2, 2], [1, 1, 1, 1, 2, 2, 2, 2], [2, 2, 2, 1, -1], [0, 0, 1, 2, -1],
  [2, 2, 1, 1, 0, -1], [0, 0, 1, 1, 2, -1], [1, 3], [0, 1, 2, 3, 3, 2, 1, 0], [0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1],
  [1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2]];
const ARPS = [null, [0, 4, 7], [0, 3, 7], [0, 4, 7, 12], [0, 3, 7, 12], [0, 12], [0, 12, 24], [0, 7], [0, 7, 12], [0, 5, 7],
  [0, 2, 7], [0, 3, 6], [0, 4, 8], [0, 4, 7, 11], [0, 3, 7, 10], [0, 4, 7, 10], [0, 4, 7, 9], [0, 3, 7, 9], [12, 7, 4, 0],
  [12, 7, 3, 0], [0, 4, 7, 12, 7, 4], [0, 3, 7, 12, 7, 3], [0, 1], [0, 2], [0, 3], [0, 4], [0, 5], [0, -12], [0, 7, 12, 19],
  [0, 4, 7, 12, 16, 19, 24], [0, 3, 7, 12, 15, 19, 24], [0, 12, 0, -12]];   // 32 = User
const ARPSPEED = [1 / 2, 1 / 3, 1 / 4, 1 / 6, 1 / 8, 1 / 12, 1 / 24];      // in beats
const B8 = { DRUM: 17, SFX: 29, BASS: 41, LEAD: 77, TOP: 112 };          // F0, F1, F2, F5, E8
const t8 = (v) => (v <= 0 ? 0 : 0.002 * Math.pow(2, v / 9.9));           // 0..99 -> 0..2 s
const CPU = 1789773;
function chipHz(f, wave) {                                                // the console divider's nearest pitch
  if (wave <= 3) { const t = Math.round(CPU / (16 * f)) - 1; return t < 8 || t > 2047 ? 0 : CPU / (16 * (t + 1)); }
  if (wave === 4) { const t = Math.round(CPU / (32 * f)) - 1; return t < 2 || t > 2047 ? 0 : CPU / (32 * (t + 1)); }
  if (wave >= 7) { const x = Math.round(2048 - 65536 / f); return x < 0 || x > 2047 ? 0 : 65536 / (2048 - x); }
  return f;
}
class Chip {                                       // one 8-Bit oscillator
  constructor() { this.ph = 0; this.lfsr = 1; this.acc = 0; this.nz = 0; }
  sample(wave, inc, duty, smooth) {
    let t = this.ph + inc; if (t >= 1) t -= 1; this.ph = t;
    if (wave <= 3) {
      const w = DUTY[duty];
      if (!smooth) return t < w ? 1 : -1;
      let t2 = t - w + 1; t2 -= Math.floor(t2);
      return (t < w ? 1 : -1) + blep(t, inc) - blep(t2, inc);
    }
    if (wave === 4) return TRI32[(t * 32) | 0] / 7.5 - 1;
    if (wave === 5 || wave === 6) {
      this.acc += inc * 16;
      while (this.acc >= 1) {
        this.acc -= 1;
        const bit = (this.lfsr ^ (this.lfsr >> (wave === 6 ? 6 : 1))) & 1;
        this.lfsr = (this.lfsr >> 1) | (bit << 14);
        this.nz = this.lfsr & 1 ? 1 : -1;
      }
      return this.nz;
    }
    return GBW[wave - 7][(t * 32) | 0] / 7.5 - 1;
  }
}

class PartVoice {                                  // the bass or the lead
  constructor(eng) { this.eng = eng; this.kind = "part"; this.active = false; this.osc = new Chip(); this.adsr = new ADSR(); }
  start(p, which, key, note, vel, chord, legato) {
    this.p = p; this.which = which; this.key = key; this.vel = vel; this.gate = true; this.age = this.eng.clock++;
    const part = p.b8[which];
    if (legato && this.active) { this.note = note; this.chord = chord; return; }
    this.active = true; this.note = note; this.pitch = note; this.chord = chord;
    this.t = 0; this.ai = 0; this.at = 0; this.frame = 0; this.sweep = 0; this.e = 0; this.st = 1; this.amp1 = 0;
    this.beatStep = this.eng.beatStep(part.speed);
    this.osc.ph = 0; this.lfoT = 0;
  }
  release() { this.gate = false; this.st = 4; }
  control(eng, dt) {
    const p = this.p, b = p.b8, part = b[this.which], lfo = eng.lfoOut(this, dt);
    this.t += dt;
    // the arpeggio steps on the key's own clock, or on the grid (Arp Sync Beat)
    const arp = this.chord;
    if (arp && arp.length > 1) {
      if (b.arpSync) { const s = eng.beatStep(part.speed); if (s !== this.beatStep) { this.beatStep = s; this.ai = (this.ai + 1) % arp.length; } }
      else { const len = ARPSPEED[part.speed] * 60 / eng.tempo; this.at += dt; while (this.at >= len) { this.at -= len; this.ai = (this.ai + 1) % arp.length; } }
    } else this.ai = 0;
    const off = arp ? arp[this.ai % arp.length] : 0;
    // glide (mono), sweep, vibrato
    const gt = part.mono && part.glide > 0 ? 0.5 * Math.pow(part.glide / 99, 2) : 0;
    if (gt > 0) { this.pitch = this.note + (this.pitch - this.note) * Math.exp(-dt * 4 / gt); } else this.pitch = this.note;
    this.sweep += part.sweep * 0.8 * dt;
    const vib = part.vib > 0 && this.t > 0.12 ? (part.vib / 99) * Math.sin(TAU * 5.5 * this.t) : 0;
    const semis = this.pitch + off + this.sweep + vib + lfo.pitch * 12 * (PMSTAB[p.lfo.pms] / 255) * eng.pmd(p) + eng.tune + eng.bend;
    let f = mtof(semis);
    if (b.tuning) f = chipHz(f, part.wave);
    this.inc = f / SR;
    // duty sequence, one step a console frame
    this.frame += dt * 60;
    const ds = DUTYSEQ[part.duty];
    if (ds && part.wave <= 3) {
      let i = Math.floor(this.frame);
      const hold = ds[ds.length - 1] === -1, len = hold ? ds.length - 1 : ds.length;
      i = hold ? Math.min(i, len - 1) : i % len;
      this.duty = ds[i];
    } else this.duty = part.wave <= 3 ? part.wave : 0;
    // the part's envelope
    const A = t8(part.a), D = t8(part.d), S = part.s / 99, R = t8(part.r);
    switch (this.st) {
      case 1: this.e = A > 0 ? this.e + dt / A : 1; if (this.e >= 1) { this.e = 1; this.st = 2; } break;
      case 2: this.e = D > 0 ? S + (this.e - S) * Math.exp(-dt * 4.6 / D) : S; if (Math.abs(this.e - S) < 1e-3) { this.e = S; this.st = 3; } break;
      case 3: this.e = S; break;
      case 4: this.e = R > 0 ? this.e * Math.exp(-dt * 6.9 / R) : 0; if (this.e < 1e-4) { this.e = 0; this.st = 5; this.active = false; } break;
    }
    let lvl = this.e * (part.level / 99) * (0.55 + 0.45 * this.vel / 127) * (1 - eng.amd(p) * 0.9 * lfo.amp);
    if (!b.tone) lvl = Math.round(lvl * 15) / 15;                                  // Raw: sixteen steps
    this.amp0 = this.amp1; this.amp1 = f > 0 ? lvl : 0;
    if (this.st === 3 && S <= 0) { this.st = 5; this.active = false; }
  }
  render(out, n) {
    const part = this.p.b8[this.which], smooth = !!this.p.b8.tone, raw = !smooth;
    const a0 = this.amp0, a1 = this.amp1, w = part.wave, inc = this.inc, d = this.duty;
    if (inc <= 0) return;
    for (let s = 0; s < n; s++) out[s] += this.osc.sample(w, inc, d, smooth) * (raw ? a1 : a0 + (a1 - a0) * (s + 1) / n) * 0.42;
  }
}

class DrumVoice {
  constructor(eng) { this.eng = eng; this.kind = "drum"; this.active = false; this.osc = new Chip(); this.nz = new Chip(); }
  start(p, idx, vel) {
    const d = p.b8.drums[idx], b = p.b8;
    this.p = p; this.idx = idx; this.vel = vel; this.active = true; this.gate = false; this.age = this.eng.clock++;
    this.key = B8.DRUM + idx;
    const dd = b.drumDecay >= 50 ? Math.pow(21, (b.drumDecay - 50) / 49) : Math.pow(23, -(50 - b.drumDecay) / 50);
    this.T = (0.012 * Math.pow(2, d.decay / 12)) * dd;
    this.f0 = 30 * Math.pow(2, d.pitch / 12);
    this.t = 0; this.choke = 1; this.chokeG = d.choke; this.osc.ph = 0; this.osc.lfsr = 1; this.nz.lfsr = 0x5a5a;
  }
  release() {}
  control(eng, dt) {
    const d = this.p.b8.drums[this.idx], b = this.p.b8;
    this.t += dt;
    const env = Math.pow(10, -3 * this.t / this.T);
    const sw = d.sweep, semis = sw * Math.min(1, this.t / Math.max(0.01, this.T * 0.35));
    let f = this.f0 * Math.pow(2, semis / 12);
    this.inc = Math.min(0.49, f / SR);
    this.nzInc = Math.min(0.49, 5000 / SR);
    const snapT = Math.min(this.T, 0.18);
    this.snap = (d.snap / 99) * Math.pow(10, -3 * this.t / snapT);
    if (this.choke < 1) this.choke = Math.max(0, this.choke - dt / 0.006);
    const dl = (d.level / 99) * (b.drumsLvl / 99);
    let lvl = env * dl * (0.55 + 0.45 * this.vel / 127) * this.choke;
    this.snap *= dl * this.choke;
    if (!b.tone) { lvl = Math.round(lvl * 15) / 15; this.snap = Math.round(this.snap * 15) / 15; }
    this.amp0 = this.amp1 === undefined ? lvl : this.amp1; this.amp1 = lvl;
    this.s0 = this.s1 === undefined ? this.snap : this.s1; this.s1 = this.snap;
    if (this.t > this.T * 1.05 || (this.choke <= 0)) this.active = false;
  }
  render(out, n) {
    const d = this.p.b8.drums[this.idx], smooth = !!this.p.b8.tone, w = d.wave;
    for (let s = 0; s < n; s++) {
      const k = (s + 1) / n;
      let y = this.osc.sample(w, this.inc, w <= 3 ? w : 0, smooth) * (this.amp0 + (this.amp1 - this.amp0) * k);
      const sn = this.s0 + (this.s1 - this.s0) * k;
      if (sn > 0) y += this.nz.sample(5, this.nzInc, 0, false) * sn * 0.8;
      out[s] += y * 0.5;
    }
  }
}

// the twelve sound effects: [duration s, function of t returning [Hz, wave, level]]
const SFX = [
  [0.45, (t) => [t < 0.07 ? 988 : 1319, 1, t < 0.07 ? 1 : Math.max(0, 1 - (t - 0.07) / 0.38)]],                  // Coin
  [0.3, (t) => [220 * Math.pow(2, t / 0.12), 2, 1 - t / 0.3]],                                                    // Jump
  [0.28, (t) => [2400 * Math.pow(0.1, t / 0.28), 0, 1 - t / 0.28]],                                                // Laser
  [0.18, (t) => [900 * Math.pow(0.25, t / 0.18), 5, 1 - t / 0.18]],                                                // Shoot
  [1.1, (t) => [180 * Math.pow(0.3, t / 1.1), 5, Math.pow(1 - t / 1.1, 2)]],                                      // Explosion
  [0.62, (t) => [mtof(72 + [0, 4, 7, 12, 16, 19, 24, 28][Math.min(7, Math.floor(t / 0.075))] + 5 * Math.sin(t * 60) * 0.02), 1, 1 - t / 0.7]], // Power-Up
  [0.66, (t) => [mtof([79, 83, 86, 91, 88, 95][Math.min(5, Math.floor(t / 0.11))]), 1, t > 0.55 ? (0.66 - t) / 0.11 : 1]], // 1-Up
  [0.32, (t) => [700 * Math.pow(0.35, t / 0.32) * (1 + 0.08 * Math.sin(TAU * 30 * t)), 2, 1 - t / 0.32]],           // Hurt
  [0.09, (t) => [1046, 1, 1 - t / 0.09]],                                                                          // Blip
  [1.0, (t) => [300 * Math.pow(4, t) * (1 + 0.12 * Math.sin(TAU * 9 * t)), 4, t < 0.8 ? 1 : (1 - t) / 0.2]],          // Warp
  [0.8, (t) => [Math.floor(t / 0.1) % 2 ? 660 : 880, 1, 0.9]],                                                    // Alarm
  [1.2, (t) => [1500 * Math.pow(0.07, t / 1.2), 2, 1 - t / 1.2]],                                                  // Fall
];
class SfxVoice {
  constructor(eng) { this.eng = eng; this.kind = "sfx"; this.active = false; this.osc = new Chip(); }
  start(p, idx, vel) { this.p = p; this.idx = idx; this.key = B8.SFX + idx; this.t = 0; this.active = true; this.gate = false; this.age = this.eng.clock++; this.osc.ph = 0; this.osc.lfsr = 1; this.amp1 = 0; }
  release() {}
  control(eng, dt) {
    const [dur, fn] = SFX[this.idx];
    this.t += dt;
    if (this.t >= dur) { this.active = false; this.amp1 = 0; return; }
    const [f, w, l] = fn(this.t);
    this.w = w; this.inc = Math.min(0.49, f / SR);
    let lvl = clamp(l, 0, 1) * 0.8;
    if (!this.p.b8.tone) lvl = Math.round(lvl * 15) / 15;
    this.amp0 = this.amp1; this.amp1 = lvl;
  }
  render(out, n) {
    if (!this.active) return;
    const smooth = !!this.p.b8.tone;
    for (let s = 0; s < n; s++) out[s] += this.osc.sample(this.w, this.inc, this.w <= 3 ? this.w : 0, smooth) * (this.amp0 + (this.amp1 - this.amp0) * (s + 1) / n) * 0.4;
  }
}

// ------------------------------------------------------------------ effects
class Reverb {                                     // Room, Hall, Plate: combs and allpasses, two channels
  constructor() { this.type = -1; }
  build(type) {
    this.type = type;
    const scale = [0.55, 1.0, 0.75][type] * SR / 44100;
    const C = [1116, 1188, 1277, 1356, 1422, 1491, 1557, 1617], A = [556, 441, 341, 225];
    const mk = (n) => ({ b: new Float32Array(Math.max(8, Math.round(n * scale))), i: 0, f: 0 });
    this.cl = C.map((n) => mk(n)); this.cr = C.map((n) => mk(n + 23));
    this.al = A.map((n) => mk(n)); this.ar = A.map((n) => mk(n + 23));
    this.pre = new Float32Array(Math.round(SR * [0.004, 0.02, 0.008][type]) + 1); this.pi = 0;
    this.damp = [0.45, 0.25, 0.12][type];
  }
  run(L, R, n, prm) {
    if (prm.type !== this.type) this.build(prm.type);
    const fbk = 0.7 + 0.285 * (prm.decay / 100), m = prm.mix / 100, dry = 1 - 0.5 * m, wet = m * 0.9, damp = this.damp;
    const comb = (c, x) => { const y = c.b[c.i]; c.f = y * (1 - damp) + c.f * damp; c.b[c.i] = x + c.f * fbk; if (++c.i >= c.b.length) c.i = 0; return y; };
    const ap = (a, x) => { const y = a.b[a.i]; a.b[a.i] = x + y * 0.5; if (++a.i >= a.b.length) a.i = 0; return y - x; };
    for (let s = 0; s < n; s++) {
      const x = (L[s] + R[s]) * 0.08;
      const pd = this.pre[this.pi]; this.pre[this.pi] = x; if (++this.pi >= this.pre.length) this.pi = 0;
      let yl = 0, yr = 0;
      for (let k = 0; k < 8; k++) { yl += comb(this.cl[k], pd); yr += comb(this.cr[k], pd); }
      for (let k = 0; k < 4; k++) { yl = ap(this.al[k], yl); yr = ap(this.ar[k], yr); }
      L[s] = L[s] * dry + yl * wet; R[s] = R[s] * dry + yr * wet;
    }
  }
}
class Delay {
  constructor() { this.bl = new Float32Array(SR); this.br = new Float32Array(SR); this.i = 0; this.fl = 0; this.fr = 0; this.t = 0.3; }
  run(L, R, n, prm) {
    const tgt = 0.8 * Math.pow(0.125, prm.rate / 100), fb = (prm.fb / 100) * 0.88, m = prm.mix / 100, N = this.bl.length;
    for (let s = 0; s < n; s++) {
      this.t += (tgt - this.t) * 0.0005;
      const d = this.t * SR, j = this.i - d, jl = (j + N) % N, j0 = Math.floor(jl), fr = jl - j0, j1 = (j0 + 1) % N;
      const yl = this.bl[j0] + (this.bl[j1] - this.bl[j0]) * fr, yr = this.br[j0] + (this.br[j1] - this.br[j0]) * fr;
      this.fl += (yl - this.fl) * 0.6; this.fr += (yr - this.fr) * 0.6;
      this.bl[this.i] = L[s] + this.fr * fb; this.br[this.i] = R[s] + this.fl * fb;   // a gentle cross-feed: ping-pong
      if (++this.i >= N) this.i = 0;
      L[s] = L[s] * (1 - 0.4 * m) + yl * m; R[s] = R[s] * (1 - 0.4 * m) + yr * m;
    }
  }
}
class Distortion {
  constructor() { this.zl = 0; this.zr = 0; }
  run(L, R, n, prm) {
    const g = Math.pow(10, (prm.gain / 100) * 36 / 20), lv = Math.pow(prm.level / 70, 1.5) * 0.9 / Math.pow(g, 0.35);
    const fc = 700 * Math.pow(20, prm.tone / 100), a = 1 - Math.exp(-TAU * fc / SR), ty = prm.type;
    const shape = (x) => {
      x *= g;
      if (ty === 0) return Math.tanh(x);
      if (ty === 1) return clamp(x, -1, 1);
      while (x > 1 || x < -1) x = x > 1 ? 2 - x : -2 - x;
      return x;
    };
    for (let s = 0; s < n; s++) {
      this.zl += (shape(L[s]) - this.zl) * a; this.zr += (shape(R[s]) - this.zr) * a;
      L[s] = this.zl * lv; R[s] = this.zr * lv;
    }
  }
}
class Chorus {
  constructor() { this.b = new Float32Array(4096); this.i = 0; this.ph = 0; }
  run(L, R, n, prm) {
    const hz = 0.1 + 0.9 * prm.rate / 100, dep = (prm.depth / 100) * 0.006 * SR, base = 0.012 * SR, m = prm.mix / 100, N = 4096;
    const rd = (d) => { let j = this.i - d; j += N; const j0 = Math.floor(j) % N, f = j - Math.floor(j); return this.b[j0] + (this.b[(j0 + 1) % N] - this.b[j0]) * f; };
    for (let s = 0; s < n; s++) {
      this.ph += hz / SR; if (this.ph >= 1) this.ph -= 1;
      this.b[this.i] = (L[s] + R[s]) * 0.5;
      const yl = rd(base + dep * (1 + sin1(this.ph)) * 0.5), yr = rd(base + dep * (1 + sin1(this.ph + 0.25)) * 0.5);
      this.i = (this.i + 1) % N;
      L[s] = L[s] * (1 - 0.5 * m) + yl * m; R[s] = R[s] * (1 - 0.5 * m) + yr * m;
    }
  }
}
class Phaser {
  constructor() { this.zl = new Float64Array(6); this.zr = new Float64Array(6); this.ph = 0; this.fl = 0; this.fr = 0; }
  run(L, R, n, prm) {
    const hz = 0.5 + 5.5 * prm.rate / 100, dep = prm.depth / 100, m = prm.mix / 100;
    for (let s = 0; s < n; s++) {
      this.ph += hz / SR; if (this.ph >= 1) this.ph -= 1;
      const sweep = 0.5 + 0.5 * sin1(this.ph), fc = 250 * Math.pow(12, sweep * dep), t = Math.tan(Math.PI * fc / SR), a = (t - 1) / (t + 1);
      let xl = L[s] + this.fl * 0.45, xr = R[s] + this.fr * 0.45;
      for (let k = 0; k < 6; k++) {
        const yl = a * xl + this.zl[k]; this.zl[k] = xl - a * yl; xl = yl;
        const yr = a * xr + this.zr[k]; this.zr[k] = xr - a * yr; xr = yr;
      }
      this.fl = xl; this.fr = xr;
      L[s] = L[s] * (1 - 0.5 * m) + xl * m; R[s] = R[s] * (1 - 0.5 * m) + xr * m;
    }
  }
}
const CRUSH_HZ = (i) => 300 * Math.pow(147, i / 100);
class Bitcrush {
  constructor() { this.acc = 0; this.hl = 0; this.hr = 0; }
  run(L, R, n, prm) {
    const step = 1 / Math.pow(2, prm.bits - 1), hz = CRUSH_HZ(prm.sr), r = Math.min(1, hz / SR), m = prm.mix / 100;
    for (let s = 0; s < n; s++) {
      this.acc += r;
      if (this.acc >= 1 || r >= 1) { this.acc -= Math.floor(this.acc); this.hl = Math.round(L[s] / step) * step; this.hr = Math.round(R[s] / step) * step; }
      L[s] = L[s] * (1 - m) + this.hl * m; R[s] = R[s] * (1 - m) + this.hr * m;
    }
  }
}
class FxFilter {
  constructor() { this.l = new SVF(); this.r = new SVF(); }
  run(L, R, n, prm) {
    const k = 2 - 1.9 * prm.res / 100;
    this.l.set(cutHz(prm.cutoff), k); this.r.set(cutHz(prm.cutoff), k);
    for (let s = 0; s < n; s++) { L[s] = this.l.run(L[s], prm.type); R[s] = this.r.run(R[s], prm.type); }
  }
}

// ------------------------------------------------------------------ the Note Engine
// ------------------------------------------------------------------ playing in a key (manual 6.5, 8.5)
// h = { key: 1..12 (C..B, 0 Off), scale, acc, voicing, chord, pattern }. A key of the scale plays the chord built on it
// from the scale's own notes (Harmonic Minor Practical: natural minor's chords, the harmonic one on V and vii). One
// outside it plays, Borrowed: the chord on it in the natural minor, else the major, of the same key, else a
// diminished one; Leading: the major chord it is the third of.
const SCALES = [[0, 2, 4, 5, 7, 9, 11], [0, 2, 3, 5, 7, 8, 10], [0, 2, 3, 5, 7, 8, 11], [0, 2, 3, 5, 7, 8, 11], [0, 2, 3, 5, 7, 9, 10],
  [0, 2, 4, 5, 7, 9, 10], [0, 1, 3, 5, 7, 8, 10], [0, 2, 4, 6, 7, 9, 11], [0, 2, 3, 5, 7, 9, 11]];
const LOCRIAN = [0, 1, 3, 5, 6, 8, 10];
const CHORD_STEPS = [[0, 2, 4], [0, 2, 4, 6], [0, 2, 4, 5], [0, 1, 4], [0, 3, 4], [0, 2, 4, 8], [0, 4]];   // Triad .. Power, in scale steps
const LEADING = [[0, 4, 7], [0, 4, 7, 10], [0, 4, 7, 9], [0, 4, 7], [0, 4, 7], [0, 4, 7, 14], [0, 4, 7]];  // above its root
const degNote = (sc, d) => sc[((d % 7) + 7) % 7] + 12 * Math.floor(d / 7);
const fold = (x) => { while (x > 127) x -= 12; while (x < 0) x += 12; return x; };
// the chord of key n: its notes in the Chord's order from the key's own note, and the same notes going up
function keyChord(n, h) {
  const t = h.key - 1, x = (((n - t) % 12) + 12) % 12, keys = SCALES[h.scale], steps = CHORD_STEPS[h.chord];
  const build = (sc, d) => steps.map((st) => degNote(sc, d + st) - degNote(sc, d));
  let rel, ro = 0;                                     // the chord above its root, and the root from the key
  const d = keys.indexOf(x);
  if (d >= 0) rel = build(h.scale === 2 && d !== 4 && d !== 6 ? SCALES[1] : keys, d);
  else if (h.acc === 1) { rel = LEADING[h.chord]; ro = -4; }
  else {
    const src = [SCALES[1], SCALES[0]].find((sc) => sc !== keys && sc.includes(x));
    rel = src ? build(src, src.indexOf(x)) : build(LOCRIAN, 0);
  }
  let v = rel.map((r) => { let y = ro + r; while (y < 0) y += 12; return y; });   // From Key: the key is the lowest note
  const k = v.indexOf(0);
  v = v.slice(k).concat(v.slice(0, k));
  let list = v.map((y) => n + y);
  if (h.voicing === 1) { const T = n - x; list = list.map((y) => T + ((((y - T) % 12) + 12) % 12)); }   // Close: within the tonic's octave
  list = list.map(fold);
  return { list, up: [...new Set(list)].sort((p, q) => p - q), t, keys };
}
// the order a chord's notes play in (Pattern); once: played once, then its last note held or repeated
const PATTERNS = ["Off", "Up", "Down", "Up Down", "Up 8", "Down 8", "Up Down 8", "Wide", "Alberti", "Pedal", "Octave", "Octave Down",
  "Two Octaves", "Bounce", "Gallop", "Plink", "Trill", "User"];
function keyRun(n, h) {
  const c = keyChord(n, h), s = c.up, N = s.length, lo = s[0], top = s[N - 1], down = s.slice().reverse(), i = (j) => s[Math.min(j, N - 1)];
  let seq, once = false;
  switch (h.pattern) {
    case 1: seq = s; break;
    case 2: seq = down; break;
    case 3: seq = s.concat(down.slice(1, -1)); break;
    case 4: seq = s.concat([lo + 12]); break;
    case 5: seq = [lo + 12].concat(down); break;
    case 6: seq = s.concat([lo + 12], down.slice(0, -1)); break;
    case 7: seq = s.concat(s.map((y) => y + 12), [lo + 24]); break;
    case 8: seq = [i(0), i(2), i(1), i(2)]; break;
    case 9: seq = []; for (let j = 1; j < Math.max(2, N); j++) seq.push(lo, i(j)); break;
    case 10: seq = [n, n + 12]; break;
    case 11: seq = [n, n - 12]; break;
    case 12: seq = [n, n + 12, n + 24]; break;
    case 13: seq = [n, n + 12, n, n - 12]; break;
    case 14: seq = [lo, lo, top]; break;                // Gallop: twice the low note, then the top
    case 15: seq = [n + 12, n]; once = true; break;     // Plink: the octave above once, then the key
    case 16: { let m = n + 1; while (!c.keys.includes((((m - c.t) % 12) + 12) % 12)) m++; seq = [n, m]; break; }   // Trill
    default: seq = [n];
  }
  return { seq: seq.map(fold), once };
}

const NE_RATE = [4, 2, 4 / 3, 1, 2 / 3, 1 / 2, 1 / 3, 1 / 4, 1 / 6, 1 / 8, 1 / 12];   // 1/1 .. 1/32T, in beats
class NoteEngine {
  constructor(eng) { this.eng = eng; this.held = []; this.latched = []; this.t = 0; this.step = 0; this.out = []; this.idx = 0; this.dir = 1; this.order = []; this.phase = 0;
    this.runs = new Map(); this.sounding = new Map(); this.cn = new Map(); }
  get s() { return this.eng.g.arp; }
  keys() { return [...new Set(this.s.latch ? this.latched : this.held)]; }   // a note held on the keys and on MIDI counts once
  keyOn(n, v) {
    const a = this.s;
    if (a.latch) {
      if (!this.held.length) { this.latched = []; if (a.ne === 2) for (const k of [...this.sounding.keys()]) this.chordOff(k); }   // a new chord
      if (!this.latched.includes(n)) this.latched.push(n);
    }
    this.held.push(n); this.vel = v;
    if (a.ne === 2) { if (!this.sounding.has(n)) this.chordOn(n, v); return; }
    if (this.keys().length === 1 && !this.running) { this.running = true; this.t = 0; this.step = 0; this.idx = 0; this.dir = 1; }
  }
  keyOff(n) {
    const i = this.held.indexOf(n);
    if (i >= 0) this.held.splice(i, 1);
    const a = this.s;
    if (a.ne === 2 && !a.latch && !this.held.includes(n)) this.chordOff(n);
    if (!this.keys().length) { this.running = false; this.stopOut(); }
  }
  // a key's chord: in the Key when one is set, else the Arpeggio's shape; at most four different notes together
  chord(n) {
    const a = this.s;
    if (a.key) return keyChord(n, a).list;
    const shape = a.arpeggio > 0 && a.arpeggio <= 31 ? ARPS[a.arpeggio] : [0];
    return [...new Set(shape.map((x) => fold(n + x)))].slice(0, 4);
  }
  run(n) {                                             // Auto-Arp: a key's run, as the settings are when it starts
    const a = this.s;
    if (a.key) return Object.assign(keyRun(n, a), { i: 0 });
    const shape = a.arpeggio > 0 && a.arpeggio <= 31 ? ARPS[a.arpeggio] : [0];
    return { seq: shape.map((x) => fold(n + x)), once: false, i: 0 };
  }
  // Auto-Chord: a note two keys share sounds once
  chordOn(n, v) {
    const notes = this.chord(n);
    this.sounding.set(n, notes);
    for (const x of notes) { const c = this.cn.get(x) || 0; if (!c) this.eng.own(x, v, x, true); this.cn.set(x, c + 1); }
  }
  chordOff(n) {
    const notes = this.sounding.get(n);
    if (!notes) return;
    this.sounding.delete(n);
    for (const x of notes) { const c = (this.cn.get(x) || 1) - 1; if (c > 0) this.cn.set(x, c); else { this.cn.delete(x); this.eng.own(x, 0, x, false); } }
  }
  refresh() {                                          // a setting changed: Auto-Chord's chords change at once
    if (this.s.ne !== 2) return;
    for (const n of [...this.sounding.keys()]) { const now = this.chord(n); if (now.join() !== this.sounding.get(n).join()) { this.chordOff(n); this.chordOn(n, this.vel || 100); } }
  }
  allOff() { this.held = []; this.latched = []; this.running = false; this.stopOut(); for (const n of [...this.sounding.keys()]) this.chordOff(n); this.runs.clear(); }
  stopOut() { for (const o of this.out) this.eng.own(o.n, 0, o.n, false); this.out = []; }
  sequence() {
    const a = this.s, k = this.keys().slice();
    if (a.ne === 1) return null;
    const asc = k.slice().sort((x, y) => x - y), base = a.mode === 5 ? k : asc;
    let seq = [];
    for (let o = 0; o < a.oct; o++) for (const x of base) seq.push(x + 12 * o);
    if (a.mode === 1) seq.reverse();
    else if (a.mode === 2 && seq.length > 1) seq = seq.concat(seq.slice().reverse());
    else if (a.mode === 3 && seq.length > 2) seq = seq.concat(seq.slice(1, -1).reverse());
    return seq;
  }
  tick(dt) {
    const a = this.s;
    if (!a.on || a.ne === 2) return;
    const now = this.t;
    for (const o of this.out.slice()) if (now >= o.off) { this.eng.own(o.n, 0, o.n, false); this.out.splice(this.out.indexOf(o), 1); }
    if (!this.running) { this.t += dt; return; }
    const len = NE_RATE[a.rate] * 60 / this.eng.tempo;
    const swing = (a.swing - 50) / 50 * len;
    const when = this.step * len + (this.step % 2 ? swing : 0);
    if (now >= when) {
      const gateLen = len * a.gate / 100;
      const play = (n) => { if (n < 0 || n > 127) return; this.eng.own(n, this.vel || 100, n, true); this.out.push({ n, off: now + gateLen }); };
      if (a.ne === 1) {                                 // Auto-Arp: each held key's chord, one note a step
        const ks = this.keys();
        for (const k of [...this.runs.keys()]) if (!ks.includes(k)) this.runs.delete(k);
        for (const k of ks) {
          let r = this.runs.get(k);
          if (!r || (r.i >= r.seq.length && !r.once)) { r = this.run(k); this.runs.set(k, r); }   // a new run takes new settings
          play(r.seq[Math.min(r.i, r.seq.length - 1)]); r.i++;   // Plink: after its run, its last note on every step
        }
      } else {
        const seq = this.sequence();
        if (seq.length) {
          if (a.mode === 6) for (const x of new Set(seq)) play(x);
          else if (a.mode === 4) play(seq[Math.floor(rnd() * seq.length)]);
          else play(seq[this.idx++ % seq.length]);
        }
      }
      this.step++;
    }
    this.t += dt;
  }
}

// ------------------------------------------------------------------ the engine
class Engine extends AudioWorkletProcessor {
  constructor() {
    super();
    this.p = null; this.clock = 0; this.tune = 0; this.lfoV = 0; this.beats = 0; this.lfoPh = 0; this.lfoSH = 0; this.lfoT = 0;
    this.g = { tempo: 120, velocity: 100, glideMode: 0, glideTime: 20, drive: 0, master: 0.7, sync: 0, clockOut: 0, local: 1, seqOut: 0,
               arp: { on: 0, ne: 0, mode: 0, oct: 1, rate: 7, gate: 50, swing: 50, latch: 0, midiIn: 1, arpeggio: 1 } };
    this.bend = 0; this.modP = 0; this.modA = 0;          // from MIDI: pitch bend in semitones, the controllers' depths 0..1
    this.ck = { last: -1, iv: [], tempo: 0 }; this.pulseT = 0;
    this.voices = []; for (let i = 0; i < 12; i++) this.voices.push(new FMVoice(this));
    this.vav = []; for (let i = 0; i < 12; i++) this.vav.push(new VAVoice(this));
    this.parts = []; for (let i = 0; i < 12; i++) this.parts.push(new PartVoice(this));
    this.drums = []; for (let i = 0; i < 12; i++) this.drums.push(new DrumVoice(this));
    this.sfx = []; for (let i = 0; i < 12; i++) this.sfx.push(new SfxVoice(this));
    this.fx = { filter: new FxFilter(), reverb: new Reverb(), delay: new Delay(), dist: new Distortion(), crush: new Bitcrush(), chorus: new Chorus(), phaser: new Phaser() };
    this.ne = new NoteEngine(this);
    this.mono = new Float32Array(BLK); this.L = new Float32Array(128); this.R = new Float32Array(128); this.b8 = new Float32Array(BLK);
    this.hp = 0; this.lp = 0; this.lim = 1; this.lastBass = null; this.down = new Map(); this.lit = ""; this.litT = 0;
    this.port.onmessage = (e) => this.msg(e.data);
  }
  msg(m) {
    if (m.t === "preset") {
      const old = this.p;
      this.p = m.p;
      if (m.same && old && old.engine === m.p.engine) for (const v of this.all()) if (v.active && v.p === old) v.p = m.p;
    } else if (m.t === "global") { Object.assign(this.g, m.g); if (!this.g.arp.on) this.ne.allOff(); else this.ne.refresh(); }
    else if (m.t === "key") this.key(m.n, m.on, m.v, m.src);
    else if (m.t === "seq") this.seqMsg(m);
    else if (m.t === "ctl") { this.bend = m.bend; this.modP = m.modP; this.modA = m.modA; }
    else if (m.t === "clock") this.clockIn();
    else if (m.t === "allOff") { this.ne.allOff(); for (const v of this.all()) if (v.active && v.gate) v.release(); this.down.clear(); }
  }
  all() { return [...this.voices, ...this.vav, ...this.parts, ...this.drums, ...this.sfx]; }
  // a key from the panel (src "p": a step's preview) or from MIDI (src "m"): through the Note Engine, or straight to the voices.
  // A MIDI note plays without being sent on, and skips the Note Engine with its MIDI In Off or with Local Control Off.
  key(n, on, v, src) {
    if (!this.p) return;
    const g = this.g, a = g.arp;
    if (a.on && (src !== "m" || (a.midiIn && g.local !== 0))) { if (on) this.ne.keyOn(n, v); else this.ne.keyOff(n); return; }
    if (src === "m") { if (on) this.voiceOn(n, v, n); else this.voiceOff(n, n); return; }
    this.own(n, v, n, on, src === "p");
  }
  // a note the FM-1 plays itself (its keys, the Note Engine, the Sequencer): sent over MIDI (manual 10.2.2), and
  // sounded unless Local Control is Off (the Sequencer: unless its Seq Output is Ext)
  own(n, v, key, on, seq) {
    const g = this.g;
    if (!seq || g.seqOut !== 1) this.port.postMessage({ t: "out", n, v, on, seq: !!seq });
    if (seq ? g.seqOut === 2 : g.local === 0) return;
    if (on) this.voiceOn(n, v, key); else this.voiceOff(n, key);
  }
  pmd(p) { return Math.min(1, p.lfo.pmd / 99 + this.modP); }   // the LFO's depths, deepened by the MIDI controllers
  amd(p) { return Math.min(1, p.lfo.amd / 99 + this.modA); }
  // ---------------------------------------------------------------- MIDI clock (manual 11.6, 11.7)
  // the tempo: the one measured from an incoming clock while Sync is On, else the FM-1's own
  get tempo() { return this.g.sync && this.ck.tempo ? this.ck.tempo : this.g.tempo; }
  following() { const c = this.ck; return !!this.g.sync && c.last >= 0 && currentTime - c.last < Math.max(0.1, 7.5 / this.tempo); }   // three pulses
  clockIn() {
    const c = this.ck, now = currentTime;
    if (c.last >= 0 && now - c.last < 0.25) {
      c.iv.push(now - c.last); if (c.iv.length > 24) c.iv.shift();
      const avg = c.iv.reduce((x, y) => x + y, 0) / c.iv.length;
      if (avg > 0) c.tempo = clamp(60 / (24 * avg), 20, 400);
    } else c.iv = [];
    c.last = now;
    if (this.g.sync) this.seqPulse();
  }
  sendRt(b) { if (this.g.clockOut && !this.following()) this.port.postMessage({ t: "rt", b }); }
  glideTime(p) {
    const mono = p.engine === "fm" ? p.fm.mono : p.engine === "va" ? p.va.mono : 0;
    if (!mono || this.g.glideTime <= 0) return 0;
    if (this.g.glideMode === 1 && !this.legato) return 0;
    return this.g.glideTime / 100;
  }
  pick(pool) {
    let best = null;
    for (const v of pool) if (!v.active) return v;
    for (const v of pool) if (!v.gate && (!best || v.age < best.age)) best = v;
    if (best) return best;
    for (const v of pool) if (!best || v.age < best.age) best = v;
    return best;
  }
  maxVoices(p) {
    if (p.engine === "va") return p.va.wave >= 2 ? 8 : 12;
    if (p.engine === "fm" && p.fm.filt.on) return p.fm.filt.type === 1 && p.fm.filt.res > 50 ? 9 : 10;
    return 12;
  }
  voiceOn(n, v, key) {
    const p = this.p;
    this.down.set(key, (this.down.get(key) || 0) + 1);
    if (p.lfo.sync) this.lfoPh = 0;
    if (p.engine === "b8") return this.on8(n, v, key);
    const pool = (p.engine === "fm" ? this.voices : this.vav).slice(0, this.maxVoices(p));
    const mono = p.engine === "fm" ? p.fm.mono : p.va.mono;
    if (mono) {
      const cur = pool.find((x) => x.active && x.gate && x.p.engine === p.engine);
      this.legato = !!cur;
      if (cur) { cur.key = key; cur.start(p, n, v, true); return; }
      for (const x of pool) if (x.active && x.gate) x.release();
      const vc = pool[0]; vc.key = key; vc.start(p, n, v, false); return;
    }
    const vc = this.pick(pool); vc.key = key; vc.start(p, n, v, false);
  }
  voiceOff(n, key) {
    const c = (this.down.get(key) || 1) - 1;
    if (c > 0) this.down.set(key, c); else this.down.delete(key);
    if (c > 0) return;
    for (const v of this.all()) if (v.active && v.gate && v.key === key) v.release();
  }
  // 8-Bit: the note decides the part
  on8(n, v, key) {
    const p = this.p, b = p.b8;
    if (n < B8.DRUM) return;
    if (n < B8.SFX) {
      const idx = n - B8.DRUM, d = b.drums[idx];
      if (d.choke) for (const x of this.drums) if (x.active && x.chokeG === d.choke && x.idx !== idx) x.choke = Math.min(x.choke, 0.999);
      const vc = this.drums[idx]; vc.start(p, idx, v); return;
    }
    if (n < B8.BASS) { this.sfx[n - B8.SFX].start(p, n - B8.SFX, v); return; }
    let which, note;
    if (n < B8.LEAD) { which = "bass"; note = n; this.lastBass = n; }
    else { which = "lead"; let m = n; while (m > B8.TOP) m -= 12; note = m - 12; }
    const part = b[which], base = note + 12 * part.oct;
    const shape = part.arp === 32 ? this.userArp(part) : part.arp ? ARPS[part.arp] : null;
    const pool = this.parts;
    if (part.mono) {
      const cur = pool.find((x) => x.active && x.gate && x.which === which);
      if (cur) { cur.key = key; cur.start(p, which, key, base, v, shape, true); return; }
      const vc = this.pick(pool); vc.start(p, which, key, base, v, shape, false); return;
    }
    if (part.ne === 1 && shape) {                       // Auto-Chord: the chord's notes together, at most four
      const notes = [...new Set(shape.map((x) => base + x))].slice(0, 4);
      for (const x of notes) { const vc = this.pick(pool); vc.start(p, which, key, x, v, null, false); }
      return;
    }
    const vc = this.pick(pool); vc.start(p, which, key, base, v, shape, false);
  }
  userArp(part) {
    const out = [];
    for (const s of part.user) { if (s > 18) break; out.push(s); }
    return out.length ? out : null;
  }
  beatStep(speed) { return Math.floor(this.beats / ARPSPEED[speed]); }
  // the LFO: one wave for the whole preset, held back per note by Delay
  lfoOut(v, dt) {
    const l = this.p ? v.p.lfo : null;
    v.lfoT += dt;
    if (!l) return { pitch: 0, amp: 0, raw: 0 };
    const dl = l.delay > 0 ? 0.03 * Math.pow(2, l.delay / 14) : 0, fade = dl > 0 ? clamp((v.lfoT - dl) / (dl * 0.5 + 0.05), 0, 1) : 1;
    return { pitch: this.lfoV * fade, amp: (this.lfoV * 0.5 + 0.5) * fade, raw: this.lfoV * fade };
  }
  lfoStep(dt) {
    if (!this.p) return;
    const l = this.p.lfo;
    this.lfoPh += lfoHz(l.speed) * dt;
    if (this.lfoPh >= 1) { this.lfoPh -= Math.floor(this.lfoPh); this.lfoSH = rnd() * 2 - 1; }
    const t = this.lfoPh;
    switch (l.wave) {
      case 0: this.lfoV = t < 0.5 ? 4 * t - 1 : 3 - 4 * t; break;
      case 1: this.lfoV = 1 - 2 * t; break;
      case 2: this.lfoV = 2 * t - 1; break;
      case 3: this.lfoV = t < 0.5 ? 1 : -1; break;
      case 4: this.lfoV = sin1(t); break;
      default: this.lfoV = this.lfoSH;
    }
  }
  // ---------------------------------------------------------------- the Sequencer's clock (manual 9)
  // Steps fire on the 32-sample control grid; each note is released after its length times the pattern's Gate.
  // A pattern changes at the end of its pass: to the one waiting, or along its Chain.
  seqMsg(m) {
    const s = this.sq || (this.sq = { playing: false, step: -1, t: 0, dur: 0, offs: [], pat: 0, next: null, bt: 0, beat: 0 });
    s.pats = m.pats; s.tr = m.tr; s.rec = m.rec; s.metro = m.metro; s.metroLvl = m.metroLvl; s.next = m.next;
    if (!s.playing) s.pat = m.pat;
    // a start (again from step 1 on a MIDI Start, or on from a step on a MIDI Continue); following a clock, step 1
    // waits for its next pulse
    if (m.playing && (!s.playing || m.restart)) {
      if (s.playing) this.seqAllOff();
      s.playing = true; s.step = (m.from || 0) - 1; s.t = 0; s.bt = 0; s.beat = 0; s.count = m.count ? 4 : -1; s.ct = 0;
      s.first = m.cont ? 0xfb : 0xfa; s.arm = this.following(); s.locked = s.arm; s.pc = 0; s.wait = 0;
    }
    else if (!m.playing && s.playing) { s.playing = false; this.seqAllOff(); this.sendRt(0xfc); }
  }
  seqAllOff() { const s = this.sq; for (const o of s.offs) this.own(o.n, 0, o.key, false, true); s.offs = []; }
  seqAdvance() {
    const s = this.sq;
    if (s.first) { this.sendRt(s.first); this.sendRt(0xf8); this.pulseT = 60 / (24 * this.tempo); s.first = 0; }   // Start, then step 1's pulse
    s.at = currentTime;
    let P = s.pats[s.pat];
    s.step++;
    if (s.step >= P.steps) {
      s.step = 0;
      s.pat = s.next !== null && s.next !== undefined ? s.next : P.chain >= 0 ? P.chain : s.pat;
      s.next = null;
      P = s.pats[s.pat];
    }
    const L = (NE_RATE[P.rate] * 60) / this.tempo, sw = (P.swing - 50) / 50;
    s.dur = L * (s.step % 2 === 0 ? 1 + sw : 1 - sw);
    if (!this.p) return;
    for (const x of P.notes[s.step]) {
      const n = clamp(x.n + s.tr, 0, 127), key = "q" + n;
      this.own(n, x.v, key, true, true);
      s.offs.push({ n, key, t: Math.max(0.008, L * (x.len - 1) + (L * P.gate) / 100) });
    }
    this.port.postMessage({ t: "pos", pat: s.pat, step: s.step, at: currentTime, dur: s.dur });
  }
  seqTick(dt) {
    const s = this.sq;
    if (!s || !s.playing || !s.pats) return;
    if (s.count >= 0) {                                  // the count-in: four clicks, then step 1 on the next beat
      s.ct -= dt;
      if (s.ct <= 0) {
        this.click = { t: 0, f: s.count === 4 ? 2000 : 1300, a: 0.5 * Math.max(30, s.metroLvl || 0) / 99 };
        s.count--; s.ct += 60 / this.tempo;
      }
      if (s.count > 0 || s.ct > 0) return;
      s.count = -1; s.t = 0; s.bt = 0; s.beat = 0;
    }
    for (let i = s.offs.length - 1; i >= 0; i--) { const o = s.offs[i]; o.t -= dt; if (o.t <= 0) { this.own(o.n, 0, o.key, false, true); s.offs.splice(i, 1); } }
    if (s.arm) return;                                   // step 1 waits for the clock's next pulse
    if (s.locked) {                                      // following a clock: the steps begin on its pulses (seqPulse)
      if (!this.following()) { s.locked = false; s.t = Math.max(0, s.at + s.dur - currentTime); }   // it stopped: on at its last tempo
      else if (s.wait > 0) { s.wait -= dt; if (s.wait <= 0) { s.wait = 0; this.seqAdvance(); } }    // a swung step, after its pulse
    }
    if (!s.locked) {
      s.t -= dt;
      while (s.t <= 0) { this.seqAdvance(); s.t += s.dur; if (this.following()) { s.locked = true; s.pc = 0; break; } }   // a clock again: locks from the next step
    }
    // the metronome, only while recording in real time: every beat, the bar's first higher
    s.bt -= dt;
    if (s.bt <= 0) {
      if (s.rec === "rt" && s.metro > 0) this.click = { t: 0, f: s.beat % 4 === 0 ? 2000 : 1300, a: 0.5 * s.metro / 99 };
      s.beat++; s.bt += 60 / this.tempo;
    }
  }
  seqPulse() {
    const s = this.sq;
    if (!s || !s.playing || !s.pats || s.count >= 0) return;
    if (s.arm) { s.arm = false; s.pc = 0; this.seqAdvance(); return; }
    if (!s.locked) return;
    const P = s.pats[s.pat];
    if (++s.pc < Math.round(NE_RATE[P.rate] * 24)) return;
    s.pc = 0;
    const sw = (P.swing - 50) / 50, next = s.step + 1;
    if (s.wait > 0) { s.wait = 0; this.seqAdvance(); }
    if (sw > 0 && next % 2 === 1 && next < P.steps) s.wait = (sw * NE_RATE[P.rate] * 60) / this.tempo;   // Swing moves the note, not the pulse
    else this.seqAdvance();
  }
  // Clock Out: 24 pulses a beat at the Tempo, Always or while the pattern plays, never while following a clock
  clockOutTick(dt) {
    const g = this.g, s = this.sq;
    if (!g.clockOut || this.following()) return;
    if (g.clockOut === 2 && !(s && s.playing && s.count < 0 && !s.first && !s.arm)) return;
    const iv = 60 / (24 * this.tempo);
    this.pulseT -= dt;
    if (this.pulseT <= 0) { this.port.postMessage({ t: "rt", b: 0xf8 }); this.pulseT = Math.max(this.pulseT + iv, 0); }
  }
  process(inputs, outputs) {
    const out = outputs[0], L = this.L, R = this.R, n = out[0].length;
    L.fill(0);
    const dt = BLK / SR, g = this.g;
    for (let off = 0; off < n; off += BLK) {
      const m = this.mono, b8 = this.b8;
      m.fill(0); b8.fill(0);
      this.beats += dt * this.tempo / 60;
      this.lfoStep(dt);
      this.ne.tick(dt);
      this.clockOutTick(dt);
      this.seqTick(dt);
      for (const v of this.voices) if (v.active) { v.control(this, dt); v.render(m, BLK); }
      for (const v of this.vav) if (v.active) { v.control(this, dt); v.render(m, BLK); }
      let any8 = false;
      for (const pool of [this.parts, this.drums, this.sfx]) for (const v of pool) if (v.active) { any8 = true; v.control(this, dt); v.render(b8, BLK); }
      const p = this.p;
      if (any8 || this.lim < 1) {
        const b = p && p.b8, smooth = b ? b.tone : 1;
        const hpA = Math.exp(-TAU * 90 / SR), lpA = 1 - Math.exp(-TAU * 14000 / SR);
        for (let s = 0; s < BLK; s++) {
          let x = b8[s];
          if (smooth) { this.lp += (x - this.lp) * lpA; const y = this.lp - this.hp; this.hp = this.lp - y * hpA; x = y; }
          const a = Math.abs(x) * this.lim;
          if (a > 0.89) this.lim = 0.89 / Math.abs(x); else this.lim = Math.min(1, this.lim + dt / BLK / 0.2);
          m[s] += x * this.lim * 1.8;
        }
      }
      // a factory preset carries a hidden trim in dB (its calibration), so presets sound equally loud at the same Level
      const lvl = p ? (p.engine === "b8" ? 1 : p.level / 99 * (p.engine === "fm" ? 0.55 : 1.3)) * (p.trim ? Math.pow(10, p.trim / 20) : 1) : 0;
      for (let s = 0; s < BLK; s++) L[off + s] = m[s] * lvl * 0.5;
    }
    R.set(L);
    // the seven effects, in the preset's order
    if (this.p) for (const id of this.p.fx.order) { const prm = this.p.fx[id]; if (prm.on) this.fx[id].run(L, R, n, prm); }
    const dg = (g.drive ? 0.5 : 1) * g.master;
    for (let s = 0; s < n; s++) {
      let l = L[s] * dg, r = R[s] * dg;
      if (this.click) {                                  // the click, after the effects
        const c = this.click, y = Math.sin(TAU * c.f * c.t) * c.a * Math.exp(-c.t / 0.012) * g.master;
        l += y; r += y; c.t += 1 / SR;
        if (c.t > 0.06) this.click = null;
      }
      if (l > 0.8 || l < -0.8) l = Math.sign(l) * (0.8 + 0.2 * Math.tanh((Math.abs(l) - 0.8) / 0.2));
      if (r > 0.8 || r < -0.8) r = Math.sign(r) * (0.8 + 0.2 * Math.tanh((Math.abs(r) - 0.8) / 0.2));
      out[0][s] = l; if (out[1]) out[1][s] = r;
    }
    // the keys' lights: every key whose note sounds, about thirty times a second
    this.litT += n;
    if (this.litT >= SR / 30) {
      this.litT = 0;
      const lit = [];
      for (const v of this.all()) if (v.active && (v.gate || v.kind === "drum" || v.kind === "sfx")) lit.push(v.key);
      const s = lit.sort((a, b) => a - b).join(",");
      if (s !== this.lit) { this.lit = s; this.port.postMessage({ t: "lit", keys: lit }); }
    }
    return true;
  }
}
registerProcessor("fm1va", Engine);
