"""Le module sample et scratch (sample.html) : son panneau, son son, le Duo, la capture, l'écran, les gestes, l'envoi."""


def open_sample(page, path="sample.html"):
    page.goto(page.base + path)
    page.wait_for_selector("#panel [data-label='REC']")


def power_sample(page):
    page.click("#go")
    page.wait_for_function("window.__sample.on && window.__sample.page === 'edit'")


def test_panneau(page):
    open_sample(page)
    assert page.locator("#panel .cap").count() == 4
    assert page.locator("#panel [data-knob]").count() == 2
    assert page.locator("#panel .key[data-pad]").count() == 16
    assert page.is_visible("#platter") and page.is_visible("#xy")
    # l'image LCD de 440 x 240, tracée trois fois plus fine (comme l'écran du FM-1, 240 sur 720)
    assert page.evaluate("(() => { const c = document.getElementById('screen'); return [c.width / 3, c.height / 3]; })()") == [440, 240]
    assert page.locator(".deck .skins .swatch").count() == 6
    assert "Module sample" in page.inner_text("#fw-picker")


def test_langue_et_coloris(page):
    page.add_init_script("localStorage.setItem('fm1.lang', 'en')")
    open_sample(page)
    assert "Sample module" in page.inner_text("#fw-picker")
    page.click(".deck .skins .swatch >> nth=3")
    assert page.evaluate("window.__sample.skin") == "navy"


def test_allumer(page):
    open_sample(page)
    power_sample(page)
    assert page.get_attribute("#power", "aria-checked") == "true"
