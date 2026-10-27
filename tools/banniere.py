"""Génère assets/banniere.png (1280 × 640) : le panneau FM-1 avec Felucca à l'écran, et le titre."""
import base64
import os
import sys

from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
from serve import serve  # noqa: E402

PAGE = """<!doctype html><meta charset="utf-8"><style>
html, body { margin: 0; width: 1280px; height: 640px; background: #f5f5f7; overflow: hidden; }
body { display: grid; grid-template-columns: 430px 1fr; align-items: center; font-family: Inter, system-ui, sans-serif; color: #1d1d1f; }
.text { padding-left: 72px; }
.eyebrow { font: 600 15px/1.2 Inter; letter-spacing: .08em; text-transform: uppercase; color: #6e6e73; margin: 0 0 14px; }
h1 { font: 650 112px/0.95 Inter; letter-spacing: -0.035em; margin: 0; }
h1 span { color: #2b7865; }
p { font: 400 21px/1.4 Inter; color: #6e6e73; margin: 22px 0 0; max-width: 330px; }
img { width: 800px; margin-left: -10px; filter: drop-shadow(0 30px 40px rgb(0 0 0 / .18)); }
</style>
<div class="text"><p class="eyebrow">Émulateur dans le navigateur</p><h1>FM-1</h1>
<p>Le M-VAVE FM-1 et ses firmwares open source, un sélecteur pour passer de l'un à l'autre.</p></div>
<img src="data:image/png;base64,{img}">"""


def main():
    out = os.path.join(ROOT, "assets", "banniere.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with serve(ROOT) as url, sync_playwright() as p:
        b = p.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])
        pg = b.new_page(viewport={"width": 1440, "height": 1000}, device_scale_factor=2)
        pg.goto(url + "index.html")
        pg.click("#go")
        pg.wait_for_function("document.getElementById('status').textContent.startsWith('Allumé') && window.__catalogue.length > 0")
        pg.evaluate("async () => window.__useEngine(window.__catalogue.find((e) => e.id === 'felucca'))")
        pg.wait_for_timeout(3000)
        shot = pg.locator("#device").screenshot()
        pg.set_viewport_size({"width": 1280, "height": 640})
        pg.set_content(PAGE.replace("{img}", base64.b64encode(shot).decode()))
        pg.wait_for_timeout(300)
        pg.screenshot(path=out, clip={"x": 0, "y": 0, "width": 1280, "height": 640})
        b.close()
    print(out)


if __name__ == "__main__":
    main()
