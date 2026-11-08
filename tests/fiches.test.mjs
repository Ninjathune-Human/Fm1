// Les fiches de firmware de l'aide : format, liste fermée des commandes, lien avec le catalogue.
import { test } from "node:test";
import assert from "node:assert/strict";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const DIR = join(ROOT, "firmwares/fiches");
const cat = JSON.parse(readFileSync(join(ROOT, "firmwares/catalogue.json"), "utf8")).firmwares;
const files = existsSync(DIR) ? readdirSync(DIR).filter((f) => f.endsWith(".json")) : [];

const ORDER = ["OCT-", "OCT+", "FX", "SEL", "ENV", "LFO", "EDIT", "GLO", "HOME", "SAVE", "ARP", "SEQ", "PLAY", "REC",
  "MASTER", "SELECT", "PRESETS", "ALGORITHM", "Touches", "Touches blanches", "Touches noires"];

test("des fiches existent", () => assert.ok(files.length > 0, "firmwares/fiches vide ou absent"));

test("chaque fiche suit le format", () => {
  for (const f of files) {
    const x = JSON.parse(readFileSync(join(DIR, f), "utf8")), id = f.replace(/\.json$/, "");
    assert.equal(x.id, id, f);
    assert.ok(typeof x.resume === "string" && x.resume.trim(), `${id} : resume`);
    assert.ok(Array.isArray(x.commandes) && x.commandes.length, `${id} : commandes`);
    const idx = x.commandes.map((c) => ORDER.indexOf(c.commande));
    assert.ok(idx.every((i) => i >= 0), `${id} : commande hors liste`);
    assert.ok(idx.every((i, k) => k === 0 || i > idx[k - 1]), `${id} : doublon ou désordre`);
    assert.ok(x.commandes.every((c) => typeof c.role === "string" && c.role.trim()), `${id} : rôle vide`);
    assert.ok(Array.isArray(x.gestes) && x.gestes.every((g) => typeof g === "string" && g.trim()), `${id} : gestes`);
    assert.ok(Array.isArray(x.modes) && x.modes.every((m) => m.nom?.trim() && m.texte?.trim()), `${id} : modes`);
    assert.ok(x.a_savoir === undefined || (Array.isArray(x.a_savoir) && x.a_savoir.every((t) => typeof t === "string" && t.trim())), `${id} : a_savoir`);
    assert.equal(typeof x.d_apres_le_code, "boolean", `${id} : d_apres_le_code`);
    assert.ok(!JSON.stringify(x).includes("<"), `${id} : un < dans le texte`);
    if (id === "fm1va") {
      assert.equal(x.source.commit, null);
      assert.equal(x.source.url, "https://baudgirl.com/work/FM-1+VA/manual");
      continue;
    }
    const e = cat.find((c) => c.id === id);
    assert.ok(e, `${id} : absent du catalogue`);
    assert.equal(x.source.commit, e.commit_source, `${id} : commit`);
    assert.ok([`${e.depot}/blob/${e.commit_source}/`, `${e.depot}/tree/${e.commit_source}/`].some((p) => x.source.url.startsWith(p)), `${id} : url`);
  }
});

test("chaque firmware optimisé (natif) a sa fiche, FM-1+VA aussi", () => {
  const natifs = JSON.parse(readFileSync(join(ROOT, "tools/natif.json"), "utf8")).firmwares.map((f) => f.id);
  const ids = new Set(files.map((f) => f.replace(/\.json$/, "")));
  const manquantes = [...natifs, "fm1va"].filter((id) => !ids.has(id));
  assert.deepEqual(manquantes, []);
});

test("chaque firmware natif a sa fiche anglaise, de même forme que la française", () => {
  const EN = join(DIR, "en");
  const natifs = JSON.parse(readFileSync(join(ROOT, "tools/natif.json"), "utf8")).firmwares.map((f) => f.id);
  for (const id of [...natifs, "fm1va"]) {
    assert.ok(existsSync(join(EN, `${id}.json`)), `${id} : fiche anglaise absente`);
    const fr = JSON.parse(readFileSync(join(DIR, `${id}.json`), "utf8")), en = JSON.parse(readFileSync(join(EN, `${id}.json`), "utf8"));
    assert.equal(en.id, id);
    assert.deepEqual(en.commandes.map((c) => c.commande), fr.commandes.map((c) => c.commande), `${id} : commandes`);
    assert.equal(en.gestes.length, fr.gestes.length, `${id} : gestes`);
    assert.equal(en.modes.length, fr.modes.length, `${id} : modes`);
    assert.equal((en.a_savoir || []).length, (fr.a_savoir || []).length, `${id} : a_savoir`);
    assert.deepEqual(en.source, fr.source, `${id} : source`);
    assert.equal(en.d_apres_le_code, fr.d_apres_le_code, `${id} : d_apres_le_code`);
    assert.ok(en.resume.trim() && en.commandes.every((c) => c.role.trim()), `${id} : textes vides`);
    assert.ok(!JSON.stringify(en).includes("<"), `${id} : un < dans le texte`);
  }
});

test("le dictionnaire de l'interface : aucune valeur n'est aussi une clé, les motifs compilent", () => {
  const d = JSON.parse(readFileSync(join(ROOT, "assets/lang-en.json"), "utf8"));
  for (const [k, v] of Object.entries(d.exact)) assert.ok(v && !(v in d.exact), `${k} : valeur vide ou rebouclée`);
  for (const [re] of d.patterns) new RegExp(re, "u");
});
