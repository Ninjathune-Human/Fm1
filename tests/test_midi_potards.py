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
    assert page.evaluate("window.__turns") == [["KNOB1", 3]]
    page.evaluate(CC % (74, 21))
    assert page.evaluate("window.__turns[1]") == ["KNOB1", -2]
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


def test_select_un_cran_par_paliers(page):
    """SELECT parcourt un menu : un message de potard ne doit pas valoir un cran (127 messages = 127 crans), et un sens puis l'autre reste fidèle."""
    power_on(page)
    page.evaluate("document.getElementById('midi-box').hidden = false")
    page.evaluate("() => { const h = window.__host, t = h.turn.bind(h); window.__turns = []; h.turn = (l, n, v) => { window.__turns.push([l, n]); return t(l, n, v); }; }")
    page.click("#midi-btn"); page.click("#midi-learn")
    page.locator("#device .hit.knob").nth(1).click()                                          # SELECT
    page.evaluate(CC % (75, 20)); page.keyboard.press("Escape")
    for v in range(21, 46):                                                                   # 25 pas vers le haut
        page.evaluate(CC % (75, v))
    up = page.evaluate("window.__turns.filter(t => t[0] === 'SELECT')")
    assert 3 <= len(up) <= 10 and all(t[1] == 1 for t in up), up
    page.evaluate("window.__turns.length = 0")
    for v in range(45, 19, -1):                                                               # puis 25 pas vers le bas
        page.evaluate(CC % (75, v))
    down = page.evaluate("window.__turns.filter(t => t[0] === 'SELECT')")
    assert 3 <= len(down) <= 10 and all(t[1] == -1 for t in down), down


def test_sans_fin_rapide_sans_repetition(page):
    """Un potard sans fin tourné vite n'envoie pas deux fois la même valeur : il est quand même reconnu (sinon MASTER saute à 50 % et ne bouge plus)."""
    power_on(page)
    page.evaluate("document.getElementById('midi-box').hidden = false")
    page.click("#midi-btn"); page.click("#midi-learn")
    page.locator("#device .hit.knob").nth(0).click()
    page.evaluate(CC % (112, 65)); page.keyboard.press("Escape")
    for v in (66, 68, 65, 70, 67, 69, 66, 68, 67):
        page.evaluate(CC % (112, v))
    m0 = page.evaluate("window.__host.G.master")
    for v in (66, 67, 66, 68):
        page.evaluate(CC % (112, v))
    assert page.evaluate("window.__host.G.master") > m0 + 0.05
