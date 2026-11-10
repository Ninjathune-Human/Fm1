"""Duo : deux FM-1 dans la même page (FM1-A, FM1-B), leurs dispositions, leurs mémoires, le tempo lié (l'horloge de la page)."""


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
    page.wait_for_function("document.querySelector('.duo-stage').dataset.layout === 'one'")
    page.frame(name="a").click('.duo-tabs [data-k="b"]')
    assert page.evaluate("document.querySelector('iframe[name=b]').classList.contains('shown')")
    assert page.evaluate("window.__duo.frames.b.contentWindow.__midiActive") is True
    assert page.evaluate("window.__duo.frames.a.contentWindow.__midiActive") is False   # le MIDI va au FM-1 affiché
    page.set_viewport_size({"width": 1600, "height": 900})
    page.wait_for_function("document.querySelector('.duo-stage').dataset.layout === 'side'")
    page.click('.duo-view [data-v="one"]')
    assert page.evaluate("document.querySelector('.duo-stage').dataset.layout") == "one"


def test_separate_memories(page):
    a, b = open_duo(page)
    power(a)
    page.frame(name="a").click('.duo-tabs [data-k="b"]')
    power(b)
    b.evaluate("() => { const fw = window.__fw; fw.G.tempo = 150; fw.loadPreset(7); fw.save(); }")
    keys = page.evaluate("Object.keys(localStorage)")
    assert "fm1b.fm1va.global" in keys and "fm1b.fm1va.idx" in keys
    assert page.evaluate("localStorage.getItem('fm1va.idx')") != "7"
    assert a.evaluate("window.__fw.G.tempo") == 120 and b.evaluate("window.__fw.G.tempo") == 150


def test_b_takes_no_emulated_firmware(page):
    a, b = open_duo(page)
    page.frame(name="a").click('.duo-tabs [data-k="b"]')
    power(b)
    b.wait_for_function("window.__catalogue && window.__catalogue.length")
    dis = b.evaluate("""() => { const e = window.__catalogue.find((x) => !x.natif); document.getElementById('fw-picker').click();
      document.getElementById('fw-search').value = e.nom; document.getElementById('fw-search').dispatchEvent(new Event('input'));
      const btn = document.querySelector(`#fw-results .fw-item[data-id='${e.id}']`); const d = btn.getAttribute('aria-disabled'); btn.click(); return d; }""")
    assert dis == "true"
    assert b.evaluate("document.getElementById('status').textContent") == "En Duo, FM1-B prend FM-1+VA ou un firmware natif."
    assert b.evaluate("window.__engine() === window.__fw")


def link(page, bpm=None):
    """Lier le tempo (et choisir le BPM) ; l'horloge de la page tourne ensuite."""
    page.click(".duo-link")
    if bpm is not None:
        page.fill(".duo-bpm input", str(bpm))
        page.dispatch_event(".duo-bpm input", "change")
    page.wait_for_function("window.__duo.linked")


def spy_midi(fr, key="data"):
    """Les octets MIDI que le moteur actif du cadre reçoit (natif : data[0] ; émulé : bytes)."""
    fr.evaluate(f"""() => {{ const e = window.__engine(), s = e.send.bind(e); window.__got = [];
      e.send = (m, t) => {{ if (m.type === 'midi') window.__got.push(...(m.{key} || [])); return s(m, t); }}; }}""")


