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


# ---------------------------------------------------------------- l'écran tactile
def lcd_point(page, x, y):
    """Un point de l'image LCD (440 x 240), en coordonnées de la page."""
    r = page.evaluate("(() => { const b = document.getElementById('screen').getBoundingClientRect(); return [b.left, b.top, b.width, b.height]; })()")
    return r[0] + x / 440 * r[2], r[1] + y / 240 * r[3]


def lcd_touch(page, x, y, pid=1, kind="pointerdown"):
    cx, cy = lcd_point(page, x, y)
    page.dispatch_event("#screen", kind, {"pointerId": pid, "clientX": cx, "clientY": cy, "isPrimary": pid == 1, "pointerType": "touch"})


def lcd_lit(page):
    return page.evaluate("""(() => { const c = document.getElementById('screen'), d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
      let n = 0; for (let i = 0; i < d.length; i += 16) if (d[i] + d[i + 1] + d[i + 2] > 120) n++; return n; })()""")


def with_sample(page, tmp_path, seconds=4):
    open_sample(page); power_sample(page)
    import_wav(page, wav(tmp_path / f"s{seconds}.wav", seconds))


def test_pages(page, tmp_path):
    with_sample(page, tmp_path)
    for cap, want in (("SEND", "send"), ("EDIT", "edit"), ("REC", "capture")):
        tap(page, f"[data-label='{cap}']")
        page.wait_for_function(f"window.__sample.page === '{want}'")
        page.wait_for_timeout(100)
        assert lcd_lit(page) > 300, want
    tap(page, "[data-label='REC']")                                     # (l'arrêt de la capture armée)


def test_colonne_et_select(page, tmp_path):
    with_sample(page, tmp_path)
    lcd_touch(page, 55, 30); lcd_touch(page, 55, 30, kind="pointerup")
    assert page.evaluate("window.__sample.col") == 0
    page.evaluate("window.__sample.turn('SELECT', 3, 0)")
    assert page.evaluate("window.__sample.samples[window.__sample.cur].cols[window.__sample.slice].start") == 3


def test_select_sans_colonne(page, tmp_path):
    with_sample(page, tmp_path, 1)
    import_wav(page, wav(tmp_path / "b.wav", 2))
    page.evaluate("window.__sample.select(0); window.__sample.col = null")
    page.evaluate("window.__sample.turn('SELECT', 1, 0)")
    assert page.evaluate("window.__sample.cur") == 1


def test_poignee(page, tmp_path):
    with_sample(page, tmp_path)
    x = 10 + 420 * 4 / 16
    lcd_touch(page, x, 120); lcd_touch(page, x + 20, 120, kind="pointermove"); lcd_touch(page, x + 20, 120, kind="pointerup")
    assert page.evaluate("window.__sample.slice") == 4
    assert page.evaluate("window.__sample.samples[window.__sample.cur].cols[4].start") > 0


def test_pincer(page, tmp_path):
    with_sample(page, tmp_path)
    lcd_touch(page, 200, 120, 1); lcd_touch(page, 240, 120, 2)
    lcd_touch(page, 120, 120, 1, "pointermove"); lcd_touch(page, 320, 120, 2, "pointermove")
    lcd_touch(page, 120, 120, 1, "pointerup"); lcd_touch(page, 320, 120, 2, "pointerup")
    z = page.evaluate("window.__sample.zoom")
    assert z["to"] - z["from"] < 1


def test_tranche_touchee(page, tmp_path):
    with_sample(page, tmp_path)
    x = 10 + 420 * 8.5 / 16
    lcd_touch(page, x, 150); lcd_touch(page, x, 150, kind="pointerup")
    assert page.evaluate("window.__sample.slice") == 8


