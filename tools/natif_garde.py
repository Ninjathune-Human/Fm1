"""Garde la version navigateur du dernier déploiement pour chaque firmware de tools/natif.json qui n'en a pas eu ce coup-ci
(source introuvable, compilation en échec) : sans elle, il redeviendrait émulé (« Non optimisés »).

    python3 tools/natif_garde.py tools/natif.json _site/natif <ancien>/natif

<ancien>/natif : le dossier natif/ de la dernière archive publiée (version GitHub « natif »). Absent : rien n'est repris.
Chaque reprise est signalée en annotation de l'action."""
import json
import shutil
import sys
from pathlib import Path


def main(liste, site, ancien):
    site, ancien = Path(site), Path(ancien)
    for f in json.loads(Path(liste).read_text())["firmwares"]:
        fid = f["id"]
        if (site / fid / "natif.json").exists() or not (ancien / fid / "natif.json").exists():
            continue
        shutil.copytree(ancien / fid, site / fid, dirs_exist_ok=True)
        print(f"::warning title=natif {fid}::pas de nouvelle version navigateur, celle du dernier déploiement est gardée")


if __name__ == "__main__":
    main(*sys.argv[1:4])
