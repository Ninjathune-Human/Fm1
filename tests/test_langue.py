# La bascule FR/EN : le bouton, le manuel, les raccourcis, la fiche d'un firmware natif, le choix gardé.
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_bascule_en_fr(page):
    page.goto(page.base + "index.html")
    assert page.inner_text("#aide-manuel summary") == "Manuel d'utilisation"
    page.click(".mast .lang [data-l=en]")
    page.wait_for_function("document.querySelector('#aide-manuel summary').textContent === 'User manual'")
    assert page.inner_text("#aide-clavier summary") == "Keyboard shortcuts"
    assert page.inner_text("#go") == "Power on"
    assert page.get_attribute("html", "lang") == "en"
    assert page.get_attribute(".mast .lang [data-l=en]", "aria-checked") == "true"
    assert page.get_attribute(".mast .lang [data-l=fr]", "aria-checked") == "false"
    # le choix est gardé
    page.reload()
    page.wait_for_function("document.querySelector('#aide-manuel summary').textContent === 'User manual'")
    # le manuel : un paragraphe à lien, la légende, une note du clavier dessiné
    page.click("#aide-manuel summary")
    assert "Power on, on the FM-1" in page.inner_text("#aide-manuel")
    assert page.locator("#aide-manuel dd a").count() >= 3
    assert "Buttons" in page.text_content(".legende") and "Knobs" in page.text_content(".legende")
    assert "C 4" in page.text_content("#clavier")
    # retour au français
    page.click(".mast .lang [data-l=fr]")
    page.wait_for_function("document.querySelector('#aide-manuel summary').textContent === \"Manuel d'utilisation\"")
    assert page.inner_text("#go") == "Allumer"
    assert "Do 4" in page.text_content("#clavier")
    assert page.get_attribute(".mast .lang [data-l=fr]", "aria-checked") == "true"


def test_fiche_anglaise(page):
    page.goto(page.base + "index.html")
    page.click(".mast .lang [data-l=en]")
    page.wait_for_function("document.documentElement.lang === 'en'")
    page.click("#aide-fiche summary")
    page.wait_for_function("document.querySelector('#fiche h3')")
    assert page.inner_text("#fiche h3") == "Controls"
    fr = json.load(open(os.path.join(ROOT, "firmwares/fiches/fm1va.json"), encoding="utf8"))["resume"]
    assert page.inner_text("#fiche p") != fr


def test_status_dynamique(page):
    page.goto(page.base + "index.html")
    page.click(".mast .lang [data-l=en]")
    page.wait_for_function("document.documentElement.lang === 'en'")
    page.evaluate("document.getElementById('status').textContent = 'Démarrage de Melodee…'")
    page.wait_for_function("document.getElementById('status').textContent === 'Starting Melodee…'")