def test_puces(page, tmp_path):
    with_sample(page, tmp_path)
    page.evaluate("window.__sample.page = 'capture'")
    with page.expect_file_chooser() as fc:
        x = page.evaluate("window.__sample.chipX('FILE')")
        page.mouse.click(*lcd_point(page, x, 68))                       # (un vrai clic : le navigateur n'ouvre la fenêtre qu'à un geste)
    assert fc.value is not None


# ---------------------------------------------------------------- platine, zone XY et pads
import math

PX, PY = 1336, 272                                       # le centre de la platine (unités du FM-1)
XYR = (914, 572, 652, 341)                               # l'intérieur de la zone XY


def dev_point(page, ux, uy):
    r = page.evaluate("(() => { const b = document.getElementById('panel').getBoundingClientRect(); return [b.left, b.top, b.width, b.height]; })()")
    return r[0] + ux / 1640 * r[2], r[1] + uy / 990 * r[3]


def ptr(page, sel, kind, ux, uy, pid=1, **extra):
    cx, cy = dev_point(page, ux, uy)
    page.dispatch_event(sel, kind, {"pointerId": pid, "clientX": cx, "clientY": cy, "isPrimary": pid == 1, "pointerType": extra.pop("pointerType", "touch"), **extra})


def on_platter(deg, r=150):
    a = math.radians(deg - 90)
    return PX + r * math.cos(a), PY + r * math.sin(a)


def xy_at(nx, ny):
    """Un point de la zone XY : x depuis la gauche, y depuis le bas, de 0 à 1."""
    return XYR[0] + nx * XYR[2], XYR[1] + (1 - ny) * XYR[3]


def spy_sent(page):
    page.evaluate("window.__sent = []; (() => { const e = window.__engine(), s = e.send.bind(e); e.send = (m, t) => { window.__sent.push(m); return s(m, t); }; })()")


def playing_loop(page, tmp_path):
    with_sample(page, tmp_path, 4)
    page.evaluate("window.__engine().play(true)")
    page.wait_for_timeout(300)


def test_scratch(page, tmp_path):
    playing_loop(page, tmp_path)
    ptr(page, "#platter", "pointerdown", *on_platter(0))
    p0 = page.evaluate("window.__sample.touch.pos")
    for d in range(10, 91, 10):
        ptr(page, "#platter", "pointermove", *on_platter(d)); page.wait_for_timeout(20)
    p1 = page.evaluate("window.__sample.touch.pos")
    ptr(page, "#platter", "pointerup", *on_platter(90))
    assert abs((p1 - p0) - 0.45) < 0.05, (p0, p1)


def test_main_posee(page, tmp_path):
    playing_loop(page, tmp_path)
    ptr(page, "#platter", "pointerdown", *on_platter(30))
    page.wait_for_timeout(150)
    a = page.evaluate("window.__engine().pos.beats")
    page.wait_for_timeout(300)
    b = page.evaluate("window.__engine().pos.beats")
    ptr(page, "#platter", "pointerup", *on_platter(30))
    assert abs(b - a) < 0.02, (a, b)


def test_relache_en_phase(page, tmp_path):
    playing_loop(page, tmp_path)
    ptr(page, "#platter", "pointerdown", *on_platter(30))
    page.wait_for_timeout(400)
    ptr(page, "#platter", "pointerup", *on_platter(30))
    page.wait_for_timeout(500)
    beats, loop = page.evaluate("[window.__engine().pos.beats, window.__engine().pos.loop]")
    assert abs(beats - loop) < 0.05, (beats, loop)


def test_lancer_en_arriere(page, tmp_path):
    playing_loop(page, tmp_path)
    ptr(page, "#platter", "pointerdown", *on_platter(90))
    for d in (70, 40, 10):
        ptr(page, "#platter", "pointermove", *on_platter(d)); page.wait_for_timeout(15)
    ptr(page, "#platter", "pointerup", *on_platter(10))
    assert page.evaluate("window.__sample.touch.reverse") is True


