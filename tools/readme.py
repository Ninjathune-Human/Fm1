"""Écrit, dans README.md, la liste des firmwares par catégorie, entre les marqueurs <!-- firmwares -->."""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORDER = ["Officiel", "Groovebox", "Synthé", "Accords", "Boîte à rythmes", "Tracker", "Autre"]
STATE = {"vérifié": "vérifié", "fonctionne selon fm1-emu": "fonctionne", "pas encore évalué": "non évalué"}


def cell(s):
    return str(s).replace("|", "\\|")


def table(entries):
    lines = ["| Firmware | Auteur | Licence | Source | État |", "|---|---|---|---|---|"]
    for e in sorted(entries, key=lambda e: e["nom"].lower()):
        src = f"[{e['commit_source'][:7]}]({e['depot']}/tree/{e['commit_source']})" if e.get("commit_source") else f"[dépôt]({e['depot']})"
        state = STATE.get(e["emulateur_fm1emu"], e["emulateur_fm1emu"]) + (", bêta" if e.get("beta") else "") + (", natif" if e.get("natif_seulement") else "" if e.get("fichier") else ", en ligne")
        lines.append(f"| {cell(e['nom'])} | {cell(e['auteur'])} | {cell(e['licence'])} | {src} | {state} |")
    return "\n".join(lines)


def main():
    cat = json.load(open(os.path.join(ROOT, "firmwares/catalogue.json"), encoding="utf-8"))["firmwares"]
    groups = {c: [] for c in ORDER}
    for e in cat:
        if e["id"] == "bubba":
            continue
        first = (e["categories"] or ["Autre"])[0]
        groups["Autre" if first not in groups else first].append(e)
    body = "\n\n".join(f"### {c} ({len(v)})\n\n{table(v)}" for c, v in groups.items() if v)
    path = os.path.join(ROOT, "README.md")
    text = open(path, encoding="utf-8").read()
    text = re.sub(r"<!-- firmwares -->.*<!-- /firmwares -->", lambda _: f"<!-- firmwares -->\n{body}\n<!-- /firmwares -->", text, flags=re.S)
    open(path, "w", encoding="utf-8").write(text)


if __name__ == "__main__":
    main()
