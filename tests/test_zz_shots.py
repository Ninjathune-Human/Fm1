"""Essai seulement : des captures, poussées dans une branche."""
import os
from conftest import power_on
from test_emu import use


def test_shots(page):
    power_on(page)
    page.set_default_timeout(30000)
    os.makedirs("shots", exist_ok=True)
    assert use(page, "mycelium")
    open("shots/kind.txt", "w").write(page.evaluate("window.__engine().kind"))
    def snap(name):
        b = page.locator("#screen").evaluate("e => { const d = e.closest('.device') || e.parentElement.parentElement; const r = d.getBoundingClientRect(); return [r.x, r.y, r.width, r.height]; }")
        page.screenshot(path=f"shots/mycelium-{name}.png", clip={"x": b[0], "y": b[1], "width": b[2], "height": b[3]})
    page.wait_for_timeout(1000); snap("1s")
    page.wait_for_timeout(2500); snap("3s5")
    page.wait_for_timeout(1500); snap("5s")
