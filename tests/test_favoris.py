"""Les favoris du sélecteur : une étoile par firmware, une section Favoris en tête."""


def open_with(page, fid):
    """Ouvre le sélecteur et déplie la catégorie de `fid`."""
    page.click("#fw-picker")
    page.evaluate("""(id) => {
      const ul = [...document.querySelectorAll('.fw-sec')].find((s) => s.dataset.cat !== 'Favoris' && s.querySelector(`.fw-item[data-id="${id}"]`));
      if (ul.querySelector('.fw-items').hidden) ul.querySelector('.fw-sec-head').click();
    }""", fid)


def star(page, fid, sec=None):
    scope = f'.fw-sec[data-cat="{sec}"] ' if sec else ".fw-sec:not([data-cat='Favoris']) "
    return page.locator(f'{scope}.fw-star[data-id="{fid}"]')


def favoris(page):
    return page.eval_on_selector_all('.fw-sec[data-cat="Favoris"] .fw-item', "els => els.map((e) => e.dataset.id)")


def test_etoile_et_section(page):
    page.goto(page.base + "index.html")
    open_with(page, "sloop")
    assert favoris(page) == []
    star(page, "sloop").scroll_into_view_if_needed()
    y0 = star(page, "sloop").bounding_box()["y"]
    star(page, "sloop").click()
    assert favoris(page) == ["sloop"]
    # la ligne touchée reste sous le doigt, la section Favoris arrive au-dessus
    assert abs(star(page, "sloop").bounding_box()["y"] - y0) <= 2
    assert star(page, "sloop").get_attribute("aria-pressed") == "true"
    assert star(page, "sloop", "Favoris").get_attribute("aria-pressed") == "true"
    assert page.eval_on_selector("#fw-sections", "s => s.querySelector('.fw-sec').dataset.cat") == "Favoris"
    # l'étoile ne choisit pas le firmware
    assert page.is_visible("#fw-sheet") and page.inner_text("#fw-name") == "FM-1+VA"


def test_ordre_et_memoire(page):
    page.goto(page.base + "index.html")
    open_with(page, "sloop")
    star(page, "sloop").click()
    page.keyboard.press("Escape")
    open_with(page, "chipbox")
    star(page, "chipbox").click()
    page.reload()
    page.click("#fw-picker")
    assert favoris(page) == ["sloop", "chipbox"]
    star(page, "sloop", "Favoris").click()
    assert favoris(page) == ["chipbox"]
    star(page, "chipbox", "Favoris").click()
    assert page.locator('.fw-sec[data-cat="Favoris"]').count() == 0


def test_repliable(page):
    page.goto(page.base + "index.html")
    open_with(page, "sloop")
    star(page, "sloop").click()
    head = page.locator('.fw-sec-head[data-cat="Favoris"]')
    assert head.get_attribute("aria-expanded") == "true"
    head.click()
    assert head.get_attribute("aria-expanded") == "false"
    assert not page.is_visible('.fw-sec[data-cat="Favoris"] .fw-item')


def test_dans_la_recherche(page):
    page.goto(page.base + "index.html")
    page.click("#fw-picker")
    page.fill("#fw-search", "sloop")
    s = page.locator('#fw-results .fw-star[data-id="sloop"]')
    s.click()
    assert s.get_attribute("aria-pressed") == "true"
    page.click("#fw-clear")
    assert favoris(page) == ["sloop"]
