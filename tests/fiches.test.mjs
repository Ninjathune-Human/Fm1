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
