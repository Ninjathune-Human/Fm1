"""L'aide : manuel, raccourcis clavier, fiches par firmware."""

NO_LAYOUT = "Object.defineProperty(Navigator.prototype, 'keyboard', { get: () => undefined });"


def titles(page):
    return page.eval_on_selector_all(".notes > details > summary", "s => s.map(x => x.textContent.trim())")


def test_titres(page):
    page.goto(page.base + "index.html")
    assert titles(page)[:2] == ["Manuel d'utilisation", "Raccourcis clavier"]


def test_manuel_rubriques(page):
    page.goto(page.base + "index.html")
    assert page.eval_on_selector_all("#aide-manuel dt", "d => d.map(x => x.textContent)") == [
        "Allumer", "Firmwares", "Boutons propres à un firmware", "Coloris", "Solo et Duo", "MIDI", "Plein écran",
        "Ce que le navigateur garde", "Crédits et licences"]


def test_clavier_dessine(page):
    page.goto(page.base + "index.html")
    page.click("#aide-clavier summary")
    want = page.evaluate("keyboardModel(keyLetters(navigator.language, null)).keys.filter(k => k.family)"
                         ".map(k => [k.code, k.label])")
    got = page.eval_on_selector_all("#clavier g[data-family]:not([data-family=''])",
                                    "g => g.map(x => [x.dataset.code, x.querySelector('.fonction').textContent])")
    assert sorted(got) == sorted(want) and len(got) == 40          # 18 notes, 16 boutons, 6 sens de molette


def lettre(browser, base, locale, code):
    ctx = browser.new_context(locale=locale)
    ctx.add_init_script(NO_LAYOUT)
    pg = ctx.new_page()
    pg.goto(base + "index.html")
    t = pg.text_content(f"#clavier [data-code='{code}'] .lettre")
    ctx.close()
    return t


def test_azerty_par_defaut(browser, base_url):
    assert lettre(browser, base_url, "fr-FR", "KeyA") == "Q"
    assert lettre(browser, base_url, "en-US", "KeyA") == "A"


def test_volet_large(page):
    page.goto(page.base + "index.html")
    page.click("#aide-clavier summary")
    w = page.evaluate("[document.querySelector('#aide-clavier').offsetWidth, document.querySelector('.notes').clientWidth]")
    assert abs(w[0] - w[1]) <= 2


def test_clavier_iphone(browser, base_url):
    ctx = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    pg = ctx.new_page()
    pg.goto(base_url + "index.html")
    pg.click("#aide-clavier summary")
    over = pg.evaluate("[document.documentElement.scrollWidth, innerWidth]")
    box = pg.evaluate("(() => { const s = document.querySelector('.clavier-scroll'); return [s.scrollWidth, s.clientWidth]; })()")
    ctx.close()
    assert over[0] <= over[1] and box[0] > box[1]
