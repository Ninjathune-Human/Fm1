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



# ---------------------------------------------------------------- l'horloge du tempo lié
def duo_ready(page, bpm=None):
    """Le Duo, FM1-A (FM-1+VA) et le module allumés, un sample dans le module ; le tempo lié si bpm."""
    a, b = open_duo_with(page, "sample")
    a.evaluate("document.getElementById('go').click()")
    a.wait_for_function("window.__fw.on && !window.__fw.splash", timeout=20000)
    b.evaluate("document.getElementById('go').click()")
    b.wait_for_function("window.__sample.on")
    load_tone(b)
    if bpm:
        page.click(".duo-link")
        page.fill(".duo-bpm input", str(bpm))
        page.dispatch_event(".duo-bpm input", "change")
        page.wait_for_function("window.__duo.linked")
    return a, b


def tap(fr, sel):
    fr.dispatch_event(sel, "pointerdown", {"pointerId": 7, "isPrimary": True})
    fr.dispatch_event(sel, "pointerup", {"pointerId": 7, "isPrimary": True})


def test_play_lance_les_deux(page):
    a, b = duo_ready(page, 150)
    tap(b, "[data-label='PLAY']")
    page.wait_for_function("window.__duo.playing && window.__duo.frames.b.contentWindow.__engine().playing", timeout=5000)
    assert b.evaluate("window.__engine().playLight()") == "green"
    tap(b, "[data-label='PLAY']")
    page.wait_for_function("!window.__duo.playing && !window.__duo.frames.b.contentWindow.__engine().playing", timeout=5000)


def test_boucle_en_phase(page):
    a, b = duo_ready(page, 240)
    tap(b, "[data-label='PLAY']")
    page.wait_for_function("window.__duo.frames.b.contentWindow.__engine().playing", timeout=5000)
    page.wait_for_timeout(8 * 4 * 250)                                  # 8 mesures à 240
    err = b.evaluate("""() => { const S = window.__sample, L = S.loopLength(), c = S.clock.beats(performance.now()) % L, l = S.loopBeats();
      let d = Math.abs(c - l); return Math.min(d, L - d); }""")
    assert err < 0.05, err


def test_tempo_change_et_delie(page):
    a, b = duo_ready(page, 120)
    tap(b, "[data-label='PLAY']")
    page.wait_for_function("window.__duo.frames.b.contentWindow.__engine().playing", timeout=5000)
    page.fill(".duo-bpm input", "180")
    page.dispatch_event(".duo-bpm input", "change")
    page.wait_for_timeout(700)
    assert abs(b.evaluate("window.__engine().pos.bpm") - 180) <= 2
    page.click(".duo-link")                                             # délié : le Duo arrête les deux, comme pour deux FM-1
    page.wait_for_function("!window.__duo.linked && !window.__duo.frames.b.contentWindow.__engine().playing", timeout=5000)
    tap(b, "[data-label='PLAY']")                                       # puis le module joue seul, à son tempo
    page.wait_for_timeout(500)
    assert b.evaluate("window.__engine().playing") is True
    assert abs(b.evaluate("window.__engine().pos.bpm") - b.evaluate("window.__sample.bpm")) < 0.5


def test_seul_avec_son_tempo(page):
    on_with(page)
    page.evaluate("window.__sample.bpm = 96")
    tap(page, "[data-label='PLAY']")
    page.wait_for_timeout(400)
    assert page.evaluate("window.__engine().playing") is True
    assert abs(page.evaluate("window.__engine().pos.bpm") - 96) < 0.5


# ---------------------------------------------------------------- la capture et la mémoire des samples
def wav(path, seconds, hz=220, rate=44100):
    import math, struct, wave
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes(b"".join(struct.pack("<h", int(12000 * math.sin(2 * math.pi * hz * i / rate))) for i in range(int(seconds * rate))))
    return str(path)


def import_wav(page, path):
    page.set_input_files("#sample-file", path)
    page.wait_for_function("window.__sample.lastImport && window.__sample.lastImport.done")
    return page.evaluate("window.__sample.lastImport.error || null")


RMS_OF = "(s) => { const x = s.ch[0]; let q = 0; for (let i = 0; i < x.length; i++) q += x[i] * x[i]; return Math.sqrt(q / x.length); }"
SPY_GUM = """window.__gum = []; const g = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
  navigator.mediaDevices.getUserMedia = (c) => { window.__gum.push(c); return g(c); };"""


