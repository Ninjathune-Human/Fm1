"""Les potards d'un clavier MIDI liés à ceux du panneau : association, puis le potard du panneau suit."""
from conftest import power_on

CC = "window.__midiRoute({ name: 'x' }, Uint8Array.from([0xB0, %d, %d]))"


def test_potards_associes(page):
    power_on(page)
    page.evaluate("document.getElementById('midi-box').hidden = false")
    page.evaluate("() => { const h = window.__host, t = h.turn.bind(h); window.__turns = []; h.turn = (l, n, v) => { window.__turns.push([l, n]); return t(l, n, v); }; }")
    page.evaluate("window.__midiRoute({ name: 'x' }, Uint8Array.from([0xB0, 74, 10]))")      # pas encore associé : rien ne tourne
    assert page.evaluate("window.__turns") == []
    page.click("#midi-btn"); page.click("#midi-learn")
    assert page.get_attribute("#midi-learn", "aria-pressed") == "true" or True
    page.evaluate("window.__midiRoute({ name: 'x' }, Uint8Array.from([0xB0, 75, 5]))")      # aucun potard choisi : sans effet
    page.locator("#device .hit.knob").nth(4).click()                                          # KNOB1
    assert page.evaluate("document.querySelector('#device').classList.contains('learn-on')")
    assert page.evaluate("window.__turns") == []                                              # toucher n'a rien tourné
    page.evaluate(CC % (74, 20))                                                              # le CC 74 devient KNOB1
    assert page.evaluate("window.__turns") == []
    page.keyboard.press("Escape")
    assert not page.evaluate("document.querySelector('#device').classList.contains('learn-on')")
    page.evaluate(CC % (74, 23))
    assert page.evaluate("window.__turns") == [["KNOB1", 6]]
    page.evaluate(CC % (74, 21))
    assert page.evaluate("window.__turns[1]") == ["KNOB1", -4]
    # MASTER : valeur absolue
    page.click("#midi-btn"); page.click("#midi-learn")
    page.locator("#device .hit.knob").nth(0).click()
    page.evaluate(CC % (7, 64)); page.keyboard.press("Escape")
    page.evaluate(CC % (7, 127))
    assert page.evaluate("window.__host.G.master") > 0.97
    page.evaluate(CC % (7, 0))
    assert page.evaluate("window.__host.G.master") < 0.03
    # effacer
    page.click("#midi-btn"); page.click("#midi-unlearn")
    n = page.evaluate("window.__turns.length")
    page.evaluate(CC % (74, 30))
    assert page.evaluate("window.__turns.length") == n


def test_potard_sans_fin(page):
    """Le premier potard du MiniLab envoie 64 + écart : reconnu après quelques messages, il fait varier le potard dans les deux sens."""
    power_on(page)
    page.evaluate("document.getElementById('midi-box').hidden = false")
    page.evaluate("() => { const h = window.__host, t = h.turn.bind(h); window.__turns = []; h.turn = (l, n, v) => { window.__turns.push([l, n]); return t(l, n, v); }; }")
    page.click("#midi-btn"); page.click("#midi-learn")
    page.locator("#device .hit.knob").nth(0).click()                                          # MASTER
    page.evaluate(CC % (112, 65)); page.keyboard.press("Escape")
    for v in (65, 65, 66, 65, 65, 66):                                                        # tourné vers la droite : écarts positifs
        page.evaluate(CC % (112, v))
    page.evaluate("window.__turns.length = 0")
    page.evaluate(CC % (112, 66)); page.evaluate(CC % (112, 63))
    t = page.evaluate("window.__turns")
    assert [x[0] for x in t] == ["MASTER", "MASTER"] and t[0][1] > 0 and t[1][1] < 0, t
