import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const cat = JSON.parse(readFileSync(join(ROOT, "firmwares/catalogue.json"), "utf8")).firmwares;
const readme = readFileSync(join(ROOT, "README.md"), "utf8");

test("le README liste chaque firmware visible avec le lien vers sa source au commit exact", () => {
  for (const e of cat.filter((e) => e.id !== "bubba")) {
    assert.ok(readme.includes(`| ${e.nom.replace(/\|/g, "\\|")} |`), `${e.id} absent`);
    if (e.commit_source) assert.ok(readme.includes(`${e.depot}/tree/${e.commit_source}`), `${e.id} : lien source absent`);
  }
});

test("le README crédite fm1-emu et précise que FM-1+VA n'est pas redistribué", () => {
  assert.match(readme, /joakimeriksson\/fm1-emu/);
  assert.match(readme, /FM-1\+VA/);
  assert.match(readme, /n'est pas redistribué/);
});
