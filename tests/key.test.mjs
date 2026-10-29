// Jouer dans une tonalité (manuel 6.5) : les accords et les Patterns du worklet, sur les exemples du manuel.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import vm from "node:vm";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const src = readFileSync(join(ROOT, "engine.js"), "utf8");
const ctx = { sampleRate: 44100, currentTime: 0, AudioWorkletProcessor: class {}, registerProcessor: () => {} };
const { keyChord, keyRun } = vm.runInNewContext(src + "\n;({ keyChord, keyRun })", ctx);
const plain = (x) => JSON.parse(JSON.stringify(x));
const NN = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
const names = (ns) => ns.map((n) => NN[n % 12]).join(" ");
const C = (o = {}) => Object.assign({ key: 1, scale: 0, acc: 0, voicing: 0, chord: 0, pattern: 1 }, o);
const chord = (n, o) => names(plain(keyChord(n, C(o)).list));
const run = (n, o) => plain(keyRun(n, C(o)).seq);

test("Do majeur : l'accord de chaque touche", () => {
  assert.equal(chord(62), "D F A");
  assert.equal(chord(67), "G B D");
  assert.equal(chord(67, { chord: 1 }), "G B D F");                    // Seventh sur Sol : la gamme décide
  assert.equal(chord(60, { chord: 5 }), "C E G D");                    // Add 9
  assert.deepEqual(plain(keyChord(60, C({ chord: 5 })).list), [60, 64, 67, 74]);
  assert.equal(chord(67, { chord: 6 }), "G D");                        // Power
});

test("Close : dans l'octave de la tonique", () => {
  assert.deepEqual(plain(keyChord(60, C({ voicing: 1 })).up), [60, 64, 67]);
  assert.deepEqual(plain(keyChord(65, C({ voicing: 1 })).up), [60, 65, 69]);
  assert.deepEqual(plain(keyChord(67, C({ voicing: 1 })).up), [62, 67, 71]);
});

test("Accidentals", () => {
  assert.equal(chord(68), "G# C D#");                                  // La bémol majeur
  assert.equal(chord(70), "A# D F");
  assert.equal(chord(66), "F# A C");                                   // diminué sur une note haussée
  assert.equal(chord(61), "C# E G");                                   // de passage, un demi-ton au-dessus de la tonique
  assert.equal(chord(61, { acc: 1 }), "C# E A");                       // Leading
  assert.equal(chord(68, { acc: 1 }), "G# B E");
});

test("mineures", () => {
  const am = { key: 10, scale: 2 };                                    // La mineur harmonique pratique
  assert.equal(chord(64, am), "E G# B");                               // majeur sur la quinte
  assert.equal(chord(68, am), "G# B D");                               // diminué sur la septième haussée
  assert.equal(chord(60, am), "C E G");                                // les autres : la mineure naturelle
  assert.equal(chord(60, { key: 10, scale: 3 }), "C E G#");            // stricte : augmenté
});

test("Patterns", () => {
  assert.deepEqual(run(60, { pattern: 1 }), [60, 64, 67]);
  assert.deepEqual(run(60, { pattern: 2 }), [67, 64, 60]);
  assert.deepEqual(run(60, { pattern: 3 }), [60, 64, 67, 64]);
  assert.deepEqual(run(60, { pattern: 4 }), [60, 64, 67, 72]);
  assert.deepEqual(run(60, { pattern: 7 }), [60, 64, 67, 72, 76, 79, 84]);
  assert.deepEqual(run(60, { pattern: 8 }), [60, 67, 64, 67]);          // Alberti 1 3 2 3
  assert.deepEqual(run(60, { pattern: 9 }), [60, 64, 60, 67]);          // Pedal 1 2 1 3
  assert.deepEqual(run(60, { pattern: 16 }), [60, 62]);                 // Trill
  assert.deepEqual(plain(keyRun(60, C({ pattern: 15 }))), { seq: [72, 60], once: true });   // Plink
  assert.deepEqual(run(60, { pattern: 0 }), [60]);
  assert.deepEqual(run(124, { pattern: 4 }), [119, 124, 127, 119]);     // Mi Sol Si : au-dessus de 127, une octave plus bas
});
