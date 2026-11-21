"""Capture l'écran d'accueil de chaque firmware sans image d'auteur : firmwares/vignettes/<id>.png (240 x 240).
Lancé à la main : python -m pytest -q -s tests/capture_vignettes.py   (VIGNETTES=id1,id2 pour quelques-uns ; TOUS=1 pour tous)."""
import base64, io, json, os
from conftest import ROOT, power_on, lit_pixels
from test_emu import use

SHOT = "() => { const c = document.getElementById('screen'), d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data; let h = 0; for (let i = 0; i < d.length; i += 16) h = (h * 31 + d[i] + d[i + 1] + d[i + 2]) | 0; return h; }"
PNG = "() => document.getElementById('screen').toDataURL('image/png')"


def a_faire():
    cat = json.load(open(os.path.join(ROOT, "firmwares/catalogue.json")))["firmwares"]
    voulus = [i for i in os.environ.get("VIGNETTES", "").split(",") if i]
    if voulus: return voulus
    images = json.load(open("/tmp/rfw/catalog/catalog.json"))["firmwares"]      # le catalogue de RemoteFM1FW, cloné
    sans = [e["id"] for e in cat if os.environ.get("TOUS") or not images.get(e["id"], {}).get("image")]
    return [i for i in sans if i != "fmdj"]            # (sans ROM, FMDj n'affiche que son message)


def test_capture(page):
    from PIL import Image
    page.set_default_timeout(60000)
    power_on(page)
    os.makedirs(os.path.join(ROOT, "firmwares/vignettes"), exist_ok=True)
    echecs = []
    for i in a_faire():
        try:
            if use(page, i) is not True: echecs.append((i, "démarrage")); continue
            for _ in range(40):                           # jusqu'à ce qu'il y ait quelque chose et que l'écran se stabilise
                page.wait_for_timeout(500)
                if lit_pixels(page) >= 500: break
            if not os.environ.get("SANS_HOME"):           # HOME ramène à l'accueil ; SANS_HOME=1 pour un firmware qui s'y perd
                page.evaluate("window.__host.press('HOME')"); page.wait_for_timeout(250); page.evaluate("window.__host.release('HOME')")
            vu = None
            for _ in range(24):                           # deux mesures égales : l'accueil est posé
                page.wait_for_timeout(500); h = page.evaluate(SHOT)
                if h == vu: break
                vu = h
            data = base64.b64decode(page.evaluate(PNG).split(",", 1)[1])
            im = Image.open(io.BytesIO(data)).convert("RGB")
            im.quantize(64, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).save(os.path.join(ROOT, f"firmwares/vignettes/{i}.png"), optimize=True)
            print("ok", i, lit_pixels(page))
        except Exception as e:                            # un firmware lent ou récalcitrant ne bloque pas les autres
            echecs.append((i, str(e)[:80]))
    print("ÉCHECS", echecs)
