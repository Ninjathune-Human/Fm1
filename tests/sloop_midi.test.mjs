// SLOOP : un fichier MIDI dans une piste (bloc fm1-lib d'index.html, repris de l'éditeur de SLOOP) : lecture, mise en pas,
// trames du protocole de l'éditeur.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import vm from "node:vm";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const html = readFileSync(join(ROOT, "index.html"), "utf8");
const m = html.match(/<script id="fm1-lib">([\s\S]*?)<\/script>/);
const S = vm.runInNewContext(m[1] + "\n;SLOOP");
const plain = (x) => JSON.parse(JSON.stringify(x));

// un fichier MIDI de format 1 : une piste de tempo, puis des pistes de notes [t, durée, note, vélocité, canal]
const vlq = (n) => { const a = [n & 0x7F]; while ((n >>= 7)) a.unshift(0x80 | (n & 0x7F)); return a; };
const u32 = (n) => [(n >>> 24) & 255, (n >> 16) & 255, (n >> 8) & 255, n & 255];
function smfFile(ppq, bpm, tracks) {
  const chunk = (body) => [0x4D, 0x54, 0x72, 0x6B, ...u32(body.length), ...body];
  const us = Math.round(60000000 / bpm);
  const out = [0x4D, 0x54, 0x68, 0x64, ...u32(6), 0, 1, 0, tracks.length + 1, ppq >> 8, ppq & 255,
    ...chunk([0, 0xFF, 0x51, 3, (us >> 16) & 255, (us >> 8) & 255, us & 255, 0, 0xFF, 0x2F, 0])];
  for (const { name, notes } of tracks) {
    const ev = [];
    for (const [t, dur, key, vel, ch = 0] of notes) { ev.push([t, 1, [0x90 | ch, key, vel]]); ev.push([t + dur, 0, [0x80 | ch, key, 0]]); }
    ev.sort((a, b) => a[0] - b[0] || a[1] - b[1]);
    const nm = [...name].map((c) => c.charCodeAt(0));
    const body = [0, 0xFF, 0x03, nm.length, ...nm];
    let last = 0;
    for (const [t, , b] of ev) { body.push(...vlq(t - last), ...b); last = t; }
    body.push(0, 0xFF, 0x2F, 0);
    out.push(...chunk(body));
  }
  return Uint8Array.from(out);
}

const PPQ = 96, Q = PPQ, S16 = PPQ / 4;   // une noire ; une double croche, un pas à DIV 2 (16 par mesure)

test("lecture : pistes, noms, tempo, notes et durées", () => {
  const f = S.readSmf(smfFile(PPQ, 97, [{ name: "Lead", notes: [[0, Q, 60, 100], [Q, Q, 64, 90], [2 * Q, 2 * Q, 67, 80]] }]));
  assert.equal(f.format, 1);
  assert.equal(f.ppq, 96);
  assert.equal(f.bpm, 97);
  assert.equal(f.tracks.length, 2);
  assert.deepEqual(plain(f.tracks[0].notes), []);
  assert.equal(f.tracks[1].name, "Lead");
  assert.deepEqual(plain(f.tracks[1].notes), [{ t: 0, dur: 96, key: 60, vel: 100, ch: 0 }, { t: 96, dur: 96, key: 64, vel: 90, ch: 0 },
    { t: 192, dur: 192, key: 67, vel: 80, ch: 0 }]);
});

test("lecture : un fichier qui n'est pas du MIDI est refusé", () => {
  assert.throws(() => S.readSmf(Uint8Array.from([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14])), /pas un fichier MIDI/);
});

test("mise en pas : notes, liaisons, accords, longueur", () => {
  const notes = S.readSmf(smfFile(PPQ, 120, [{ name: "", notes: [[0, S16, 60, 100], [S16, 3 * S16, 62, 90],
    [4 * S16, S16, 64, 70], [4 * S16, S16, 67, 110]] }])).tracks[1].notes;
  const p = S.toSteps(notes, PPQ, 2, 64);
  assert.equal(p.len, 5);
  assert.deepEqual(plain(p.report), { notes: 4, steps: 5, moved: 0, chordCut: 0, overlap: 0, dropped: 0, merged: 0 });
  assert.deepEqual(plain(p.steps[0]), { n: 1, notes: [60, 0, 0, 0], time: 0, flags: 0, vel: 100, lvl: 0, rat: 0 });
  assert.equal(p.steps[1].notes[0], 62);
  assert.equal(p.steps[2].time, 1);                 // la note de trois pas : deux liaisons
  assert.equal(p.steps[3].time, 1);
  assert.deepEqual(plain(p.steps[4]), { n: 2, notes: [64, 67, 0, 0], time: 0, flags: 0, vel: 110, lvl: 0, rat: 0 });
  assert.equal(p.steps[5].time, 2);                 // le reste : des silences
  assert.equal(p.steps.length, 64);
});