def test_cut_deuxieme_doigt(page, tmp_path):
    playing_loop(page, tmp_path)
    ptr(page, "#platter", "pointerdown", *on_platter(0), pid=1)
    ptr(page, "#platter", "pointerdown", *on_platter(180), pid=2)
    assert page.evaluate("window.__sample.touch.cut") is True
    ptr(page, "#platter", "pointerup", *on_platter(180), pid=2)
    assert page.evaluate("window.__sample.touch.cut") is False
    assert page.evaluate("window.__sample.touch.platter") == 1
    ptr(page, "#platter", "pointerup", *on_platter(0), pid=1)


def test_xy_filtre_et_retour(page, tmp_path):
    playing_loop(page, tmp_path)
    ptr(page, "#xy", "pointerdown", *xy_at(0.1, 0.8))
    f = page.evaluate("window.__sample.touch.filter")
    assert abs(f["x"] - 0.1) < 0.02 and abs(f["y"] - 0.8) < 0.02, f
    ptr(page, "#xy", "pointerup", *xy_at(0.1, 0.8))
    page.wait_for_timeout(300)
    assert abs(page.evaluate("window.__sample.touch.filter.x") - 0.5) < 0.01


def test_xy_echo(page, tmp_path):
    playing_loop(page, tmp_path)
    ptr(page, "#xy", "pointerdown", *xy_at(0.25, 0.5), pid=1)
    ptr(page, "#xy", "pointerdown", *xy_at(0.75, 0.5), pid=2)
    assert abs(page.evaluate("window.__sample.touch.echo.amount") - 0.5) < 0.05
    ptr(page, "#xy", "pointerup", *xy_at(0.75, 0.5), pid=2); ptr(page, "#xy", "pointerup", *xy_at(0.25, 0.5), pid=1)


def test_stylet(page, tmp_path):
    playing_loop(page, tmp_path)
    ptr(page, "#xy", "pointerdown", *xy_at(0.1, 0.5), pointerType="pen", pressure=0.3)
    assert abs(page.evaluate("window.__sample.touch.filter.x") - 0.38) < 0.02
    ptr(page, "#xy", "pointermove", *xy_at(0.1, 0.5), pointerType="pen", pressure=0.9)
    assert abs(page.evaluate("window.__sample.touch.filter.x") - 0.14) < 0.02
    ptr(page, "#xy", "pointerup", *xy_at(0.1, 0.5), pointerType="pen", pressure=0)


def test_pad_et_roll(page, tmp_path):
    with_sample(page, tmp_path)
    spy_sent(page)
    tap(page, "[data-pad='4']")
    sent = page.evaluate("window.__sent.filter((m) => m.t === 'pad')")
    assert sent[0] == {"t": "pad", "i": 4, "on": True} and sent[-1] == {"t": "pad", "i": 4, "on": False}
    page.dispatch_event("[data-pad='4']", "pointerdown", {"pointerId": 5, "isPrimary": True})
    page.wait_for_timeout(400)
    assert page.evaluate("window.__sent.some((m) => m.t === 'roll' && m.i === 4 && m.on)")
    page.dispatch_event("[data-pad='4']", "pointerup", {"pointerId": 5, "isPrimary": True})
    assert page.evaluate("window.__sent.filter((m) => m.t === 'roll').pop().on") is False


def test_clavier_et_midi(page, tmp_path):
    with_sample(page, tmp_path)
    spy_sent(page)
    page.keyboard.press("Space")
    page.wait_for_timeout(100)
    assert page.evaluate("window.__engine().playing") is True
    page.evaluate("window.__sample.capt.thresh = null")
    page.keyboard.press("KeyR")
    page.wait_for_function("!!window.__sample.recording")
    page.keyboard.press("KeyR")
    page.evaluate("window.__engine().midiIn(Uint8Array.of(0x90, 36, 100)); window.__engine().midiIn(Uint8Array.of(0x80, 36, 0))")
    pads = page.evaluate("window.__sent.filter((m) => m.t === 'pad' && m.i === 0).map((m) => m.on)")
    assert pads == [True, False]


