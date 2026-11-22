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


# ---------------------------------------------------------------- le moteur audio
def load_tone(page, hz=440, seconds=2.0, decay=0.0, amp=0.5):
    """Un sample de test : un sinus (qui décroît si decay), chargé dans le moteur."""
    page.evaluate(f"""() => {{ const r = 44100, n = Math.round({seconds} * r), x = new Float32Array(n);
      for (let i = 0; i < n; i++) x[i] = {amp} * Math.sin(2 * Math.PI * {hz} * i / r) * Math.exp(-{decay} * i / r);
      window.__engine().load({{ ch: [x], rate: r }}); }}""")


def rms_out(page):
    return page.evaluate("() => { const a = window.__engine().an, d = new Float32Array(a.fftSize); a.getFloatTimeDomainData(d); return Math.sqrt(d.reduce((s, x) => s + x * x, 0) / d.length); }")


def on_with(page, **tone):
    open_sample(page)
    power_sample(page)
    load_tone(page, **tone)


def test_lecture_et_master(page):
    on_with(page)
    page.evaluate("window.__engine().play(true)")
    page.wait_for_timeout(300)
    assert rms_out(page) > 0.05
    page.evaluate("window.__engine().send({ t: 'master', v: 0 })")
    page.wait_for_timeout(200)
    assert rms_out(page) < 0.001


def test_cut(page):
    on_with(page)
    page.evaluate("window.__engine().play(true)")
    page.wait_for_timeout(200)
    page.evaluate("window.__engine().send({ t: 'cut', on: true })")
    page.wait_for_timeout(150)
    assert rms_out(page) < 0.001
    page.evaluate("window.__engine().send({ t: 'cut', on: false })")
    page.wait_for_timeout(150)
    assert rms_out(page) > 0.05


def test_filtre(page):
    on_with(page, hz=4000)
    page.evaluate("window.__engine().play(true)")
    page.wait_for_timeout(300)
    open_level = rms_out(page)
    page.evaluate("window.__engine().send({ t: 'filter', x: 0.05, y: 0 })")
    page.wait_for_timeout(300)
    assert rms_out(page) < 0.3 * open_level, open_level


def test_scratch_tient_la_position(page):
    on_with(page)
    page.evaluate("window.__engine().play(true)")
    page.wait_for_timeout(200)
    page.evaluate("window.__hold = setInterval(() => window.__engine().send({ t: 'scratch', pos: 0.5 }), 16)")
    page.wait_for_timeout(300)
    a = page.evaluate("window.__engine().pos.beats")
    page.wait_for_timeout(200)
    b = page.evaluate("window.__engine().pos.beats")
    assert abs(a - 1) < 0.02 and abs(b - a) < 0.01, (a, b)          # 0,5 s d'un sample de 2 s sur une mesure : le temps 1
    page.evaluate("clearInterval(window.__hold); window.__engine().send({ t: 'scratch', pos: null })")
    page.wait_for_timeout(500)
    assert abs(page.evaluate("window.__engine().pos.beats") - a) > 0.2


def test_roll(page):
    on_with(page, decay=30)
    hits = page.evaluate("""() => new Promise((ok) => { const e = window.__engine(), a = e.ac.createAnalyser(); a.fftSize = 256; e.node.connect(a);
      const d = new Float32Array(256); let n = 0, was = false;
      e.send({ t: 'roll', i: 0, on: true });
      const iv = setInterval(() => { a.getFloatTimeDomainData(d); const r = Math.sqrt(d.reduce((s, x) => s + x * x, 0) / 256);
        const up = r > 0.1; if (up && !was) n++; was = up; }, 4);
      setTimeout(() => { clearInterval(iv); e.send({ t: 'roll', i: 0, on: false }); ok(n); }, 1000); })""")
    assert 7 <= hits <= 9, hits


# ---------------------------------------------------------------- le cadre B du Duo
def open_duo_with(page, b=None, w=1600, h=900):
    """Le Duo ; b = 'sample' : le module déjà gardé dans FM1-B."""
    page.set_viewport_size({"width": w, "height": h})
    page.goto(page.base + "index.html")
    page.evaluate(f"localStorage.setItem('fm1.duo.b', '{b}')" if b else "localStorage.removeItem('fm1.duo.b')")
    page.goto(page.base + "index.html?duo")
    page.wait_for_function("window.__duo && window.__duo.frames.a.contentWindow.__fw")
    if b == "sample":
        page.wait_for_function("window.__duo.frames.b.contentWindow.__sample")
    else:
        page.wait_for_function("window.__duo.frames.b.contentWindow.__fw")
    return page.frame(name="a"), page.frame(name="b")


def frame_b_url(page):
    return page.evaluate("window.__duo.frames.b.contentWindow.location.href")


def test_choisir_le_module_dans_b(page):
    a, b = open_duo_with(page)
    b.click("#fw-picker")
    b.wait_for_selector("#fw-sections .fw-item[data-id='sample']")
    b.click("#fw-sections .fw-item[data-id='sample']")
    page.wait_for_function("window.__duo.frames.b.contentWindow.location.pathname.endsWith('sample.html') && window.__duo.frames.b.contentWindow.__sample")
    assert page.evaluate("localStorage.getItem('fm1.duo.b')") == "sample"
    assert "fm1=b" in frame_b_url(page)


def test_revenir_a_un_fm1(page):
    a, b = open_duo_with(page, "sample")
    page.frame(name="b").click("#fw-picker")
    page.wait_for_function("window.__duo.frames.b.contentWindow.__fw && !window.__duo.frames.b.contentWindow.document.getElementById('fw-sheet').hidden")
    assert "choisir" in frame_b_url(page) and "sample.html" not in frame_b_url(page)
    assert page.evaluate("localStorage.getItem('fm1.duo.b')") == "fm1"


def test_module_garde_au_rechargement(page):
    open_duo_with(page, "sample")
    assert "sample.html" in frame_b_url(page)


def test_pas_de_section_modules_ailleurs(page):
    page.goto(page.base + "index.html")
    page.click("#fw-picker")
    page.wait_for_selector("#fw-sections .fw-item")
    assert page.locator("#fw-sections .fw-item[data-id='sample']").count() == 0
    a, b = open_duo_with(page)
    a.click("#fw-picker")
    a.wait_for_selector("#fw-sections .fw-item")
    assert a.locator("#fw-sections .fw-item[data-id='sample']").count() == 0


def test_allow_micro(page):
    open_duo_with(page)
    for k in ("a", "b"):
        assert "microphone" in page.get_attribute(f"iframe[name={k}]", "allow")

