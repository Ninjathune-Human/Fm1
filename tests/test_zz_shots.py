"""Essai seulement : des captures, poussées dans une branche."""
import os
from conftest import power_on
from test_emu import use


def test_shots(page, tmp_path):
    power_on(page)
    page.set_default_timeout(30000)
    os.makedirs("shots", exist_ok=True)
    assert use(page, "fmdj")
    page.wait_for_timeout(3000)
    def snap(name):
        b = page.locator("#screen").evaluate("e => { const d = e.closest('.device') || e.parentElement.parentElement; const r = d.getBoundingClientRect(); return [r.x, r.y, r.width, r.height]; }")
        page.screenshot(path=f"shots/fmdj-{name}.png", clip={"x": b[0], "y": b[1] - 10, "width": b[2], "height": b[3] + 120})
    snap("demarrage")
    page.evaluate("window.__host.press('PLAY')"); page.wait_for_timeout(150); page.evaluate("window.__host.release('PLAY')")
    page.wait_for_timeout(1500); snap("play")
    (tmp_path / "x.gb").write_bytes(bytes(32768))
    page.set_input_files("#samples", str(tmp_path / "x.gb")); page.wait_for_timeout(3000)
    open("shots/status.txt", "w").write(page.inner_text("#status"))
    page.screenshot(path="shots/fmdj-page.png", full_page=True)
