"""Une note MIDI allume sa touche sur le panneau, quel que soit le firmware (Chipbox n'allume rien lui-même en MIDI)."""
from conftest import power_on
from test_emu import use

NOTE = "window.__midiRoute({ name: 'x' }, Uint8Array.from([%s]))"
LIT = "() => [...document.querySelectorAll('#device .key.lit, #device [class*=key].lit')].length"


def test_note_midi_allume_la_touche(page):
    power_on(page)
    page.set_default_timeout(30000)
    assert use(page, "chipbox") is True
    page.wait_for_timeout(3000)
    before = page.evaluate(LIT)
    page.evaluate(NOTE % "0x90, 65, 100")
    page.wait_for_timeout(400)
    assert page.evaluate(LIT) == before + 1
    page.evaluate(NOTE % "0x80, 65, 0")
    page.wait_for_timeout(400)
    assert page.evaluate(LIT) == before
    page.evaluate(NOTE % "0x90, 70, 100"); page.evaluate(NOTE % "0x90, 72, 100")
    page.wait_for_timeout(300)
    assert page.evaluate(LIT) == before + 2
    page.evaluate(NOTE % "0xB0, 123, 0")                      # toutes les notes coupées
    page.wait_for_timeout(400)
    assert page.evaluate(LIT) == before
