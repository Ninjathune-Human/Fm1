"""« Gestes du firmware » suit le firmware actif : FM-1+VA, NACHTFAHRT (ses gestes, sa prise en main, son manuel)."""
from conftest import power_on
from test_emu import use


def test_gestures_follow_the_firmware(page):
    power_on(page)
    assert page.evaluate("document.getElementById('gestes-fw').hidden") and "HOME" in page.text_content("#gestes-va")
    page.set_default_timeout(30000)
    assert use(page, "nachtfahrt") is True
    page.wait_for_function("!document.getElementById('gestes-fw').hidden")
    box = page.evaluate("document.getElementById('gestes-fw').innerHTML")
    assert "NACHTFAHRT" in box and "fm1-nachtfahrt/manual" in box and "Prise en main" in box and "Touches noires" in box
    assert page.evaluate("document.getElementById('gestes-va').hidden")
