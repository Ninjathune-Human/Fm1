"""Sélecteur de firmwares."""
import os

from conftest import ROOT, lit_pixels, power_on

SHOTS = os.path.join(ROOT, "test-results")


def status(page):
    return page.inner_text("#status")


def wait_status(page, text, timeout=30000):
    page.wait_for_function("(t) => document.getElementById('status').textContent === t", arg=text, timeout=timeout)


def click_row(page, fid):
    page.evaluate("(id) => document.querySelector(`.fw-item[data-id=\"${id}\"]`).click()", fid)


def notch_transform(page, sel):
    return page.evaluate("(s) => getComputedStyle(document.querySelector(s)).transform", sel)


def test_open_close(page):
    page.goto(page.base + "index.html")
    closed = notch_transform(page, "#fw-picker .notch")
    page.click("#fw-picker")
    assert page.is_visible("#fw-sheet")
    assert page.get_attribute("#fw-picker", "aria-expanded") == "true"
    page.wait_for_timeout(300)
    assert notch_transform(page, "#fw-picker .notch") != closed
    page.keyboard.press("Escape")
    assert not page.is_visible("#fw-sheet")
    assert page.get_attribute("#fw-picker", "aria-expanded") == "false"


def test_search(page):
    page.goto(page.base + "index.html")
    page.click("#fw-picker")
    page.fill("#fw-search", "sloop")
    texts = page.eval_on_selector_all("#fw-results .fw-item", "els => els.map((e) => e.textContent.toLowerCase())")
    # les correspondances directes passent avant celles admises par tolérance aux fautes (« loop »)
    has = ["sloop" in t for t in texts]
    assert texts and has[0] and has == sorted(has, reverse=True)
    page.fill("#fw-search", "bubba")
    assert "bubba machine" not in page.inner_text("#fw-sheet").lower()
    page.fill("#fw-search", "sloop zzzzqq")
    assert page.is_visible("text=Résultats approchants")
    page.click("#fw-clear")
    assert page.input_value("#fw-search") == ""
    assert page.is_visible(".fw-sec-head")
    page.fill("#fw-search", "chipb")
    page.keyboard.press("Escape")
    assert page.input_value("#fw-search") == ""
    assert page.is_visible("#fw-sheet")


def test_pick(page):
    power_on(page)
    click_row(page, "sloop")
    assert status(page) == "Démarrage de SLOOP…"
    wait_status(page, "SLOOP")
    assert page.inner_text("#fw-name") == "SLOOP"
    assert not page.is_visible("#fw-sheet")


def test_enter_picks_first(page):
    power_on(page)
    page.click("#fw-picker")
    page.fill("#fw-search", "chipbox")
    page.keyboard.press("Enter")
    assert not page.is_visible("#fw-sheet")
    wait_status(page, "Chipbox")


def test_last_wins(page):
    power_on(page)
    page.evaluate("""() => { document.querySelector('.fw-item[data-id="x0x"]').click();
      setTimeout(() => document.querySelector('.fw-item[data-id="zp12"]').click(), 30); }""")
    wait_status(page, "zp12", timeout=60000)
    page.wait_for_timeout(500)
    assert page.evaluate("window.__engine().name") == "zp12"
    assert page.evaluate("window.__nodes().length") == 1


def test_restore_last(page):
    power_on(page)
    click_row(page, "zp12")
    wait_status(page, "zp12")
    page.reload()
    assert page.inner_text("#fw-name") == "zp12"
    page.click("#go")
    wait_status(page, "zp12")
    assert page.evaluate("window.__engine().name") == "zp12"


def test_sections_fold(page):
    page.goto(page.base + "index.html")
    page.click("#fw-picker")
    head = '.fw-sec-head[data-cat="Synthé"]'
    before = page.get_attribute(head, "aria-expanded")
    notch = notch_transform(page, head + " .notch")
    page.click(head)
    page.wait_for_timeout(300)
    assert page.get_attribute(head, "aria-expanded") != before
    assert notch_transform(page, head + " .notch") != notch
    expanded = page.get_attribute(head, "aria-expanded") == "true"
    assert page.is_visible('.fw-sec[data-cat="Synthé"] .fw-items') == expanded


def test_layouts(browser, base_url):
    os.makedirs(SHOTS, exist_ok=True)
    for w, h in [(390, 844), (820, 1180), (1440, 900)]:
        ctx = browser.new_context(viewport={"width": w, "height": h}, has_touch=w < 1000)
        pg = ctx.new_page()
        pg.goto(base_url + "index.html")
        pg.click("#fw-picker")
        pg.wait_for_timeout(400)
        sheet = pg.eval_on_selector("#fw-sheet", "e => e.getBoundingClientRect().toJSON()")
        picker = pg.eval_on_selector("#fw-picker", "e => e.getBoundingClientRect().toJSON()")
        # la liste tient dans la fenêtre : son pied « Ouvrir un .fwsc… » reste visible sans faire défiler la page
        assert sheet["bottom"] <= h + 1, (w, sheet)
        if w < 700:
            assert abs(sheet["bottom"] - h) <= 1, sheet
        else:
            assert sheet["top"] >= picker["bottom"] - 1, (sheet, picker)
        assert sheet["left"] >= 0 and sheet["right"] <= w
        pg.screenshot(path=os.path.join(SHOTS, f"selecteur-{w}.png"))
        ctx.close()


def test_contextual_controls(page):
    power_on(page)
    assert page.is_visible(".file")
    click_row(page, "sloop")
    wait_status(page, "SLOOP")
    assert not page.is_visible(".file")
    click_row(page, "fm1va")
    wait_status(page, "FM-1+VA")
    assert page.is_visible(".file")


def test_open_local(page):
    power_on(page)
    n = page.evaluate("window.__catalogue.length")
    page.set_input_files("#fw-file", os.path.join(ROOT, "firmwares", "felucca.fwsc"))
    wait_status(page, "felucca")
    assert page.inner_text("#fw-name") == "felucca"
    page.wait_for_timeout(3000)
    assert lit_pixels(page) >= 2000
    assert page.evaluate("window.__catalogue.length") == n


def test_tag_no_boot(page):
    import json
    cat = json.load(open(os.path.join(ROOT, "firmwares", "catalogue.json")))
    for e in cat["firmwares"]:
        if e["id"] == "x0x":
            e["emulateur_fm1emu"] = "ne démarre pas"
    page.route("**/firmwares/catalogue.json", lambda r: r.fulfill(status=200, body=json.dumps(cat), content_type="application/json"))
    page.goto(page.base + "index.html")
    page.wait_for_selector('.fw-item[data-id="x0x"]', state="attached")
    assert "ne démarre pas" in page.eval_on_selector('.fw-item[data-id="x0x"]', "e => e.textContent")
