// Le module sample : ses fonctions pures (bloc <script id="sample-lib"> de sample.html), sous Node.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import vm from "node:vm";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const file = join(ROOT, "sample.html");
const html = existsSync(file) ? readFileSync(file, "utf8") : "";
const m = html.match(/<script id="sample-lib">([\s\S]*?)<\/script>/);
const lib = m ? vm.runInNewContext(m[1] + "\n;({ TURN_SECONDS, MAX_SECONDS, BARS, fitBars, sliceBounds, encodeWav, makeClock, rollSeconds })") : {};
const plain = (x) => JSON.parse(JSON.stringify(x));   // objets du contexte vm vers ce contexte

test("le bloc sample-lib existe", () => assert.ok(m, "bloc <script id=\"sample-lib\"> absent"));

test("constantes", () => {
  assert.equal(lib.TURN_SECONDS, 1.8);
  assert.equal(lib.MAX_SECONDS, 16);
  assert.deepEqual(plain(lib.BARS), [1, 2, 4, 8]);
});

test("fitBars", () => {
  assert.deepEqual(plain(lib.fitBars(4, 120)), { bars: 2, rate: 1 });
  assert.equal(lib.fitBars(3.8, 120).bars, 2); assert.ok(Math.abs(lib.fitBars(3.8, 120).rate - 0.95) < 1e-9);
  assert.deepEqual(plain(lib.fitBars(16, 120)), { bars: 8, rate: 1 });
  assert.deepEqual(plain(lib.fitBars(0.05, 120)), { bars: null, rate: 1 });
});

test("sliceBounds", () => {
  const b = lib.sliceBounds(44100); assert.equal(b.length, 17); assert.equal(b[0], 0); assert.equal(b[16], 44100); assert.equal(b[8], 22050);
});

test("encodeWav", () => {
  const w = lib.encodeWav([Float32Array.of(1, -1, 0)], 44100), t = (o, n) => String.fromCharCode(...w.slice(o, o + n));
  assert.equal(t(0, 4), "RIFF"); assert.equal(t(8, 4), "WAVE"); assert.equal(w.length, 44 + 6);
  const d = new DataView(w.buffer); assert.equal(d.getUint32(24, true), 44100); assert.equal(d.getInt16(44, true), 32767); assert.equal(d.getInt16(46, true), -32768);
});

test("makeClock : tempo et phase à 64 mesures", () => {
  const c = lib.makeClock(), per = 60000 / (120 * 24);
  c.feed(0xfa, 0);
  let n = 0, t = 0;
  for (; n < 64 * 4 * 24; n++) { t = n * per + (n % 2 ? 2 : -2); c.feed(0xf8, t); }   // ±2 ms de gigue
  assert.ok(Math.abs(c.bpm - 120) < 0.5);
  assert.ok(Math.abs(c.beats(n * per) - 256) * 0.5 < 128 / 44100, "écart inférieur à 128 échantillons");
  c.feed(0xfc, t); assert.equal(c.running, false);
});

test("rollSeconds", () => assert.equal(lib.rollSeconds(120), 0.125));