# ---------------------------------------------------------------- les lumières
I_OF = "(el) => parseFloat(el.style.getPropertyValue('--i') || '0')"


def test_led_des_pads(page, tmp_path):
    with_sample(page, tmp_path)
    page.evaluate("window.__sample.slice = 6")
    page.wait_for_timeout(100)
    rest = page.evaluate(f"({I_OF})(document.querySelector(\"[data-pad='6']\"))")
    assert abs(rest - 0.25) < 0.05, rest
    page.evaluate("window.__engine().play(true)")
    page.wait_for_timeout(700)
    k, cur, prev = page.evaluate(f"""(() => {{ const L = window.__sample.lit, k = L.slice, f = {I_OF};
      return [k, f(document.querySelector(`[data-pad='${{k}}']`)), f(document.querySelector(`[data-pad='${{(k + 15) % 16}}']`))]; }})()""")
    assert cur == 1 and 0 < prev < 1, (k, cur, prev)


def test_couronne(page, tmp_path):
    with_sample(page, tmp_path)
    page.evaluate("window.__engine().play(true)")
    page.wait_for_timeout(500)
    head, brightest = page.evaluate(f"""(() => {{ const d = window.__sample.lit.disc, f = {I_OF}, leds = [...document.querySelectorAll('#platter .led')];
      const head = ((Math.round(d / (2 * Math.PI) * 32) % 32) + 32) % 32; let b = 0; leds.forEach((l, i) => {{ if (f(l) > f(leds[b])) b = i; }});
      return [head, b]; }})()""")
    assert head == brightest, (head, brightest)


def test_play_bat(page, tmp_path):
    with_sample(page, tmp_path)
    page.evaluate("window.__engine().play(true)")
    page.wait_for_timeout(200)
    n = page.evaluate(f"""() => new Promise((ok) => {{ const el = document.querySelector("[data-label='PLAY']"), f = {I_OF}; let n = 0, was = false;
      const iv = setInterval(() => {{ const up = f(el) > 0.9; if (up && !was) n++; was = up; }}, 15);
      setTimeout(() => {{ clearInterval(iv); ok(n); }}, 1000); }})""")
    assert 1 <= n <= 3, n                                               # deux temps par seconde à 120


def test_rec(page, tmp_path):
    with_sample(page, tmp_path)
    page.evaluate("window.__sample.capt.input = -24; window.__sample.capt.thresh = -0.1")   # armé : il attend un son qui ne vient pas
    tap(page, "[data-label='REC']")
    page.wait_for_function("!!window.__sample.recording")
    seen = page.evaluate(f"""() => new Promise((ok) => {{ const el = document.querySelector("[data-label='REC']"), f = {I_OF}, s = new Set();
      const iv = setInterval(() => s.add(f(el) > 0.5), 30); setTimeout(() => {{ clearInterval(iv); ok([...s]); }}, 1000); }})""")
    assert sorted(seen) == [False, True]
    tap(page, "[data-label='REC']")
    page.wait_for_function("!window.__sample.recording")
    page.evaluate("window.__sample.capt.input = 0; window.__sample.capt.thresh = null")
    tap(page, "[data-label='REC']")
    page.wait_for_function("window.__sample.recording && window.__sample.recording.started()")
    page.wait_for_timeout(100)
    assert page.evaluate(f"({I_OF})(document.querySelector(\"[data-label='REC']\"))") == 1
    tap(page, "[data-label='REC']")


def test_point_xy(page, tmp_path):
    with_sample(page, tmp_path)
    count = "document.querySelectorAll('#xy-pts .pt').length"
    ptr(page, "#xy", "pointerdown", *xy_at(0.3, 0.3), pid=1)
    page.wait_for_timeout(60)
    assert page.evaluate(count) == 1
    ptr(page, "#xy", "pointerdown", *xy_at(0.7, 0.6), pid=2)
    page.wait_for_timeout(60)
    assert page.evaluate(count) == 2
    ptr(page, "#xy", "pointerup", *xy_at(0.7, 0.6), pid=2); ptr(page, "#xy", "pointerup", *xy_at(0.3, 0.3), pid=1)
    page.wait_for_timeout(60)
    assert page.evaluate(count) == 0


