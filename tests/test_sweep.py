"""L'animation lumineuse de l'allumage (celle de Felucca 1.1) : FM-1+VA la joue, et le panneau dessine celle des natifs."""
from conftest import power_on


def levels(page):
    return page.evaluate("() => [...document.querySelectorAll('#device .key')].sort((a, b) => a.dataset.key - b.dataset.key).map((k) => k.classList.contains('lv') ? +k.style.getPropertyValue('--lv') : null)")


def test_sweep_math(page):
    page.goto(page.base + "index.html")
    first = page.evaluate("() => { const peak = (id) => { let b = -1, at = 0; for (let f = 0; f < 640; f++) { const v = sweepLevel(f, id, false) & 0x7f; if (v > b) { b = v; at = f; } } return at; }; return [peak(14), peak(27), peak(40), peak(0)]; }")
    assert first[0] < first[1] < first[2]                               # la tête court de F3 à G5
    assert 352 <= first[3] <= 520                                       # puis les boutons montent
    assert page.evaluate("sweepLevel(700, 20, false)") == 0 and page.evaluate("sweepLevel(700, 20, true)") == 0x80


def test_fm1va_plays_the_sweep(page):
    page.goto(page.base + "index.html")
    page.click("#go")
    page.wait_for_function("window.__fw.on")
    seen = []
    for _ in range(12):
        seen.append(levels(page))
        page.wait_for_timeout(50)
    lit = [s for s in seen if any(v is not None for v in s)]
    assert lit, "aucune image de l'animation"
    page.wait_for_timeout(900)
    assert all(v is None for v in levels(page))                          # finie : les LED du firmware
    assert page.evaluate("window.__fw.ledLevels()") is None


def test_native_anim_drawn(page):
    power_on(page)
    page.evaluate("() => { window.__fw.ledLevels = () => Array.from({ length: 41 }, (_, i) => (i === 14 ? 1 : 0)); }")
    page.wait_for_timeout(200)
    lv = levels(page)
    assert lv[0] == 1 and lv[1] == 0
    page.evaluate("() => { delete window.__fw.ledLevels; }")
    page.wait_for_timeout(200)
    assert all(v is None for v in levels(page))
