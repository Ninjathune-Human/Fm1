"""Démarre chaque firmware local du catalogue dans le sélecteur et mesure écran et son.

Usage : python3 tests/boot_all.py [id ...]
Écrit tests/boot_all.json et docs/verification.md.
"""
import json
import os
import sys
import time

from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(__file__))
from serve import serve  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAT = json.load(open(os.path.join(ROOT, "firmwares", "catalogue.json")))["firmwares"]
LIT_MIN, RMS_MIN = 500, 0.0005

LIT_JS = """() => { const c = document.getElementById('screen'), d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
  let n = 0; for (let i = 0; i < d.length; i += 4) if (d[i] + d[i + 1] + d[i + 2] > 30) n++; return n; }"""
RMS_JS = """async () => { const an = window.__engine().an, d = new Float32Array(an.fftSize); let best = 0;
  for (let k = 0; k < 20; k++) { an.getFloatTimeDomainData(d); let s = 0; for (const x of d) s += x * x;
    best = Math.max(best, Math.sqrt(s / d.length)); await new Promise((r) => setTimeout(r, 50)); } return best; }"""


def check(page, e):
    t0 = time.time()
    ok = page.evaluate("async (id) => window.__useEngine(window.__catalogue.find((x) => x.id === id))", e["id"])
    took = time.time() - t0
    if not ok or took > 30:
        return {"id": e["id"], "nom": e["nom"], "boot": False, "lit": 0, "rms": 0.0, "s": round(took, 1)}
    page.wait_for_timeout(4000)
    lit = page.evaluate(LIT_JS)
    page.evaluate("window.__host.press('PLAY')"); page.wait_for_timeout(150); page.evaluate("window.__host.release('PLAY')")
    page.evaluate("window.__host.keyDown(12, 'v')")
    level = page.evaluate(RMS_JS)
    page.evaluate("window.__host.keyUp('v')")
    page.evaluate("window.__host.press('PLAY')"); page.wait_for_timeout(150); page.evaluate("window.__host.release('PLAY')")
    return {"id": e["id"], "nom": e["nom"], "boot": True, "lit": lit, "rms": round(level, 5), "s": round(took, 1)}


def verdict(r):
    if not r["boot"] or r["lit"] < LIT_MIN:
        return "ne démarre pas"
    return "vérifié" if r["rms"] > RMS_MIN else "silencieux"


def main(ids):
    todo = [e for e in CAT if e.get("fichier") and e["id"] != "bubba" and (not ids or e["id"] in ids)]
    results = []
    with serve(ROOT) as url, sync_playwright() as p:
        b = p.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])
        page = None
        for i, e in enumerate(todo):
            if page is None or i % 15 == 0:            # une page neuve de temps en temps : mémoire bornée
                if page:
                    page.context.close()
                page = b.new_context(viewport={"width": 1280, "height": 900}).new_page()
                page.set_default_timeout(40000)
                page.goto(url + "index.html")
                page.click("#go")
                page.wait_for_function("document.getElementById('power').getAttribute('aria-checked') === 'true' && window.__catalogue.length > 0")
            try:
                r = check(page, e)
            except Exception as err:                  # page bloquée : on repart d'une page neuve
                r = {"id": e["id"], "nom": e["nom"], "boot": False, "lit": 0, "rms": 0.0, "s": 0, "erreur": str(err)[:120]}
                page.context.close(); page = None
                if i + 1 < len(todo):
                    page = b.new_context(viewport={"width": 1280, "height": 900}).new_page()
                    page.set_default_timeout(40000)
                    page.goto(url + "index.html"); page.click("#go")
                    page.wait_for_function("document.getElementById('power').getAttribute('aria-checked') === 'true' && window.__catalogue.length > 0")
            r["verdict"] = verdict(r)
            r["declare"] = e["emulateur_fm1emu"]
            results.append(r)
            print(f"{e['id']:14} {r['verdict']:15} lit={r['lit']:7} rms={r['rms']:.4f} {r['s']} s", flush=True)
        b.close()
    json.dump(results, open(os.path.join(ROOT, "tests", "boot_all.json"), "w"), indent=1, ensure_ascii=False)
    write_report(results)


def write_report(results):
    lines = ["# Vérification des firmwares", "",
             f"Chaque paquet local démarre dans le sélecteur (Chromium sans interface, cœur fm1-emu à 100 MHz). "
             f"Critères : démarrage en moins de 30 s, au moins {LIT_MIN} pixels allumés après 4 s, "
             f"niveau RMS supérieur à {RMS_MIN} pendant PLAY puis la touche 12 tenue 1 s.", "",
             "| Firmware | État déclaré | Résultat | Pixels | RMS | Démarrage (s) |", "|---|---|---|---:|---:|---:|"]
    for r in sorted(results, key=lambda r: r["nom"].lower()):
        lines.append(f"| {r['nom']} | {r['declare']} | {r['verdict']} | {r['lit']} | {r['rms']} | {r['s']} |")
    n = {v: sum(1 for r in results if r["verdict"] == v) for v in ("vérifié", "silencieux", "ne démarre pas")}
    lines += ["", f"Total : {len(results)} firmwares, {n['vérifié']} vérifiés, {n['silencieux']} démarrés sans son mesuré, "
              f"{n['ne démarre pas']} qui ne démarrent pas.", "",
              "« Silencieux » : le firmware démarre et affiche son écran, mais ne produit pas de son avec PLAY et une touche ; "
              "c'est attendu pour un contrôleur MIDI ou un moniteur, et ne vaut pas un échec."]
    open(os.path.join(ROOT, "docs", "verification.md"), "w").write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main(set(sys.argv[1:]))
