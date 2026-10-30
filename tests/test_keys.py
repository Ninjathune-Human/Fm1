"""Le clavier de l'ordinateur, comme sur la page de fm1-emu : un piano sur A..', les boutons sur les chiffres."""
from conftest import power_on


def test_piano_and_buttons(page):
    power_on(page)
    page.evaluate("""() => { const fw = window.__fw; window.__k = []; window.__b = [];
      const kd = fw.keyDown.bind(fw), pr = fw.press.bind(fw);
      fw.keyDown = (i, s) => { window.__k.push(i); return kd(i, s); }; fw.press = (b) => { window.__b.push(b); return pr(b); }; }""")
    page.mouse.click(5, 5)                                               # la page a le focus, pas un bouton
    for code in ["KeyA", "KeyW", "Quote", "Digit1", "Digit0", "Space", "KeyR", "KeyZ"]:
        page.keyboard.press(code)
    assert page.evaluate("window.__k") == [7, 8, 24]                     # Do 4, Do# 4, Fa 5
    assert page.evaluate("window.__b") == ["FX", "SEQ", "PLAY", "REC", "OCT-"]


def test_arrows_turn_select_and_presets(page):
    power_on(page)
    page.evaluate("""() => { const fw = window.__fw; window.__t = []; const t = fw.turn.bind(fw); fw.turn = (r, n, v) => { window.__t.push([r, Math.sign(n)]); return t(r, n, v); }; }""")
    page.mouse.click(5, 5)
    for code in ["ArrowRight", "ArrowUp", "Period"]:
        page.keyboard.press(code)
    seen = page.evaluate("window.__t.map((x) => x.join(' '))")
    assert "SELECT 1" in seen and "PRESETS 1" in seen and "ALGORITHM 1" in seen


def test_fields_keep_their_keys(page):
    power_on(page)
    page.evaluate("() => { const fw = window.__fw; window.__k = []; const kd = fw.keyDown.bind(fw); fw.keyDown = (i, s) => { window.__k.push(i); return kd(i, s); }; }")
    page.click("#fw-picker")
    page.fill("#fw-search", "")
    page.type("#fw-search", "as")                                        # dans la recherche : des lettres, pas des notes
    assert page.evaluate("window.__k") == []
