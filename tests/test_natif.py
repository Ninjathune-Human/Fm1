"""Felucca compilé depuis ses sources (natif) derrière le panneau, à la place de l'émulation."""
from conftest import lit_pixels, power_on
from test_emu import rms, use


def test_felucca_runs_native(page):
    power_on(page)
    page.set_default_timeout(30000)
    assert use(page, "felucca") is True
    assert page.evaluate("window.__engine().kind") == "natif"
    page.wait_for_timeout(2500)
    assert lit_pixels(page) >= 2000
    page.evaluate("window.__host.keyDown(12, 't')")
    page.wait_for_timeout(500)
    level = rms(page)
    lit = page.evaluate("window.__host.keyLit(12)")
    page.evaluate("window.__host.keyUp('t')")
    assert level > 0.001, level
    assert lit is True


def test_native_light_cost(page):
    """Le firmware natif prend une petite part du temps audio (Felucca mesure lui-même sa charge)."""
    power_on(page)
    page.set_default_timeout(30000)
    assert use(page, "felucca") is True
    page.evaluate("window.__host.keyDown(12, 't'); window.__host.keyDown(16, 'u')")
    page.wait_for_function("window.__engine().load !== null", timeout=8000)
    load = page.evaluate("window.__engine().load")
    page.evaluate("window.__host.keyUp('t'); window.__host.keyUp('u')")
    assert load < 0.25, load


def test_native_then_emulated_then_back(page):
    """Felucca natif, puis un firmware émulé, puis FM-1+VA : chaque passage marche, aucune note tenue."""
    power_on(page)
    page.set_default_timeout(30000)
    assert use(page, "felucca") is True
    page.evaluate("window.__host.keyDown(12, 't')")
    assert use(page, "zp12") is True
    assert page.evaluate("window.__engine().kind") != "natif"
    page.wait_for_timeout(2000)
    assert lit_pixels(page) >= 2000
    assert use(page, "felucca") is True
    page.wait_for_timeout(800)
    assert rms(page) < 0.001
    assert use(page, "fm1va") is True
    assert page.evaluate("window.__engine() === window.__fw")


def test_native_saves_kept(page):
    """Ce que Felucca écrit dans sa flash revient à la prochaine ouverture de la page."""
    power_on(page)
    page.set_default_timeout(30000)
    assert use(page, "felucca") is True
    page.evaluate("""() => window.__engine().onWorklet({ data: { type: 'frame', sectors: { 0x97000: new Uint8Array(4096).fill(7) } } })""")
    page.wait_for_function("window.__engine().pendingSave === null", timeout=5000)
    power_on(page)
    assert use(page, "felucca") is True
    assert page.evaluate("window.__engine().lastLoadSectors && window.__engine().lastLoadSectors[0x97000][0]") == 7


def test_native_screen_60fps(page):
    """L'écran natif n'est plus plafonné à 30 images par seconde : il suit le rythme de dessin du firmware."""
    power_on(page)
    page.set_default_timeout(30000)
    assert use(page, "felucca") is True
    page.wait_for_timeout(1500)
    rate = page.evaluate("""() => new Promise((done) => {
      const e = window.__engine(), o = e.onWorklet.bind(e); let n = 0;
      e.onWorklet = (ev) => { if (ev.data.fb) n++; o(ev); };
      const t = setInterval(() => window.__host.turn('KNOB1', 1), 8);
      setTimeout(() => { clearInterval(t); e.onWorklet = o; done(n / 2); }, 2000); })""")
    assert rate > 33, rate


def test_native_colours(page):
    """L'écran natif est dans l'ordre d'octets de la dalle : un pixel 0x00F8 (rouge pur côté dalle) s'affiche rouge."""
    power_on(page)
    page.set_default_timeout(30000)
    assert use(page, "felucca") is True
    px = page.evaluate("""() => { const e = window.__engine(); e.onWorklet = () => {};
      e.fb = new Uint16Array(240 * 240).fill(0x00F8); e.fbNew = true; e.draw();
      const c = document.getElementById('screen'); return Array.from(c.getContext('2d').getImageData(c.width >> 1, c.height >> 1, 1, 1).data); }""")
    assert px[0] > 200 and px[1] < 40 and px[2] < 40, px


