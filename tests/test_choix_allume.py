"""Choisir un firmware, FM-1 éteint, l'allume et le lance sans passer par « Allumer »."""


def test_choix_allume_et_lance(page):
    page.set_default_timeout(30000)
    page.goto(page.base + "index.html")
    page.click("#fw-picker")
    page.wait_for_selector(".fw-item", state="attached")
    page.fill("#fw-search", "felucca")
    page.locator(".fw-item[data-id=\"felucca\"]:visible").first.click()
    page.wait_for_function("document.getElementById('power').getAttribute('aria-checked') === 'true'", timeout=30000)
    page.wait_for_function("window.__engine && window.__engine().kind !== 'va'", timeout=30000)
    assert page.is_hidden("#start")
    assert page.inner_text("#fw-picker").lower().find("felucca") >= 0


def test_panneau_se_ferme_et_chargement_disparait(page):
    page.set_default_timeout(30000)
    page.goto(page.base + "index.html")
    page.click("#fw-picker")
    page.wait_for_selector(".fw-item", state="attached")
    page.fill("#fw-search", "felucca")
    page.locator('.fw-item[data-id="felucca"]:visible').first.click()
    assert page.evaluate("document.getElementById('fw-sheet').hidden && document.getElementById('fw-picker').getAttribute('aria-expanded') === 'false'")
    page.wait_for_function("window.__engine && window.__engine().kind !== 'va'")
    page.wait_for_function("document.getElementById('loading').hidden")
