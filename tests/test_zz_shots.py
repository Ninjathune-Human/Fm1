"""Essai seulement : des captures de Melodee, en annotations."""
import base64
from conftest import power_on
from test_emu import use


def test_shots(page):
    power_on(page)
    page.set_default_timeout(30000)
    assert use(page, "melodee") is True
    page.wait_for_timeout(3500)
    out = []
    def snap(name):
        url = page.evaluate("document.getElementById('screen').toDataURL('image/png')")
        out.append(f"{name} {url.split(',')[1]}")
        b = page.locator("#screen").evaluate("e => { const d = e.closest('.device') || e.parentElement.parentElement; const r = d.getBoundingClientRect(); return [r.x, r.y, r.width, r.height]; }")
        img = page.screenshot(type="jpeg", quality=35, clip={"x": b[0], "y": b[1], "width": b[2], "height": b[3]}, scale="css")
        out.append(f"{name}-panneau {base64.b64encode(img).decode()}")
    snap("stage")
    page.evaluate("window.__host.keyDown(7, 't')"); page.wait_for_timeout(300); snap("touche"); page.evaluate("window.__host.keyUp('t')")
    page.evaluate("window.__host.press('SEQ')"); page.wait_for_timeout(150); page.evaluate("window.__host.release('SEQ')"); page.wait_for_timeout(500); snap("seq")
    page.evaluate("window.__host.press('PLAY')"); page.wait_for_timeout(150); page.evaluate("window.__host.release('PLAY')"); page.wait_for_timeout(800); snap("play")
    open("shots.txt", "w").write("\n".join(out))
