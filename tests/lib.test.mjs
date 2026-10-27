import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import vm from "node:vm";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const html = readFileSync(join(ROOT, "index.html"), "utf8");
const m = html.match(/<script id="fm1-lib">([\s\S]*?)<\/script>/);
const lib = m ? vm.runInNewContext(m[1] + "\n;({ KEY_IDS, noteId, ENC_IDS, potAfter, rgb565ToRgba, LIT, isLit, CATEGORY_ORDER, HIDDEN, groupCatalogue })") : {};
const cat = JSON.parse(readFileSync(join(ROOT, "firmwares/catalogue.json"), "utf8")).firmwares;
const plain = (x) => JSON.parse(JSON.stringify(x));   // objets du contexte vm vers ce contexte
const fold = (s) => String(s || "").normalize("NFD").replace(/\p{M}/gu, "").toLowerCase();

test("le bloc fm1-lib existe", () => assert.ok(m, "bloc <script id=\"fm1-lib\"> absent"));

test("touches et encodeurs", () => {
  assert.equal(lib.KEY_IDS.SEL, 3);
  assert.equal(lib.KEY_IDS["OCT-"], 0);
  assert.equal(lib.KEY_IDS.REC, 13);
  assert.equal(lib.noteId(0), 14);
  assert.equal(lib.noteId(26), 40);
  assert.equal(lib.noteId(27), -1);
  assert.equal(lib.noteId(-1), -1);
  assert.equal(lib.ENC_IDS.PRESETS, 6);
  assert.equal(lib.ENC_IDS.KNOB4, 5);
});

test("volume borné", () => {
  assert.equal(lib.potAfter(1020, 2), 1023);
  assert.equal(lib.potAfter(4, -1), 0);
  assert.equal(lib.potAfter(900, 1), 908);
});

test("conversion RGB565 vers RGBA", () => {
  const src = new Uint16Array([0xf800, 0x07e0, 0x001f, 0x0000, 0xffff]);
  const dst = new Uint8ClampedArray(src.length * 4);
  lib.rgb565ToRgba(src, dst);
  assert.deepEqual([...dst], [255, 0, 0, 255, 0, 255, 0, 255, 0, 0, 255, 255, 0, 0, 0, 255, 255, 255, 255, 255]);
});

test("voyants", () => {
  const leds = new Float32Array(41);
  leds[12] = 0.3; leds[13] = 0.2;
  assert.equal(lib.isLit(leds, 12), true);
  assert.equal(lib.isLit(leds, 13), false);
});

test("catalogue groupé sans recherche", () => {
  const g = plain(lib.groupCatalogue(cat, ""));
  assert.equal(g[0].categorie, "Officiel");
  assert.ok(!g.some((s) => s.items.some((e) => e.id === "bubba")));
  assert.ok(g.every((s) => plain(lib.CATEGORY_ORDER).includes(s.categorie) && s.items.length > 0));
  assert.equal(g.reduce((n, s) => n + s.items.length, 0), cat.length - 1);
  const autre = g.find((s) => s.categorie === "Autre").items.map((e) => e.id);
  assert.ok(autre.includes("dinghy"));
  for (const s of g) {
    const noms = s.items.map((e) => e.nom);
    assert.deepEqual(noms, [...noms].sort((a, b) => a.localeCompare(b, "fr", { sensitivity: "base" })));
  }
});

test("recherche sans accents ni casse", () => {
  const items = plain(lib.groupCatalogue(cat, "SYNTHÉ")).flatMap((s) => s.items);
  assert.ok(items.length > 0);
  for (const e of items) assert.ok([e.nom, e.auteur, e.description].some((t) => fold(t).includes("synthe")), e.id);
  assert.deepEqual(plain(lib.groupCatalogue(cat, "zzz")), []);
});
