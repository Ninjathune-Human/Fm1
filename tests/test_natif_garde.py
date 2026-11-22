"""Un firmware dont la version navigateur n'a pas pu être faite ce coup-ci (source introuvable, compilation en échec) garde
celle du dernier déploiement (tools/natif_garde.py) au lieu de redevenir émulé ; ceux qui ont réussi ne sont pas touchés."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/natif_garde.py"


def natif(d, fid, mark):
    (d / fid).mkdir(parents=True)
    (d / fid / "natif.json").write_text(json.dumps({"wasm": f"{fid}.wasm", "dialecte": "fm1", "mark": mark}))
    (d / fid / f"{fid}.wasm").write_text(mark)


def test_garde_les_manquants(tmp_path):
    liste = tmp_path / "natif.json"
    liste.write_text(json.dumps({"firmwares": [{"id": "amb"}, {"id": "evilgenius"}, {"id": "ruido"}, {"id": "neuf"}]}))
    site, ancien = tmp_path / "site", tmp_path / "ancien"
    natif(site, "amb", "nouveau")                     # compilé ce coup-ci
    natif(ancien, "amb", "ancien")
    natif(ancien, "evilgenius", "ancien")             # échec ce coup-ci, présent au dernier déploiement
    natif(ancien, "ruido", "ancien")
    out = subprocess.run([sys.executable, str(TOOL), str(liste), str(site), str(ancien)], capture_output=True, text=True, check=True).stdout
    assert json.loads((site / "amb/natif.json").read_text())["mark"] == "nouveau"            # le neuf n'est pas écrasé
    for fid in ("evilgenius", "ruido"):
        assert json.loads((site / fid / "natif.json").read_text())["mark"] == "ancien"
        assert (site / fid / f"{fid}.wasm").read_text() == "ancien"
        assert f"::warning title=natif {fid}::" in out
    assert not (site / "neuf").exists()               # jamais publié : il reste émulé


def test_sans_archive(tmp_path):
    liste = tmp_path / "natif.json"
    liste.write_text(json.dumps({"firmwares": [{"id": "evilgenius"}]}))
    site = tmp_path / "site"; site.mkdir()
    subprocess.run([sys.executable, str(TOOL), str(liste), str(site), str(tmp_path / "absent")], check=True)
    assert not (site / "evilgenius").exists()
