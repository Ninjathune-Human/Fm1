"""Duo : deux FM-1 dans la même page (FM1-A, FM1-B), leurs dispositions, leurs mémoires, le tempo lié."""


def open_duo(page, w=1180, h=820):
    page.set_viewport_size({"width": w, "height": h})
    page.goto(page.base + "index.html?duo")
    page.wait_for_function("window.__duo && window.__duo.frames.a.contentWindow.__fw && window.__duo.frames.b.contentWindow.__fw")
    return page.frame(name="a"), page.frame(name="b")


def power(fr):
    fr.evaluate("document.getElementById('go').click()")
    fr.wait_for_function("window.__fw.on && !window.__fw.splash", timeout=20000)


def test_layouts(page):
    open_duo(page, 820, 1180)
    assert page.evaluate("document.querySelector('.duo-stage').dataset.layout") == "stack"
    page.set_viewport_size({"width": 1180, "height": 820})
    page.wait_for_timeout(100)
    assert page.evaluate("document.querySelector('.duo-stage').dataset.layout") == "one"
    page.click('[role="tab"][data-k="b"]')
    assert page.evaluate("document.querySelector('iframe[name=b]').classList.contains('shown')")
    assert page.evaluate("window.__duo.frames.b.contentWindow.__midiActive") is True
    assert page.evaluate("window.__duo.frames.a.contentWindow.__midiActive") is False   # le MIDI va au FM-1 affiché
    page.set_viewport_size({"width": 1600, "height": 900})
    page.wait_for_timeout(100)
    assert page.evaluate("document.querySelector('.duo-stage').dataset.layout") == "side"
    page.click('.duo-view [data-v="one"]')
    assert page.evaluate("document.querySelector('.duo-stage').dataset.layout") == "one"


def test_separate_memories(page):
    a, b = open_duo(page)
    power(a)
    page.click('[role="tab"][data-k="b"]')
    power(b)
    b.evaluate("() => { const fw = window.__fw; fw.G.tempo = 150; fw.loadPreset(7); fw.save(); }")
    keys = page.evaluate("Object.keys(localStorage)")
    assert "fm1b.fm1va.global" in keys and "fm1b.fm1va.idx" in keys
    assert page.evaluate("localStorage.getItem('fm1va.idx')") != "7"
    assert a.evaluate("window.__fw.G.tempo") == 120 and b.evaluate("window.__fw.G.tempo") == 150


def test_b_takes_no_emulated_firmware(page):
    a, b = open_duo(page)
    page.click('[role="tab"][data-k="b"]')
    power(b)
    b.wait_for_function("window.__catalogue && window.__catalogue.length")
    dis = b.evaluate("""() => { const e = window.__catalogue.find((x) => !x.natif); document.getElementById('fw-picker').click();
      document.getElementById('fw-search').value = e.nom; document.getElementById('fw-search').dispatchEvent(new Event('input'));
      const btn = document.querySelector(`#fw-results .fw-item[data-id='${e.id}']`); const d = btn.getAttribute('aria-disabled'); btn.click(); return d; }""")
    assert dis == "true"
    assert b.evaluate("document.getElementById('status').textContent") == "En Duo, FM1-B prend FM-1+VA ou un firmware natif."
    assert b.evaluate("window.__engine() === window.__fw")


def test_linked_tempo(page):
    a, b = open_duo(page, 1600, 900)
    power(a)
    power(b)
    page.click(".duo-link")
    page.wait_for_timeout(400)
    assert a.evaluate("!!window.__fw.mi.lead") and b.evaluate("!!window.__fw.mi.follow")
    assert b.evaluate("window.__fw.globList().rows[0].dim()")           # le Tempo de FM1-B grisé
    a.evaluate("() => { const fw = window.__fw; fw.G.tempo = 150; fw.sendGlobal(); fw.seqOn(true); fw.sendSeq(); }")
    b.evaluate("""() => { const fw = window.__fw, P = fw.pats[0]; fw.G.tempo = 90; fw.sendGlobal(); P.rate = 7; P.steps = 16;
      P.notes[0] = [{ n: 60, v: 100, len: 1 }]; fw.seqOn(true); fw.sendSeq();
      window.__pos = []; const on = fw.onPos.bind(fw); fw.onPos = (m) => { window.__pos.push(m); on(m); }; }""")
    page.wait_for_timeout(500)                                          # l'horloge de FM1-A arrive déjà (Always)
    a.evaluate("window.__fw.seqPlay()")                                 # PLAY sur FM1-A : Start vers FM1-B
    page.wait_for_timeout(1500)
    pos = b.evaluate("window.__pos")
    assert len(pos) >= 8
    at = [p["at"] for p in pos]
    d = sorted(y - x for x, y in zip(at, at[1:]))
    assert 0.085 <= d[len(d) // 2] <= 0.115                             # 1/16 à 150 (0,1 s), pas à 90
    a.evaluate("window.__fw.seqPlay()")                                 # Stop
    page.wait_for_timeout(300)
    assert not b.evaluate("window.__fw.S.playing")
    page.click(".duo-link")
    page.wait_for_timeout(400)
    assert not b.evaluate("!!window.__fw.mi.follow")
