"""Essai seulement : des captures, poussées dans une branche."""
import os
from conftest import power_on
from test_emu import use


def test_shots(page):
    power_on(page)
    page.set_default_timeout(30000)
    os.makedirs("shots", exist_ok=True)
    for fid in ("mnm1", "cutador", "mycelium"):
        if not use(page, fid): continue
        page.wait_for_timeout(5000)
        def snap(name):
            b = page.locator("#screen").evaluate("e => { const d = e.closest('.device') || e.parentElement.parentElement; const r = d.getBoundingClientRect(); return [r.x, r.y, r.width, r.height]; }")
            page.screenshot(path=f"shots/{fid}-{name}.png", clip={"x": b[0], "y": b[1], "width": b[2], "height": b[3]})
        snap("repos")
        page.evaluate("window.__host.press('PLAY')"); page.wait_for_timeout(150); page.evaluate("window.__host.release('PLAY')")
        page.wait_for_timeout(1500); snap("play")
        page.evaluate("window.__host.keyDown(0, 't')"); page.wait_for_timeout(400); snap("touche"); page.evaluate("window.__host.keyUp('t')")
        page.evaluate("window.__host.press('PLAY')"); page.wait_for_timeout(150); page.evaluate("window.__host.release('PLAY')")
