"""Lumières des boutons : seule la légende s'éclaire ; PLAY vert en lecture, rouge à l'arrêt séquenceur actif, éteint sinon."""
from conftest import power_on
from test_emu import use

CAP = "document.querySelector(`.cap[data-label=\"${l}\"]`)"


def state(page, label):
    return page.evaluate(f"""(l) => {{ const c = {CAP};
      return {{ lit: c.classList.contains('lit'), green: c.classList.contains('lit-green'), red: c.classList.contains('lit-red') }}; }}""", label)


def test_only_legend_lights(page):
    power_on(page)
    page.evaluate("() => { window.__fw.cur.env.on = 1; }")
    page.wait_for_timeout(300)
    s = page.evaluate(f"""(l) => {{ const c = {CAP}, t = c.querySelector('.legend');
      return [c.classList.contains('lit'), c.querySelectorAll('.halo, .glow').length, 0, getComputedStyle(t).fill]; }}""", "ENV")
    assert s[0] is True
    assert s[1] == 0, s                                   # plus de lueur sur le capuchon
    assert s[3] not in ("rgb(36, 48, 45)",), s           # la légende n'a plus la couleur de l'encre éteinte


def test_va_play_colours(page):
    power_on(page)
    page.evaluate("() => { const f = window.__fw; f.G.seqOn = 0; f.S.playing = false; }")
    page.wait_for_timeout(200)
    assert state(page, "PLAY") == {"lit": False, "green": False, "red": False}
    page.evaluate("() => { window.__fw.G.seqOn = 1; }")
    page.wait_for_timeout(200)
    assert state(page, "PLAY") == {"lit": False, "green": False, "red": True}
    page.evaluate("() => { window.__fw.S.playing = true; }")
    page.wait_for_timeout(200)
    assert state(page, "PLAY") == {"lit": False, "green": True, "red": False}
    page.evaluate("() => { window.__fw.S.playing = false; window.__fw.G.seqOn = 0; }")


def test_emulated_play_colours(page):
    power_on(page)
    page.set_default_timeout(30000)
    assert use(page, "zp12") is True
    r = page.evaluate("""() => { const e = window.__engine(); e.onHalt = null; const seq = e.running.seq;
      const leds = new Float32Array(41), out = [];
      e.onWorklet({ data: { type: 'frame', seq, leds: leds.slice(), green: 0.9 } }); out.push(e.playLight());
      leds[12] = 0.9; e.onWorklet({ data: { type: 'frame', seq, leds: leds.slice(), green: 0 } }); out.push(e.playLight());
      e.onWorklet({ data: { type: 'frame', seq, leds: new Float32Array(41), green: 0 } }); out.push(e.playLight());
      return out; }""")
    assert r == ["green", "red", None]


def test_native_play_colours(page):
    power_on(page)
    page.set_default_timeout(30000)
    assert use(page, "felucca") is True
    r = page.evaluate("""() => { const e = window.__engine(), out = [];
      for (const b of [1 << 14, 1 << 10, 0]) { e.onWorklet({ data: { type: 'frame', leds: [b, 0, 0, 0, 0, 0, 0, 0] } }); out.push(e.playLight()); }
      return out; }""")
    assert r == ["green", "red", None]
    assert use(page, "x0x") is True
    r = page.evaluate("""() => { const e = window.__engine(), out = [];
      for (const b of [1 << 10, 0]) { e.onWorklet({ data: { type: 'frame', buttons: b, keys: 0 } }); out.push(e.playLight()); }
      return out; }""")
    assert r == ["green", None]