# ---------------------------------------------------------------- l'envoi
def send_key(fr):
    tap(fr, "[data-label='SEND']")


def test_cibles_selon_fm1a(page):
    a, b = open_duo_with(page, "sample")
    b.evaluate("document.getElementById('go').click()")
    b.wait_for_function("window.__sample.on")
    assert b.evaluate("window.__sample.targets()") == ["file", "erase"]          # FM1-A éteint
    a.evaluate("document.getElementById('go').click()")
    a.wait_for_function("window.__fw.on && !window.__fw.splash", timeout=20000)
    assert b.evaluate("window.__sample.targets()") == ["file", "erase"]          # FM-1+VA ne prend pas d'échantillons


def sent_to(page, tmp_path, fid):
    from test_natif import _natif
    from test_emu import use
    _natif(fid)
    a, b = open_duo_with(page, "sample")
    a.evaluate("document.getElementById('go').click()")
    a.wait_for_function("window.__fw.on && !window.__fw.splash", timeout=20000)
    page.set_default_timeout(30000)
    assert use(a, fid) is True
    a.wait_for_timeout(4000)                                                     # l'écran de démarrage
    b.evaluate("document.getElementById('go').click()")
    b.wait_for_function("window.__sample.on")
    import_wav(b, wav(tmp_path / "boucle.wav", 4))
    assert fid in b.evaluate("window.__sample.targets()")
    send_key(b)
    b.evaluate(f"window.__sample.target = '{fid}'")
    return a, b


def test_envoi_pigeon(page, tmp_path):
    a, b = sent_to(page, tmp_path, "pigeon")
    send_key(b)
    assert b.evaluate("window.__sample.sendArmed") is True
    assert "SEND to confirm" in b.evaluate("window.__sample.sendLine()")
    send_key(b)
    a.wait_for_function("document.getElementById('status').textContent.includes('chargé')", timeout=30000)


def test_envoi_zp12(page, tmp_path):
    a, b = sent_to(page, tmp_path, "zp12")
    send_key(b)
    a.wait_for_function("document.getElementById('status').textContent.startsWith('zp12 : 16 sons')", timeout=60000)


def test_envoi_fichier(page, tmp_path):
    with_sample(page, tmp_path)
    send_key(page)
    page.evaluate("window.__sample.target = 'file'")
    with page.expect_download() as dl:
        send_key(page)
    d = dl.value
    assert d.suggested_filename == "S01.wav"
    assert open(d.path(), "rb").read(4) == b"RIFF"


def test_erase(page, tmp_path):
    with_sample(page, tmp_path)
    send_key(page)
    page.evaluate("window.__sample.target = 'erase'")
    send_key(page)
    assert page.evaluate("window.__sample.samples.length") == 1                  # d'abord la confirmation
    send_key(page)
    page.wait_for_function("window.__sample.samples.length === 0")
    assert page.evaluate("window.__engine().sample") is None                     # plus rien dans le moteur
    page.reload()
    page.wait_for_selector("#panel [data-label='REC']")
    page.wait_for_timeout(300)
    assert page.evaluate("window.__sample.samples.length") == 0


def test_onglets_caches_en_portrait(page):
    """Duo empilé (portrait) : sous le module, comme sous un FM-1, pas d'onglets FM1-A | FM1-B."""
    a, b = open_duo_with(page, "sample", 820, 1180)
    page.wait_for_function("document.querySelector('.duo-stage').dataset.layout === 'stack'")
    b.wait_for_selector(".duo-tabs", state="attached")
    assert b.evaluate("getComputedStyle(document.querySelector('.duo-tabs')).display") == "none"