def test_x0x_runs_native(page):
    """X0X, de l'autre famille de protocole (store, master sur 4096), tourne aussi en natif."""
    power_on(page)
    page.set_default_timeout(30000)
    assert use(page, "x0x") is True
    assert page.evaluate("window.__engine().kind") == "natif"
    page.wait_for_timeout(2500)
    assert lit_pixels(page) >= 2000
    # X0X est une boîte à rythmes : une touche allume un pas, PLAY lance le motif
    for k in (0, 4, 8, 12):
        page.evaluate(f"window.__host.keyDown({k}, 't')"); page.wait_for_timeout(120); page.evaluate("window.__host.keyUp('t')")
    page.wait_for_timeout(300)
    assert page.evaluate("window.__host.keyLit(12)") is True, page.evaluate("window.__engine().leds")
    page.evaluate("window.__host.press('PLAY')"); page.wait_for_timeout(150); page.evaluate("window.__host.release('PLAY')")
    level = 0
    for _ in range(10):
        page.wait_for_timeout(150); level = max(level, rms(page))
    assert level > 0.001, level
    page.wait_for_function("window.__engine().load !== null", timeout=8000)
    assert page.evaluate("window.__engine().load") < 0.25


def test_x0x_store_kept(page):
    """Ce que X0X enregistre (store) revient à la prochaine ouverture."""
    power_on(page)
    page.set_default_timeout(30000)
    assert use(page, "x0x") is True
    page.evaluate("""() => window.__engine().onWorklet({ data: { type: 'frame', buttons: 0, keys: 0, store: { 3: new Uint8Array(16).fill(9) } } })""")
    page.wait_for_function("window.__engine().pendingSave === null", timeout=5000)
    power_on(page)
    assert use(page, "x0x") is True
    assert page.evaluate("window.__engine().lastLoadSectors[3][0]") == 9


def test_every_native_boots(page):
    """Chaque firmware de natif/manifest.json démarre et dessine son écran."""
    import json, os
    from conftest import ROOT
    ids = sorted(json.load(open(os.path.join(ROOT, "natif/manifest.json"))))
    power_on(page)
    page.set_default_timeout(30000)
    bad = []
    for i in ids:
        if use(page, i) is not True or page.evaluate("window.__engine().kind") != "natif":
            bad.append((i, "démarrage")); continue
        page.wait_for_timeout(1500)
        if lit_pixels(page) < 500: bad.append((i, "écran"))
    assert not bad, bad


def test_every_native_reacts(page):
    """Chaque firmware natif répond au panneau : la molette SELECT ou une touche change l'écran ou le son."""
    import json, os
    from conftest import ROOT
    ids = sorted(json.load(open(os.path.join(ROOT, "natif/manifest.json"))))
    shot = "() => { const c = document.getElementById('screen'), d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data; let h = 0; for (let i = 0; i < d.length; i += 16) h = (h * 31 + d[i] + d[i + 1] + d[i + 2]) | 0; return h; }"
    power_on(page)
    page.set_default_timeout(30000)
    mute = []
    for i in ids:
        if use(page, i) is not True:
            mute.append((i, "démarrage")); continue
        page.wait_for_timeout(4000)        # après l'écran de démarrage (environ 3 s chez fmini et pigeon), qui ignore le panneau
        before = page.evaluate(shot)
        page.evaluate("window.__host.turn('SELECT', 3)")
        page.wait_for_timeout(400)
        page.evaluate("window.__host.keyDown(12, 't')")
        page.wait_for_timeout(500)
        level = rms(page)
        page.evaluate("window.__host.keyUp('t')")
        if page.evaluate(shot) == before and level <= 0.001:
            mute.append((i, "aucune réaction"))
    assert not mute, mute
