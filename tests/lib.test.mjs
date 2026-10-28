import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import vm from "node:vm";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const html = readFileSync(join(ROOT, "index.html"), "utf8");
const m = html.match(/<script id="fm1-lib">([\s\S]*?)<\/script>/);
const lib = m ? vm.runInNewContext(m[1] + "\n;({ KEY_IDS, noteId, ENC_IDS, potAfter, rgb565ToRgba, LIT, isLit, CATEGORY_ORDER, HIDDEN, groupCatalogue, rankCatalogue })") : {};
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

test("optimisés d'abord, non optimisés à la fin", () => {
  const natifs = new Set(["felucca", "x0x", "ghoulbox"]);
  const entries = cat.map((e) => (natifs.has(e.id) ? { ...e, natif: "natif/" + e.id + "/" } : e));
  const g = plain(lib.groupCatalogue(entries));
  const k = g.findIndex((s) => !s.optimise);
  assert.ok(k > 0, "deux groupes attendus");
  assert.ok(g.slice(0, k).every((s) => s.optimise && s.items.every((e) => natifs.has(e.id))));
  assert.ok(g.slice(k).every((s) => !s.optimise && s.items.every((e) => !natifs.has(e.id))));
  assert.equal(g.slice(0, k).reduce((n, s) => n + s.items.length, 0), 3);
  assert.equal(new Set(g.map((s) => s.cle)).size, g.length);
  const va = plain(lib.groupCatalogue([{ id: "fm1va", nom: "FM-1+VA", categories: ["FM-1+VA"] }, ...entries]));
  assert.ok(va[0].optimise && va[0].items[0].id === "fm1va");
});

const firstIds = (q) => plain(lib.rankCatalogue(cat, q)).items.slice(0, 3).map((e) => e.id);

test("recherche : mots dans n'importe quel ordre, mots vides et casse ignorés", () => {
  assert.equal(firstIds("machine FART")[0], "fart");
  assert.equal(firstIds("le chipbox")[0], "chipbox");
});

test("recherche : début de mot et fautes de frappe", () => {
  assert.equal(firstIds("chipb")[0], "chipbox");
  assert.equal(firstIds("slopo")[0], "sloop");
  assert.equal(firstIds("kalimab")[0], "fimba");
});

test("recherche : accents ignorés", () => {
  const r = plain(lib.rankCatalogue([{ id: "a", nom: "Été", auteur: "", description: "" }, { id: "b", nom: "Hiver", auteur: "", description: "" }], "ete"));
  assert.deepEqual(r.items.map((e) => e.id), ["a"]);
});

test("recherche : résultats approchants quand aucun élément n'a tous les mots", () => {
  const r = plain(lib.rankCatalogue(cat, "sloop zzzzqq"));
  assert.equal(r.approchants, true);
  assert.ok(r.items.some((e) => e.id === "sloop"));
  assert.equal(plain(lib.rankCatalogue(cat, "sloop")).approchants, false);
});

test("recherche : vide, mots vides seuls, élément masqué", () => {
  assert.deepEqual(plain(lib.rankCatalogue(cat, "")), { items: [], approchants: false });
  assert.deepEqual(plain(lib.rankCatalogue(cat, "le de la")), { items: [], approchants: false });
  assert.ok(!plain(lib.rankCatalogue(cat, "bubba machine")).items.some((e) => e.id === "bubba"));
});
