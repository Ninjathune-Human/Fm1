// L'app iPad : ios/midi.js, le Web MIDI que l'app donne à la page avec le MIDI de l'iPad (entrées seulement).
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import vm from "node:vm";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const src = readFileSync(join(ROOT, "ios/midi.js"), "utf8");

// une page (ou un cadre) de l'app : l'app répond à « ouvrir » par la liste des appareils branchés
function page(list = [["7", "KeyStep 37"]], frames = []) {
  const asked = [];
  const w = { navigator: {}, EventTarget, Event, frames, webkit: { messageHandlers: { fm1midi: { postMessage: (m) => { asked.push(m); return Promise.resolve(list); } } } } };
  w.window = w;
  vm.runInNewContext(src, w);
  return Object.assign(w, { asked });
}
const heard = (input) => { const got = []; input.onmidimessage = (m) => got.push([...m.data]); return got; };

test("sans l'app (pas de messageHandlers), la page reste sans Web MIDI", () => {
  const w = { navigator: {}, EventTarget, Event, frames: [] };
  w.window = w;
  vm.runInNewContext(src, w);
  assert.equal(w.navigator.requestMIDIAccess, undefined);
});

test("requestMIDIAccess : les appareils de l'iPad en entrées, aucune sortie, une seule demande à l'app", async () => {
  const w = page([["7", "KeyStep 37"], ["-12", "Network Session 1"]]);
  const a = await w.navigator.requestMIDIAccess({ sysex: true });
  assert.equal(await w.navigator.requestMIDIAccess(), a);
  assert.deepEqual(w.asked, ["ouvrir"]);
  assert.deepEqual([...a.inputs.values()].map((i) => [i.id, i.name, i.state, i.type]), [["7", "KeyStep 37", "connected", "input"], ["-12", "Network Session 1", "connected", "input"]]);
  assert.equal(a.outputs.size, 0);
  assert.equal(a.sysexEnabled, true);
});

test("les octets découpés en messages : statut courant, paquets coupés, horloge au milieu, SysEx en plusieurs fois", async () => {
  const w = page();
  const a = await w.navigator.requestMIDIAccess();
  const got = heard(a.inputs.get("7"));
  w.__fm1midi.rx("7", [0x90, 60, 100, 62, 90]);                    // deux notes, la seconde en statut courant
  w.__fm1midi.rx("7", [0xb0, 1]);                                   // un CC coupé entre deux paquets
  w.__fm1midi.rx("7", [0xf8, 64]);                                  // l'horloge passe avant la fin du CC
  w.__fm1midi.rx("7", [0xc0, 5, 0xe0, 0, 64, 0xfe]);                // programme (2 octets), pitch bend, Active Sensing
  w.__fm1midi.rx("7", [0xf0, 0x43, 0x00]);                          // un SysEx sur deux paquets, l'horloge au milieu
  w.__fm1midi.rx("7", [0xf8, 0x09, 0xf7, 0x80, 60, 0]);
  w.__fm1midi.rx("7", [12, 0xf2, 1, 2, 3]);                          // un octet de données perdu ; position (pas de statut courant après)
  assert.deepEqual(got, [[0x90, 60, 100], [0x90, 62, 90], [0xf8], [0xb0, 1, 64], [0xc0, 5], [0xe0, 0, 64], [0xfe],
    [0xf8], [0xf0, 0x43, 0x00, 0x09, 0xf7], [0x80, 60, 0], [0xf2, 1, 2]]);
});

test("avant requestMIDIAccess, rien n'arrive ; un appareil inconnu non plus", async () => {
  const w = page();
  w.__fm1midi.rx("7", [0x90, 60, 100]);
  const a = await w.navigator.requestMIDIAccess();
  const got = heard(a.inputs.get("7"));
  w.__fm1midi.rx("99", [0x90, 61, 100]);
  w.__fm1midi.rx("7", [0x90, 62, 100]);
  assert.deepEqual(got, [[0x90, 62, 100]]);
});

test("un clavier débranché puis rebranché : statechange avec son port, il reste dans la liste", async () => {
  const w = page();
  const a = await w.navigator.requestMIDIAccess();
  const seen = [];
  a.onstatechange = (e) => seen.push([e.port.name, e.port.state]);
  w.__fm1midi.ports([]);
  assert.equal(a.inputs.get("7").state, "disconnected");
  w.__fm1midi.ports([["7", "KeyStep 37"], ["8", "Arturia"]]);
  w.__fm1midi.ports([["7", "KeyStep 37"], ["8", "Arturia"]]);           // rien de neuf : rien
  assert.deepEqual(seen, [["KeyStep 37", "disconnected"], ["KeyStep 37", "connected"], ["Arturia", "connected"]]);
  assert.equal(a.inputs.size, 2);
});

test("Duo : la page principale passe les octets et les appareils à ses cadres", async () => {
  const fa = page(), fb = page();
  const top = page([["7", "KeyStep 37"]], [fa, fb]);
  const ga = heard((await fa.navigator.requestMIDIAccess()).inputs.get("7"));
  const gb = heard((await fb.navigator.requestMIDIAccess()).inputs.get("7"));
  top.__fm1midi.rx("7", [0x90, 60, 100]);
  top.__fm1midi.ports([]);
  assert.deepEqual([ga, gb], [[[0x90, 60, 100]], [[0x90, 60, 100]]]);
  assert.equal((await fb.navigator.requestMIDIAccess()).inputs.get("7").state, "disconnected");
});
