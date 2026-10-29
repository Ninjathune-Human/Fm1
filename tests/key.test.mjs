// Jouer dans une tonalité (manuel 6.5) : les accords et les Patterns du worklet, sur les exemples du manuel.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import vm from "node:vm";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const src = readFileSync(join(ROOT, "engine.js"), "utf8");
const ctx = { sampleRate: 44100, currentTime: 0, AudioWorkletProcessor: class { constructor() { this.port = { postMessage() {} }; } } };
ctx.registerProcessor = (name, cls) => { ctx.Engine = cls; };
const { keyChord, keyRun, followChord } = vm.runInNewContext(src + "\n;({ keyChord, keyRun, followChord })", ctx);
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

// une partie 8-Bit : Key du preset, Chord et Pattern de la partie
const part = (o = {}) => Object.assign({ arp: 0, ne: 0, chord: 0, pattern: 1, user: [19, 19, 19, 19, 19, 19, 19, 19], mono: 0 }, o);
const b8 = (o = {}) => Object.assign({ key: 1, scale: 0, acc: 0, voicing: 0, follow: 0, bass: part(), lead: part() }, o);

test("8-Bit : l'accord et la course d'une partie", () => {
  const e = new ctx.Engine();
  assert.deepEqual(plain(e.partChord(b8(), "bass", 50)), { run: [0, 3, 7], chord: [0, 3, 7] });   // Ré : Ré Fa La
  assert.equal(e.partChord(b8({ bass: part({ pattern: 0 }) }), "bass", 50).run, null);           // Off : la touche seule
  const p = e.partChord(b8({ bass: part({ pattern: 15 }) }), "bass", 50).run;
  assert.deepEqual([plain(p), p.once], [[12, 0], true]);                                           // Plink
  // User : les pas par leur rôle, 0 4 7 12 sur Ré mineur
  assert.deepEqual(plain(e.partChord(b8({ bass: part({ pattern: 17, user: [0, 4, 7, 12, 19, 19, 19, 19] }) }), "bass", 50).run), [0, 3, 7, 12]);
  assert.deepEqual(plain(e.partChord(b8({ key: 0, bass: part({ arp: 1 }) }), "bass", 50).run), [0, 4, 7]);   // sans Key : l'Arpeggio
});

test("Lead Follows Bass", () => {
  const C = keyChord(48, { key: 1, scale: 0, acc: 0, voicing: 0, chord: 0 }), G = keyChord(55, { key: 1, scale: 0, acc: 0, voicing: 0, chord: 0 });
  assert.equal(names(plain(followChord(64, C).list)), "E G C");
  assert.equal(names(plain(followChord(62, C).list)), "D E G");
  assert.equal(names(plain(followChord(60, G).list)), "C D G");
  const e = new ctx.Engine();
  e.lastBass = 55;
  assert.deepEqual(plain(e.partChord(b8({ follow: 1 }), "lead", 60).chord), [0, 2, 7]);
  e.lastBass = null;                                                                                // pas encore de basse : ses propres accords
  assert.deepEqual(plain(e.partChord(b8({ follow: 1 }), "lead", 60).chord), [0, 4, 7]);
});

test("8-Bit : pas d'accord du Note Engine sur la batterie ni sur une partie qui a le sien", () => {
  const e = new ctx.Engine();
  e.p = { engine: "b8", b8: b8({ key: 0, bass: part({ arp: 0 }), lead: part({ arp: 1 }) }) };
  e.g.arp = Object.assign(e.g.arp, { ne: 2, key: 1, scale: 0, acc: 0, voicing: 0, chord: 0 });
  assert.deepEqual(plain(e.ne.chord(20)), [20]);                                                    // une batterie
  assert.deepEqual(plain(e.ne.chord(86)), [86]);                                                    // le lead joue son Arpeggio
  assert.deepEqual(plain(e.ne.chord(74)), [74, 65, 69]);                                            // Ré Fa La, gardé dans la basse
});

test("les verrous d'un pas dans le worklet", () => {
  const e = new ctx.Engine(), base = { engine: "va", fx: { reverb: { mix: 20 } }, va: { filt: { cutoff: 50 } } };
  e.p = e.base = base;
  e.seqLocks([{ eng: "fx", sets: [["fx.reverb.mix", 77]] }, { eng: "va", sets: [["va.filt.cutoff", 99]] }, { eng: "fm", sets: [["fx.reverb.mix", 5]] }]);
  assert.equal(e.p.fx.reverb.mix, 77);
  assert.equal(e.p.va.filt.cutoff, 99);
  assert.equal(base.fx.reverb.mix, 20);                                 // le preset lui-même ne change pas
  e.seqLocks([]);
  assert.equal(e.p, base);                                              // un pas sans verrou : les valeurs du preset
});