test("mise en pas : ce qui change en route est compté", () => {
  const n = (t, key, vel = 100, dur = S16) => ({ t, dur, key, vel, ch: 0 });
  const five = [60, 62, 64, 65, 67].map((k, i) => n(0, k, 60 + i));
  const p = S.toSteps([...five, n(S16 + 10, 70), n(2 * S16, 72, 100, 4 * S16), n(3 * S16, 74), n(3 * S16, 74), n(64 * S16, 76)], PPQ, 2, 64);
  assert.equal(p.report.chordCut, 1);               // cinq notes : la plus douce tombe
  assert.deepEqual(plain(p.steps[0].notes), [62, 64, 65, 67]);
  assert.equal(p.report.moved, 1);                  // 10 ticks après le pas (plus d'un quart de pas)
  assert.equal(p.report.overlap, 1);                // la note longue s'arrête au pas suivant
  assert.equal(p.report.merged, 1);                 // la même note deux fois sur un pas
  assert.equal(p.report.dropped, 1);                // après le pas 64
});

test("mise en pas : la batterie, sur ses 16 voix", () => {
  const n = (t, key, vel) => ({ t, dur: 6, key, vel, ch: 9 });
  const p = S.toSteps([n(0, 36, 100), n(0, 42, 40), n(S16, 38, 120), n(S16, 40, 70)], PPQ, 2, 64, true);
  assert.equal(p.len, 2);
  assert.equal(p.dsteps[0].on, (1 << 0) | (1 << 4));            // KICK, HAT
  assert.equal(p.dsteps[0].lvl[4], 1);                           // GHOST
  assert.equal(p.dsteps[1].on, (1 << 2) | (1 << 8));            // SNARE, SNARE 2
  assert.equal(p.dsteps[1].lvl[2], 3);                           // HARD
  assert.equal(p.dsteps[1].lvl[8], 2);                           // SOFT
});

test("trames : en-tête, aller-retour, octets de données", () => {
  const f = S.frame(S.CMD.TRACK_STEP, [0, 3, 1]);
  assert.deepEqual(plain(f), [0xF0, 0x7D, 0x46, 0x4C, 30, 0, 3, 1, 0xF7]);
  assert.deepEqual(plain(S.unframe(Uint8Array.from(f))), { cmd: 30, a: [0, 3, 1] });
  assert.equal(S.unframe(Uint8Array.from([0xF0, 0x43, 0, 0, 1, 0xF7])), null);
  assert.throws(() => S.frame(1, [128]), /invalide/);
});

test("trames : un pas de piste, un pas de batterie, une valeur", () => {
  assert.deepEqual(plain(S.stepArgs(1, 5, { n: 2, notes: [60, 64, 0, 0], time: 0, flags: 0, vel: 100, lvl: 0, rat: 0 })),
    [1, 5, 2, 60, 64, 0, 0, 0, 0, 100, 0, 0, 0]);
  const d = S.emptyDrum(); d.on = (1 << 0) | (1 << 9); d.lvl[9] = 3;
  // on : 0x201 en 3 groupes de 7 bits ; lvl : 3 x 4^9 = 3 x 2^18 en 5 groupes ; rat : rien
  assert.deepEqual(plain(S.drumArgs(7, d)), [7, 0x01, 0x04, 0, 0, 0, 48, 0, 0, 0, 0, 0, 0, 0]);
  assert.deepEqual(plain(S.v14(16)), [16, 64]);    // 16 + 8192, poids faible d'abord
});

test("réponses : INFO et DESC", () => {
  const str = (s) => [...s].map((c) => c.charCodeAt(0)).concat(0);
  const info = S.info([...str("2.8.5"), 2, 60, 40, 64, 52, ...str("ANALOG"), ...str("FM"), 4, 9]);
  assert.deepEqual(plain(info), { version: "2.8.5", nengines: 2, pcount: 60, gcount: 40, nstep: 64, pe0: 52, engines: ["ANALOG", "FM"], ntrk: 4, proto: 9 });
  const v = (x) => plain(S.v14(x));
  const d = S.desc([0, 30, 8, ...v(0), ...v(2), ...v(2), ...str("DIV"), ...str(""), ...str("1/4"), ...str("1/8"), ...str("1/16")]);
  assert.equal(d.label, "DIV");
  assert.deepEqual(plain(d.names), ["1/4", "1/8", "1/16"]);
});
