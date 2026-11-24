"""Audit : les touches du panneau s'allument-elles quand le firmware est joué en MIDI ? (python -m pytest -q -s tests/audit_midi_leds.py)
Pour chaque firmware natif : touches allumées au repos, sous une touche du panneau, sous une note MIDI (53 à 79, F3 à G5 : les 27 touches), et le son de la note MIDI.
Écrit /tmp/audit_midi_leds.json."""
import json
import os
from conftest import ROOT, power_on
from test_emu import rms, use

KEYS = range(0, 24)
LIT = "() => { const h = window.__host, r = []; for (let i = 0; i < 24; i++) if (h.keyLit(i)) r.push(i); return r; }"


def test_audit(page):
    ids = sorted(i for i in json.load(open(os.path.join(ROOT, "natif/manifest.json"))) if i != "fmdj")
    only = os.environ.get("AUDIT_IDS")
    if only: ids = [i for i in ids if i in only.split(",")]
    power_on(page)
    page.set_default_timeout(30000)
    out = {}
    for i in ids:
        if use(page, i) is not True:
            out[i] = {"erreur": "démarrage"}; continue
        page.wait_for_timeout(3500)
        base = set(page.evaluate(LIT))
        page.evaluate("window.__host.keyDown(12, 't')"); page.wait_for_timeout(350)
        press = set(page.evaluate(LIT)) - base
        page.evaluate("window.__host.keyUp('t')"); page.wait_for_timeout(300)
        lit_notes, loud = {}, 0.0
        for n in range(53, 80):
            page.evaluate(f"window.__midiRoute({{ name: 'audit' }}, Uint8Array.from([0x90, {n}, 100]))")
            page.wait_for_timeout(110)
            new = sorted(set(page.evaluate(LIT)) - base)
            if new: lit_notes[n] = new
            loud = max(loud, rms(page))
            page.evaluate(f"window.__midiRoute({{ name: 'audit' }}, Uint8Array.from([0x80, {n}, 0]))")
        out[i] = {"repos": sorted(base), "touche": sorted(press), "midi": lit_notes, "son_midi": round(loud, 4)}
        print(i, "touche", sorted(press)[:3], "midi", len(lit_notes), "son", round(loud, 4), flush=True)
    json.dump(out, open("/tmp/audit_midi_leds.json", "w"), indent=1)
