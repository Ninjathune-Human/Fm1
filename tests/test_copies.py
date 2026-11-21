"""Copies nommées de la mémoire d'un firmware (natif et émulé) : enregistrer, charger, exporter, importer, supprimer."""
import pytest
from conftest import power_on
from test_emu import use


def ouvre(page):
    page.click("#cp-btn")
    page.wait_for_selector("#cp-pop", state="visible")


@pytest.mark.parametrize("fw", ["felucca", "sloop"])
def test_copies(page, fw, tmp_path):
    page.on("dialog", lambda d: d.accept())
    power_on(page)
    page.set_default_timeout(30000)
    assert use(page, fw) is True
    page.wait_for_timeout(2000)
    assert page.is_visible("#cp-btn")
    ouvre(page)
    assert page.locator("#cp-load").is_disabled()
    page.fill("#cp-name", "Essai")
    page.click("#cp-save")
    page.wait_for_function("document.querySelectorAll('#cp-sel option').length === 2")
    assert "Essai" in page.text_content("#cp-sel")
    # exporter, supprimer, réimporter
    page.select_option("#cp-sel", "Essai")
    with page.expect_download() as dl:
        page.click("#cp-exp")
    f = tmp_path / "c.json"; dl.value.save_as(f)
    page.click("#cp-del")
    page.wait_for_function("document.querySelectorAll('#cp-sel option').length === 1")
    page.set_input_files("#cp-imp", str(f))
    page.wait_for_function("document.querySelectorAll('#cp-sel option').length === 2")
    # charger : le firmware redémarre
    page.select_option("#cp-sel", "Essai")
    page.click("#cp-load")
    page.wait_for_function("document.querySelector('#cp-pop').hidden", timeout=30000)
    page.wait_for_timeout(1500)
    assert page.evaluate("window.__engine().kind") in ("natif", "emu")
    assert page.is_visible("#cp-btn")


def test_memoire_avec_fm1va(page, tmp_path):
    """FM-1+VA n'a pas de copies : le bouton Mémoire reste, avec la sauvegarde et Importer… seuls."""
    power_on(page)
    assert page.inner_text("#cp-btn") == "Mémoire"
    ouvre(page)
    assert not page.is_visible("#cp-copies") and not page.is_visible("#cp-exp")
    assert page.is_visible("#backup-export") and page.is_visible("label[for=cp-imp]")
    # « Importer… » s'écrit comme les autres boutons, pas comme les intitulés en capitales
    assert page.eval_on_selector("label[for=cp-imp]", "l => getComputedStyle(l).textTransform") == "none"
    # une copie d'un autre firmware : il faut d'abord le choisir
    f = tmp_path / "c.json"
    f.write_text('{"format": "fm1-copie", "version": 1, "id": "sloop", "nom": "Essai", "kind": "emu", "sectors": []}')
    page.set_input_files("#cp-imp", str(f))
    page.wait_for_function("document.getElementById('cp-msg').textContent.includes('choisissez ce firmware')")
    # ni une copie ni une sauvegarde
    f.write_text('{"format": "autre"}')
    page.set_input_files("#cp-imp", str(f))
    page.wait_for_function("document.getElementById('cp-msg').textContent.includes('ni une copie ni une sauvegarde')")


def test_memoire_meme_place_en_duo(page):
    """Le bouton Mémoire est là en Solo comme dans chaque FM-1 du Duo, juste avant l'interrupteur."""
    page.goto(page.base + "index.html")
    assert page.eval_on_selector("#cp-box", "b => b.nextElementSibling.id") == "power"
    assert page.is_visible("#cp-btn")
    page.goto(page.base + "index.html?duo")
    page.wait_for_function("window.__duo && window.__duo.frames.a.contentWindow.__fw")
    assert page.frame(name="a").is_visible("#cp-btn")
