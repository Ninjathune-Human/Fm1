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


def test_copies_absentes_avec_fm1va(page):
    power_on(page)
    assert not page.is_visible("#cp-btn")
