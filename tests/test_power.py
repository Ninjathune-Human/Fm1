"""L'interrupteur marche / arrêt : il allume le FM-1, et l'éteindre efface les réglages du firmware actif."""


def checked(page):
    return page.get_attribute("#power", "aria-checked")


def test_interrupteur_allume(page):
    page.goto(page.base + "index.html")
    assert checked(page) == "false"
    page.click("#power")
    page.wait_for_function("document.getElementById('status').textContent.startsWith('Allumé')", timeout=20000)
    assert checked(page) == "true"
    assert page.is_hidden("#start")


def test_eteindre_efface_les_reglages(page):
    page.goto(page.base + "index.html")
    page.click("#power")
    page.wait_for_function("document.getElementById('status').textContent.startsWith('Allumé')", timeout=20000)
    page.evaluate("localStorage.setItem('fm1va.essai', '1'); localStorage.setItem('fm1.firmware', JSON.stringify({ id: 'fm1va', nom: 'FM-1+VA' }))")
    with page.expect_navigation():
        page.click("#power")
    assert page.evaluate("localStorage.getItem('fm1va.essai')") is None
    assert page.evaluate("localStorage.getItem('fm1.firmware')") is not None   # le choix du firmware reste
    assert checked(page) == "false"
    assert page.is_visible("#start")
    assert page.text_content("#status").startswith("Éteint")


def test_plus_de_bouton_reglages_usine(page):
    page.goto(page.base + "index.html")
    assert page.query_selector("#reset") is None