# ---------------------------------------------------------------- corrections après la relecture
def wav_info(page, expr):
    """[images, canaux, crête] d'un .wav (Uint8Array) rendu par la page."""
    return page.evaluate(f"""(() => {{ const w = {expr}, d = new DataView(w.buffer, w.byteOffset), nc = d.getUint16(22, true), n = d.getUint32(40, true) / 2;
      let pk = 0; for (let i = 0; i < n; i++) pk = Math.max(pk, Math.abs(d.getInt16(44 + 2 * i, true)) / 32768); return [n / nc, nc, pk]; }})()""")


def test_one_shot_joue_une_fois(page, tmp_path):
    with_sample(page, tmp_path, 0.5)
    assert page.evaluate("window.__sample.samples[window.__sample.cur].bars") is None
    page.evaluate("window.__engine().play(true)")
    page.wait_for_timeout(1500)
    assert rms_out(page) < 0.001
    assert page.evaluate("window.__engine().playing") is False


def test_rec_lie_sur_un_temps(page):
    a, b = duo_ready(page, 120)
    tap(b, "[data-label='PLAY']")
    page.wait_for_function("window.__duo.frames.b.contentWindow.__engine().playing", timeout=5000)
    page.wait_for_timeout(700)
    b.evaluate("window.__sample.capt.thresh = null")
    pressed = b.evaluate("window.__sample.clock.beats(performance.now())")
    tap(b, "[data-label='REC']")
    b.wait_for_function("!!window.__sample.recording")
    at = b.evaluate("window.__sample.recording.at")
    assert at is not None and at == int(at) and at > pressed, (pressed, at)
    tap(b, "[data-label='REC']")


def test_envoi_echec_affiche(page, tmp_path):
    with_sample(page, tmp_path)
    page.evaluate("""window.__sample.fm1A = () => ({ w: { File, __takeSamples: async () => ({ ok: false, text: 'Échantillons : délai dépassé' }) },
      eng: { entry: { id: 'pigeon' } } })""")
    r = page.evaluate("window.__sample.send('pigeon')")
    assert "délai dépassé" in r
    assert "Sent" not in page.evaluate("window.__sample.note") and "délai dépassé" in page.evaluate("window.__sample.note")


def test_tranches_envoyees_avec_reglages(page, tmp_path):
    with_sample(page, tmp_path)
    page.evaluate("Object.assign(window.__sample.samples[window.__sample.cur].cols[0], { start: 0, len: 100, pitch: 0, gain: 50 })")
    frames, nc, pk = wav_info(page, "window.__sample.sliceWav(window.__sample.samples[window.__sample.cur], 0)")
    rate = page.evaluate("window.__sample.samples[window.__sample.cur].rate")
    assert abs(frames - 0.1 * rate) <= 2, frames
    assert abs(pk - 0.5 * 12000 / 32768) < 0.02, pk


def test_pigeon_chanson_courte(page, tmp_path):
    with_sample(page, tmp_path, 1.5)
    n = page.evaluate("window.__sample.pigeonFiles(window.__sample.samples[window.__sample.cur]).length")
    assert n == 17
    frames, nc, pk = wav_info(page, "window.__sample.pigeonFiles(window.__sample.samples[window.__sample.cur])[0].bytes")
    rate = page.evaluate("window.__sample.samples[window.__sample.cur].rate")
    assert frames / rate >= 2.05


def test_eteindre_pendant_capture(page):
    page.add_init_script("""window.__streams = []; const g = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
      navigator.mediaDevices.getUserMedia = async (c) => { const s = await g(c); window.__streams.push(s); return s; };""")
    open_sample(page); power_sample(page)
    page.evaluate("window.__sample.capt.thresh = null")
    tap(page, "[data-label='REC']")
    page.wait_for_function("!!window.__sample.recording")
    page.click("#power")
    page.wait_for_function("!window.__sample.on")
    assert page.evaluate("window.__sample.recording") is None
    assert page.evaluate("window.__streams.every((s) => s.getTracks().every((t) => t.readyState === 'ended'))") is True