def test_capture_micro(page):
    page.add_init_script(SPY_GUM)
    open_sample(page); power_sample(page)
    page.evaluate("window.__sample.capt.thresh = null")
    level = page.evaluate(f"async () => {{ const s = await window.__sample.capture('mic', {{ seconds: 1 }}); return [s.slices.length, ({RMS_OF})(s)]; }}")
    assert level[0] == 17 and level[1] > 0.001, level
    c = page.evaluate("window.__gum[0].audio")
    assert c["echoCancellation"] is False and c["noiseSuppression"] is False and c["autoGainControl"] is False


def test_mic_refuse(page, tmp_path):
    page.add_init_script("navigator.mediaDevices.getUserMedia = () => Promise.reject(new DOMException('refusé', 'NotAllowedError'))")
    open_sample(page); power_sample(page)
    assert page.evaluate("window.__sample.capture('mic', { seconds: 0.3 }).then(() => 'ok', () => 'refus')") == "refus"
    assert isinstance(page.evaluate("window.__sample.sources().mic"), str)
    assert import_wav(page, wav(tmp_path / "a.wav", 1)) is None             # les autres sources restent
    assert page.evaluate("window.__sample.samples.length") == 1


def test_capture_fm1(page):
    page.add_init_script(SPY_GUM)
    a, b = duo_ready(page)
    a.evaluate("window.__host.keyDown(7, 't')")
    level = b.evaluate(f"async () => {{ window.__sample.capt.thresh = null; const s = await window.__sample.capture('fm1', {{ seconds: 1 }}); return ({RMS_OF})(s); }}")
    a.evaluate("window.__host.keyUp('t')")
    assert level > 0.01, level
    assert b.evaluate("window.__gum.length") == 0


def test_capture_fm1_interrompue(page):
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    a, b = duo_ready(page)
    a.evaluate("window.__host.keyDown(7, 't')")
    got = b.evaluate("""() => { window.__sample.capt.thresh = null; const p = window.__sample.capture('fm1', { seconds: 4 });
      setTimeout(() => window.__duo_a_off(), 600); return p.then((s) => s ? s.ch[0].length : -1, (e) => 'rejet ' + e); }""".replace(
        "window.__duo_a_off()", "parent.__duo.frames.a.contentWindow.document.getElementById('power').click()"))
    assert isinstance(got, int) and 0 < got < 4 * 48000, got
    assert errors == []


def test_fichier(page, tmp_path):
    open_sample(page); power_sample(page)
    assert import_wav(page, wav(tmp_path / "boucle.wav", 4)) is None
    s = page.evaluate("(() => { const s = window.__sample.samples[window.__sample.cur]; return [s.bars, s.fit, s.slices.length]; })()")
    assert s[0] == 2 and abs(s[1] - 1) < 1e-6 and s[2] == 17


def test_fichier_court_et_long(page, tmp_path):
    open_sample(page); power_sample(page)
    import_wav(page, wav(tmp_path / "court.wav", 0.05))
    assert page.evaluate("window.__sample.samples[window.__sample.cur].bars") is None
    import_wav(page, wav(tmp_path / "long.wav", 20))
    s = page.evaluate("window.__sample.samples[window.__sample.cur]")
    assert abs(len(s["ch"][0]) / s["rate"] - 16) < 0.01
    assert "16 s" in page.evaluate("window.__sample.note")


def test_rec_pad(page, tmp_path):
    open_sample(page); power_sample(page)
    import_wav(page, wav(tmp_path / "base.wav", 2))
    before = page.evaluate("window.__sample.samples[0].ch[0].length")
    page.evaluate("window.__sample.capt.thresh = null")
    page.dispatch_event("[data-pad='3']", "pointerdown", {"pointerId": 3, "isPrimary": True})
    tap(page, "[data-label='REC']")
    page.wait_for_timeout(800)
    tap(page, "[data-label='REC']")
    page.dispatch_event("[data-pad='3']", "pointerup", {"pointerId": 3, "isPrimary": True})
    page.wait_for_function("window.__sample.samples[0].pads[3] !== null", timeout=5000)
    assert page.evaluate("window.__sample.samples.length") == 1
    assert page.evaluate("window.__sample.samples[0].ch[0].length") == before


def test_samples_gardes(page, tmp_path):
    open_sample(page); power_sample(page)
    import_wav(page, wav(tmp_path / "un.wav", 1)); import_wav(page, wav(tmp_path / "deux.wav", 2))
    page.click("#power")
    page.reload()
    page.wait_for_function("window.__sample && window.__sample.samples.length === 2")
    assert page.evaluate("window.__sample.samples[window.__sample.cur].id") == "S02"


def test_tab_selon_navigateur(page):
    page.add_init_script("delete MediaDevices.prototype.getDisplayMedia")
    open_sample(page)
    assert page.evaluate("window.__sample.sources().tab") is False
