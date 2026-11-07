"""Essai seulement : des captures de Melodee, en annotations."""
import base64
from conftest import power_on
from test_emu import use


def test_shots(page):
    power_on(page)
    page.set_default_timeout(30000)
    assert use(page, "modelar") is True
    page.wait_for_timeout(3500)
    import os
    os.makedirs("shots", exist_ok=True)
    def snap(name):
        url = page.evaluate("document.getElementById('screen').toDataURL('image/png')")
        open(f"shots/{name}.png", "wb").write(base64.b64decode(url.split(',')[1]))
        b = page.locator("#screen").evaluate("e => { const d = e.closest('.device') || e.parentElement.parentElement; const r = d.getBoundingClientRect(); return [r.x, r.y, r.width, r.height]; }")
        page.screenshot(path=f"shots/{name}-panneau.png", clip={"x": b[0], "y": b[1], "width": b[2], "height": b[3]})
    for _ in range(6):
        page.evaluate("window.__host.turn('KNOB1', 5)"); page.wait_for_timeout(80)
    snap("stage")
    page.evaluate("window.__host.keyDown(0, 't')"); page.wait_for_timeout(300); snap("touche"); page.evaluate("window.__host.keyUp('t')")
    page.evaluate("window.__host.press('SEQ')"); page.wait_for_timeout(150); page.evaluate("window.__host.release('SEQ')"); page.wait_for_timeout(500); snap("seq")
    page.evaluate("window.__host.press('PLAY')"); page.wait_for_timeout(150); page.evaluate("window.__host.release('PLAY')"); page.wait_for_timeout(800); snap("play")
