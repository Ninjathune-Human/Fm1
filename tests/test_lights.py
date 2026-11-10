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
    page.evaluate("() => { window.__fw.G.seqOn = 1; }")       # séquenceur allumé, jamais lancé : éteint, comme REC
    page.wait_for_timeout(200)
    assert state(page, "PLAY") == {"lit": False, "green": False, "red": False}
    assert page.evaluate("window.__fw.buttonLit('REC')") is False
    page.evaluate("() => { window.__fw.seqPlay(); }")
    page.wait_for_timeout(200)
    assert state(page, "PLAY") == {"lit": False, "green": True, "red": False}
    page.evaluate("() => { window.__fw.seqPlay(); }")         # arrêt : rouge
    page.wait_for_timeout(200)
    assert state(page, "PLAY") == {"lit": False, "green": False, "red": True}
    page.evaluate("() => { window.__fw.seqOn(false); }")      # séquenceur éteint : plus rien
    page.wait_for_timeout(200)
    assert state(page, "PLAY") == {"lit": False, "green": False, "red": False}


def test_launch_state(page):
    """Au lancement : PLAY et REC éteints, « Jouer » replié."""
    page.goto(page.base + "index.html")
    assert page.evaluate("[window.__fw.playLight(), window.__fw.buttonLit('REC'), document.querySelectorAll('details[open]').length]") == [None, False, 0]


def test_emulated_play_colours(page):
    power_on(page)
    page.set_default_timeout(30000)
    assert use(page, "monohull") is True                                # (un émulé : zp12 et gator sont natifs maintenant)
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


def test_seq_dark_before_power_on(page):
    """Avant l'allumage, SEQ ne clignote pas, même séquenceur allumé dans les réglages sauvegardés."""
    page.goto(page.base + "index.html")
    page.evaluate("() => { window.__fw.G.seqOn = 1; }")
    seen = page.evaluate("""() => new Promise((done) => { let lit = 0; const t = setInterval(() => { if (window.__fw.buttonLit('SEQ')) lit++; }, 25);
      setTimeout(() => { clearInterval(t); done(lit); }, 2500); })""")
    assert seen == 0, seen
    assert page.evaluate("document.querySelector('.cap[data-label=\"SEQ\"]').classList.contains('lit')") is False


def test_emulated_levels(page):
    """fm1-emu mesure la part du temps où une LED brille : allumée, une colonne sur 11 de la matrice. Ramenée à 0..1 :
    1/11 est allumée ; un tiers de cela, une lueur, dessinée à son intensité vue (ledSeen)."""
    power_on(page)
    page.set_default_timeout(30000)
    assert use(page, "monohull") is True
    r = page.evaluate("""() => { const e = window.__engine(); e.onHalt = null; const seq = e.running.seq, leds = new Float32Array(41);
      e.onWorklet = ((f) => (ev) => { if (ev.data.mine) f.call(e, ev); })(e.onWorklet);   // (seules nos images)
      leds[8] = 1 / 11; leds[14] = 1 / 33; e.onWorklet({ data: { mine: 1, type: 'frame', seq, leds: leds.slice(), green: 0 } });
      const L = e.ledDuty(); return [e.buttonLit('HOME'), L.d[6], L.d[14], L.live]; }""")
    assert r[0] is True and abs(r[1] - 1) < 1e-6 and abs(r[2] - 1 / 3) < 0.01 and r[3] is True
    page.wait_for_timeout(300)
    i = page.evaluate("() => [+document.querySelector('#device .key[data-key=\"0\"]').style.getPropertyValue('--i'), ledSeen(1 / 3)]")
    assert abs(i[0] - i[1]) < 0.01 and 0.7 < i[0] < 0.9                  # 1/3 du temps : presque allumée, à l'œil


def test_seen_levels(page):
    """L'intensité vue d'une part du temps allumé (Felucca #35 : 1/4 paraît presque allumée) : croissante, 0 sous le plancher."""
    page.goto(page.base + "index.html")
    r = page.evaluate("() => [0, 0.005, 1 / 60, 1 / 30, 0.155, 0.25, 0.6, 1].map(ledSeen)")
    assert r[0] == 0 and r[1] == 0 and r[-1] == 1
    assert all(a < b for a, b in zip(r[1:], r[2:]))
    assert 0.3 < r[3] < 0.45 and 0.65 < r[5] < 0.8                     # la lueur de Felucca ; une image sur 4


def test_felucca_layers(page):
    """Natif Felucca : la lueur de repos, ce qui respire et le niveau moyen des temps DRUM se voient sous l'allumé,
    chacun à sa part du temps (felucca-bsp : la lueur 3,2 µs sur ~95, le milieu une image sur 8)."""
    from test_natif import _natif
    _natif("felucca")
    power_on(page)
    page.set_default_timeout(30000)
    assert use(page, "felucca") is True
    page.wait_for_timeout(2500)
    page.evaluate("""() => { const e = window.__engine(); e.anim = null; e.onWorklet = ((f) => (ev) => { if (!ev.data.mine) return; f.call(e, ev); })(e.onWorklet);
      e.onWorklet({ data: { mine: 1, type: 'frame', leds: [1 << 0, 1 << 0, 1 << 1, 0b110, 0, 1 << 2, 1 << 3, 1 << 4, 0] } }); }""")
    page.wait_for_timeout(300)
    keys = page.evaluate("() => [0, 1, 2, 3, 4].map((i) => document.querySelector(`#device .key[data-key='${i}']`)).map((k) => [k.getAttribute('class'), k.style.getPropertyValue('--i')])")
    caps = page.evaluate("() => ['FX', 'SEL', 'ENV'].map((l) => document.querySelector(`#device .cap[data-label='${l}']`)).map((c) => [c.getAttribute('class'), c.style.getPropertyValue('--i')])")
    seen = page.evaluate("() => [ledSeen(3200 / 95000), ledSeen(1 / 8)]")
    assert "lit" in keys[0][0] and float(keys[0][1]) == 1                # l'allumé passe devant la lueur
    assert abs(float(keys[1][1]) - seen[0]) < 0.002                     # la lueur
    pk = page.evaluate("ledSeen(154 / 256)")
    assert "breath" in keys[3][0] and 0 <= float(keys[3][1]) <= pk + 1e-3   # ce qui respire, jusqu'à 60 % de l'allumé
    assert abs(float(keys[4][1]) - seen[1]) < 0.002                     # le niveau moyen
    assert "lit" in caps[0][0] and abs(float(caps[1][1]) - seen[0]) < 0.002 and "breath" in caps[2][0]
    a = float(keys[3][1]); page.wait_for_timeout(300)
    b = float(page.evaluate("document.querySelector(`#device .key[data-key='3']`).style.getPropertyValue('--i')"))
    assert a != b                                                        # elle respire, image par image
