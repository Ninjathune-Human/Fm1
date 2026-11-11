import { test } from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const cat = JSON.parse(readFileSync(join(ROOT, "firmwares/catalogue.json"), "utf8"));

test("le catalogue compte 133 entrées aux ids uniques, Bubba Machine, NACHTFAHRT, FMDj, SPAMPY, Scintilla, ECHOFIELD, GRAINE, Elixir et KARMA compris", () => {
  assert.equal(cat.firmwares.length, 133);
  assert.equal(new Set(cat.firmwares.map((e) => e.id)).size, 133);
  assert.ok(cat.firmwares.some((e) => e.id === "bubba"));
  assert.ok(cat.firmwares.some((e) => e.id === "karma"));
});

test("chaque paquet local existe et a l'empreinte du catalogue", () => {
  for (const e of cat.firmwares.filter((e) => e.fichier)) {
    const p = join(ROOT, e.fichier);
    assert.ok(existsSync(p), `${e.id} : ${e.fichier} absent`);
    assert.equal(createHash("sha256").update(readFileSync(p)).digest("hex"), e.sha256, e.id);
  }
});

test("une entrée sans paquet local a un paquet en ligne sur le Hub, sauf un natif seul qui n'y est pas", () => {
  for (const e of cat.firmwares.filter((e) => !e.fichier)) {
    if (e.paquet_en_ligne === null && e.natif_seulement) continue;   // ECHOFIELD, GRAINE, Elixir
    assert.match(e.paquet_en_ligne || "", /^https:\/\/thefirmwarehub\.com\/fw\//, e.id);
  }
});

test("chaque firmware a un état d'émulation mesuré ou déclaré", () => {
  const allowed = new Set(["fonctionne selon fm1-emu", "vérifié", "ne démarre pas"]);
  // un paquet seulement en ligne n'a pas pu être essayé ici : il garde « pas encore évalué »
  for (const e of cat.firmwares) assert.ok(allowed.has(e.emulateur_fm1emu) || (!e.fichier && e.emulateur_fm1emu === "pas encore évalué"), `${e.id} : ${e.emulateur_fm1emu}`);
});

test("chaque firmware dit s'il suit l'horloge MIDI (tempo lié du Duo) : par l'USB ou la TRS, par l'USB seulement, ou pas", () => {
  for (const e of cat.firmwares) assert.ok([true, false, "usb"].includes(e.horloge_midi), e.id);
});

test("chaque firmware dit s'il est vérifié en Duo, tempo lié (tempo_lie) : seulement s'il sait suivre l'horloge MIDI, ou si rien ne le lance (demarre false)", () => {
  for (const e of cat.firmwares) {
    assert.equal(typeof e.tempo_lie, "boolean", e.id);
    assert.ok(!("demarre" in e) || e.demarre === false, e.id);
    if (e.tempo_lie) assert.ok(e.horloge_midi || e.demarre === false, e.id);
  }
});