def test_glisser_une_valeur(page, tmp_path):
    with_sample(page, tmp_path)
    lcd_touch(page, 385, 40); lcd_touch(page, 385, 80, kind="pointermove"); lcd_touch(page, 385, 80, kind="pointerup")
    assert page.evaluate("window.__sample.col") == 3
    assert page.evaluate("window.__sample.samples[window.__sample.cur].cols[window.__sample.slice].gain") < 100


def test_poignee_de_fin(page, tmp_path):
    with_sample(page, tmp_path)
    before = page.evaluate("window.__sample.samples[window.__sample.cur].cols[0].len")
    x = 10 + 420 * 1 / 16 - 1                                            # la fin de la tranche 1, juste avant la limite suivante
    page.evaluate("window.__sample.samples[window.__sample.cur].cols[0].len -= 60")
    xe = 10 + 420 * ((before - 60) / 1000 / 4)
    lcd_touch(page, xe, 120); lcd_touch(page, xe - 10, 120, kind="pointermove"); lcd_touch(page, xe - 10, 120, kind="pointerup")
    assert page.evaluate("window.__sample.samples[window.__sample.cur].cols[0].len") < before - 60


def test_puce_de_cible(page, tmp_path):
    with_sample(page, tmp_path)
    send_key(page)
    page.evaluate("window.__sample.target = 'erase'")
    x = page.evaluate("window.__sample.targetChipX('FILE')")
    lcd_touch(page, x, 68); lcd_touch(page, x, 68, kind="pointerup")
    assert page.evaluate("window.__sample.target") == "file"


def test_micro_mono_reste_mono(page):
    page.add_init_script("""navigator.mediaDevices.getUserMedia = async () => { const c = new AudioContext(), o = c.createOscillator(), d = c.createMediaStreamDestination();
      d.channelCount = 1; d.channelCountMode = 'explicit'; o.connect(d); o.start(); return d.stream; };""")
    open_sample(page); power_sample(page)
    page.evaluate("window.__sample.capt.thresh = null")
    assert page.evaluate("window.__sample.capture('mic', { seconds: 0.5 }).then((s) => s.ch.length)") == 1


def test_session_audio_pendant_le_micro(page):
    page.add_init_script("Object.defineProperty(navigator, 'audioSession', { value: { type: 'auto' }, configurable: true })")
    open_sample(page); power_sample(page)
    assert page.evaluate("navigator.audioSession.type") == "playback"
    page.evaluate("window.__sample.capt.thresh = null")
    tap(page, "[data-label='REC']")
    page.wait_for_function("!!window.__sample.recording")
    assert page.evaluate("navigator.audioSession.type") == "play-and-record"
    tap(page, "[data-label='REC']")
    page.wait_for_function("!window.__sample.recording")
    assert page.evaluate("navigator.audioSession.type") == "playback"


def test_rec_pad_coupe_le_roll(page, tmp_path):
    with_sample(page, tmp_path)
    spy_sent(page)
    page.evaluate("window.__sample.capt.thresh = null")
    page.dispatch_event("[data-pad='3']", "pointerdown", {"pointerId": 3, "isPrimary": True})
    page.wait_for_timeout(400)
    assert page.evaluate("window.__sent.some((m) => m.t === 'roll' && m.i === 3 && m.on)")
    tap(page, "[data-label='REC']")
    page.wait_for_function("!!window.__sample.recording")
    last = page.evaluate("window.__sent.filter((m) => m.t === 'roll' && m.i === 3).pop()")
    assert last["on"] is False
    tap(page, "[data-label='REC']")
    page.dispatch_event("[data-pad='3']", "pointerup", {"pointerId": 3, "isPrimary": True})