def test_linked_tempo(page):
    """Deux FM-1+VA : l'horloge de la page, au BPM choisi ; un PLAY seul sur FM1-A lance et arrête aussi FM1-B."""
    a, b = open_duo(page, 1600, 900)
    power(a)
    power(b)
    link(page, 150)
    page.wait_for_timeout(400)
    assert a.evaluate("!!window.__fw.mi.follow") and b.evaluate("!!window.__fw.mi.follow")
    assert b.evaluate("window.__fw.globList().rows[0].dim()")           # leur Tempo grisé : ils suivent
    assert b.evaluate("valText(window.__fw.globList().rows[0])") == "150"   # FM1-B montre le BPM de la page
    for fr in (a, b):
        fr.evaluate("""() => { const fw = window.__fw, P = fw.pats[0]; fw.G.tempo = 90; fw.sendGlobal(); fw.seqOn(true); P.rate = 7; P.steps = 16;
          P.notes[0] = [{ n: 60, v: 100, len: 1 }]; fw.sendSeq(); }""")
    b.evaluate("() => { const fw = window.__fw; window.__pos = []; const on = fw.onPos.bind(fw); fw.onPos = (m) => { window.__pos.push(m); on(m); }; }")
    a.evaluate("window.__host.press('PLAY'); window.__host.release('PLAY')")   # PLAY sur FM1-A
    page.wait_for_timeout(1500)
    assert page.evaluate("window.__duo.playing")
    assert a.evaluate("window.__fw.S.playing") and b.evaluate("window.__fw.S.playing")
    at = [p["at"] for p in b.evaluate("window.__pos")]
    assert len(at) >= 8
    d = sorted(y - x for x, y in zip(at, at[1:]))
    assert 0.085 <= d[len(d) // 2] <= 0.115                             # 1/16 à 150 (0,1 s), pas à 90
    b.evaluate("window.__host.press('PLAY'); window.__host.release('PLAY')")   # PLAY sur FM1-B : les deux s'arrêtent
    page.wait_for_timeout(400)
    assert not a.evaluate("window.__fw.S.playing") and not b.evaluate("window.__fw.S.playing")
    page.click(".duo-link")
    page.wait_for_timeout(400)
    assert not b.evaluate("!!window.__fw.mi.follow")


def test_play_with_another_button_stays_local(page):
    """PLAY tenu avec un autre bouton (REC + PLAY, GLO + PLAY) reste au firmware : la page ne lance rien."""
    a, b = open_duo(page, 1600, 900)
    power(a)
    power(b)
    link(page)
    a.evaluate("window.__host.press('REC'); window.__host.press('PLAY'); window.__host.release('PLAY'); window.__host.release('REC')")
    page.wait_for_timeout(300)
    assert not page.evaluate("window.__duo.playing")


def test_native_pair_receives_clock(page):
    """Deux firmwares natifs, sans FM-1+VA : la page leur donne l'horloge, puis Start et Stop avec un PLAY seul."""
    a, b = open_duo(page, 1600, 900)
    power(a)
    power(b)
    for fr in (a, b):
        fr.wait_for_function("window.__catalogue && window.__catalogue.some((e) => e.natif)")
        assert fr.evaluate("() => window.__useEngine(window.__catalogue.find((e) => e.natif && e.natif_dialecte === 'felucca'))")
        spy_midi(fr)
    link(page)
    page.wait_for_timeout(600)
    for fr in (a, b):
        assert fr.evaluate("window.__got").count(0xF8) >= 10            # 120 BPM : 48 impulsions par seconde
    a.evaluate("window.__host.press('PLAY'); window.__host.release('PLAY')")
    page.wait_for_timeout(300)
    for fr in (a, b):
        assert 0xFA in fr.evaluate("window.__got")
    b.evaluate("window.__host.press('PLAY'); window.__host.release('PLAY')")
    page.wait_for_timeout(200)
    for fr in (a, b):
        assert 0xFC in fr.evaluate("window.__got")


def test_bpm_sets_pulse_rate(page):
    """Le BPM règle l'horloge : 24 impulsions par noire."""
    a, b = open_duo(page, 1600, 900)
    power(a)
    a.wait_for_function("window.__catalogue && window.__catalogue.some((e) => e.natif)")
    assert a.evaluate("() => window.__useEngine(window.__catalogue.find((e) => e.natif && e.natif_dialecte === 'felucca'))")
    link(page, 60)
    page.wait_for_timeout(500)
    spy_midi(a)
    page.wait_for_timeout(2000)
    n = a.evaluate("window.__got").count(0xF8)
    assert 40 <= n <= 56, n                                             # 60 BPM : 24 par seconde, 48 en deux secondes


def test_sheet_opens_upward_frame_stays(page):
    a, _ = open_duo(page, 834, 1112)
    a.click("#fw-picker")
    page.wait_for_timeout(300)
    up = a.evaluate("document.getElementById('fw-sheet').getBoundingClientRect().bottom <= document.getElementById('fw-picker').getBoundingClientRect().top")
    assert up and a.evaluate("scrollY") == 0                            # la liste au-dessus du contrôle, le cadre en place
    a.evaluate("scrollTo(0, 40)")
    page.wait_for_timeout(100)
    a.click("#fw-picker")
    assert a.evaluate("scrollY") == 0


def test_sheet_visible_side_by_side(page):
    a, _ = open_duo(page, 1366, 1024)
    page.wait_for_function("document.querySelector('.duo-stage').dataset.layout === 'side'")
    a.click("#fw-picker")
    a.wait_for_function("document.getElementById('fw-sheet').getBoundingClientRect().bottom <= innerHeight + 1", timeout=3000)   # (sa montée finie)
    top, bottom, h = a.evaluate("() => { const r = document.getElementById('fw-sheet').getBoundingClientRect(); return [r.top, r.bottom, innerHeight]; }")
    assert 0 <= top < bottom <= h + 1 and bottom - top > 200           # la liste dans le cadre, pas hors de vue


def test_link_works_with_any_firmware(page):
    """Rien d'allumé : le tempo se lie quand même, et le BPM se règle (il n'attend plus FM-1+VA)."""
    open_duo(page, 1600, 900)
    assert page.is_disabled(".duo-bpm input")
    link(page, 100)
    assert page.evaluate("window.__duo.bpm") == 100 and not page.is_disabled(".duo-bpm input")
    assert page.evaluate("localStorage.getItem('fm1.duo.bpm')") == "100"


def test_emulated_follows(page):
    """FM1-A émulé : l'horloge de la page arrive par sa prise MIDI IN."""
    a, b = open_duo(page, 1600, 900)
    power(a)
    a.wait_for_function("window.__catalogue && window.__catalogue.length")
    assert a.evaluate("() => window.__useEngine(window.__catalogue.find((e) => e.id === 'monohull'))")
    spy_midi(a, "bytes")
    link(page)
    page.wait_for_timeout(600)
    assert a.evaluate("window.__got").count(0xF8) >= 10


def test_unfollowing_firmware_explained(page):
    """Felucca natif sur son horloge interne (CLK INT) ne démarre pas avec l'autre : la bulle dit quoi régler."""
    a, b = open_duo(page, 1600, 900)
    power(a)
    power(b)
    a.wait_for_function("window.__catalogue && window.__catalogue.some((e) => e.natif)")
    assert a.evaluate("() => window.__useEngine(window.__catalogue.find((e) => e.id === 'felucca'))")
    link(page)
    b.evaluate("window.__host.press('PLAY'); window.__host.release('PLAY')")
    page.wait_for_function("document.querySelector('.fs-tip')", timeout=4000)
    tip = page.inner_text(".fs-tip")
    assert "FM1-A" in tip and "CLK" in tip and "USB" in tip


def test_felucca_follows_linked_tempo(page):
    """Felucca natif réglé sur CLK USB (HOME, HOME : la page CLOCK ; KNOB 3) suit le tempo lié : un PLAY sur FM1-B (FM-1+VA)
    le lance, un autre l'arrête. (Sa version navigateur reçoit le MIDI temps réel depuis tools/natif_build.sh.)"""
    a, b = open_duo(page, 1600, 900)
    power(a)
    power(b)
    a.wait_for_function("window.__catalogue && window.__catalogue.some((e) => e.id === 'felucca' && e.natif)")
    assert a.evaluate("() => window.__useEngine(window.__catalogue.find((e) => e.id === 'felucca'))")
    page.wait_for_timeout(2500)

    def tap(fr, btn):
        fr.evaluate(f"window.__host.press('{btn}')"); page.wait_for_timeout(120); fr.evaluate(f"window.__host.release('{btn}')"); page.wait_for_timeout(400)

    tap(a, "HOME"); tap(a, "HOME")
    a.evaluate("window.__host.turn('KNOB3', 1)")                       # CLK : INT -> USB
    page.wait_for_timeout(400)
    link(page, 120)
    page.wait_for_timeout(600)
    tap(b, "PLAY")
    a.wait_for_function("window.__engine().playLight() === 'green'", timeout=3000)
    tap(b, "PLAY")
    a.wait_for_function("window.__engine().playLight() !== 'green'", timeout=3000)
