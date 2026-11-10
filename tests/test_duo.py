"""Duo : deux FM-1 dans la même page (FM1-A, FM1-B), leurs dispositions, leurs mémoires, le tempo lié (l'horloge de la page)."""
import pytest


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


def test_linked_tempo_greys_unfollowing(page):
    """Tempo lié : dans le sélecteur, un firmware qui suit l'horloge MIDI se choisit (texte noir), un autre est grisé et
    ne se choisit pas ; délié, tout se choisit à nouveau, la liste ouverte se met à jour."""
    a, b = open_duo(page, 1600, 900)
    power(a)
    a.wait_for_function("window.__catalogue && window.__catalogue.length")
    dis = lambda i: a.evaluate("(i) => document.querySelector(`#fw-results .fw-item[data-id='${i}']`).getAttribute('aria-disabled')", i)
    find = lambda i: a.evaluate("""(i) => { const e = window.__catalogue.find((x) => x.id === i), s = document.getElementById('fw-search');
      s.value = e.nom; s.dispatchEvent(new Event('input')); }""", i)
    link(page)
    a.evaluate("document.getElementById('fw-picker').click()")
    find("mutable")                                   # émulé, pas d'horloge MIDI dans son code
    assert dis("mutable") == "true"
    find("sloop")                                     # émulé, suit l'horloge par sa prise TRS
    assert dis("sloop") is None
    find("kwasub")                                    # suit l'horloge, mais par l'USB seulement : l'émulateur ne la lui donne pas
    assert dis("kwasub") == "true"
    a.evaluate("document.querySelector(`#fw-results .fw-item[data-id='kwasub']`).click()")
    assert a.evaluate("document.getElementById('status').textContent") == "Tempo lié : K-WASUB ne suit pas l'horloge MIDI."
    assert a.evaluate("window.__engine() === window.__fw")
    a.evaluate("document.getElementById('fw-picker').click()"); find("mutable")
    page.click(".duo-link")                           # délié, la liste ouverte : tout se choisit
    page.wait_for_function("!window.__duo.linked")
    assert dis("mutable") is None
    assert a.evaluate("window.__catalogue.every((e) => [true, false, 'usb'].includes(e.horloge_midi))")


def test_unfollowing_firmware_explained(page):
    """Monohull émulé sur son horloge interne (CLK INT) ne démarre pas avec l'autre : la bulle dit quoi régler.
    (Un natif de la famille Felucca, lui, suit seul : test_native_follows_without_setting.)"""
    a, b = open_duo(page, 1600, 900)
    power(a)
    power(b)
    a.wait_for_function("window.__catalogue && window.__catalogue.length")
    assert a.evaluate("() => window.__useEngine(window.__catalogue.find((e) => e.id === 'monohull'))")
    page.wait_for_timeout(1500)
    link(page)
    b.evaluate("window.__host.press('PLAY'); window.__host.release('PLAY')")
    page.wait_for_function("document.querySelector('.fs-tip')", timeout=4000)
    tip = page.inner_text(".fs-tip")
    assert "FM1-A" in tip and "CLK" in tip and "USB" in tip


def estampie_and_va(page):
    """FM1-A : ESTAMPIE natif (famille Felucca), sur son horloge interne ; FM1-B : FM-1+VA."""
    a, b = open_duo(page, 1600, 900)
    power(a)
    power(b)
    a.wait_for_function("window.__catalogue && window.__catalogue.some((e) => e.id === 'estampie' && e.natif)")
    assert a.evaluate("() => window.__useEngine(window.__catalogue.find((e) => e.id === 'estampie'))")
    page.wait_for_timeout(2500)
    return a, b


def tap(page, fr, btn):
    fr.evaluate(f"window.__host.press('{btn}')"); page.wait_for_timeout(120); fr.evaluate(f"window.__host.release('{btn}')"); page.wait_for_timeout(400)


def test_own_play_on_internal_clock_explained(page):
    """Tempo lié, un PLAY seul sur ESTAMPIE resté sur CLK INT : il ne part pas à son propre tempo, FM-1+VA part, et la bulle
    dit quoi régler (avant : ESTAMPIE jouait à son tempo, sa lumière PLAY verte, sans bulle)."""
    a, b = estampie_and_va(page)
    link(page, 130)
    tap(page, a, "PLAY")
    page.wait_for_function("document.querySelector('.fs-tip')", timeout=4000)
    tip = page.inner_text(".fs-tip")
    assert "FM1-A" in tip and "CLK" in tip and "USB" in tip
    assert a.evaluate("window.__engine().playLight()") != "green"
    assert b.evaluate("window.__fw.S.playing")


def test_own_play_on_external_clock_starts_both(page):
    """ESTAMPIE sur CLK USB (HOME, HOME : la page CLOCK ; KNOB 3) : un PLAY seul sur lui les lance ensemble, un autre les arrête."""
    a, b = estampie_and_va(page)
    tap(page, a, "HOME"); tap(page, a, "HOME")
    a.evaluate("window.__host.turn('KNOB3', 1)")                       # CLK : INT -> USB
    page.wait_for_timeout(400)
    link(page, 130)
    page.wait_for_timeout(600)
    tap(page, a, "PLAY")
    a.wait_for_function("window.__engine().playLight() === 'green'", timeout=3000)
    assert b.evaluate("window.__fw.S.playing") and page.evaluate("window.__duo.playing")
    tap(page, a, "PLAY")
    a.wait_for_function("window.__engine().playLight() !== 'green'", timeout=3000)
    assert not b.evaluate("window.__fw.S.playing")


def test_own_play_held_reaches_firmware(page):
    """PLAY tenu seul plus de 0,9 s sur ESTAMPIE : il lui parvient (ses gestes à lui), la page ne lance rien."""
    a, b = estampie_and_va(page)
    link(page)
    a.evaluate("window.__host.press('PLAY')"); page.wait_for_timeout(1100); a.evaluate("window.__host.release('PLAY')")
    a.wait_for_function("window.__engine().playLight() === 'green'", timeout=3000)
    assert not page.evaluate("window.__duo.playing")


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


@pytest.mark.parametrize("fid", ["felucca", "hortator", "melodee", "spampy", "elixir"])
def test_native_follows_without_setting(page, fid):
    """Tempo lié : un natif qui sait suivre (web_clock, tools/natif_clock.py) prend l'horloge de la page sans qu'on touche
    à la sienne : un PLAY sur FM1-B (FM-1+VA) le lance, un autre l'arrête ; délié, il revient à son propre réglage."""
    a, b = open_duo(page, 1600, 900)
    power(a)
    power(b)
    a.wait_for_function(f"window.__catalogue && window.__catalogue.some((e) => e.id === '{fid}' && e.natif)")
    assert a.evaluate(f"() => window.__useEngine(window.__catalogue.find((e) => e.id === '{fid}'))")
    assert a.evaluate("window.__engine().entry.natif_horloge") == 1
    page.wait_for_timeout(2500)

    def tap(fr, btn):
        fr.evaluate(f"window.__host.press('{btn}')"); page.wait_for_timeout(120); fr.evaluate(f"window.__host.release('{btn}')"); page.wait_for_timeout(400)

    link(page, 120)
    page.wait_for_timeout(600)
    tap(b, "PLAY")
    a.wait_for_function("window.__engine().playLight() === 'green'", timeout=4000)
    tap(b, "PLAY")
    a.wait_for_function("window.__engine().playLight() !== 'green'", timeout=4000)
    page.click(".duo-link")                           # délié : pas de réglage à remettre, pas de bulle
    page.wait_for_function("!window.__duo.linked")
    page.wait_for_timeout(300)
    assert not page.query_selector(".fs-tip")
    if fid == "felucca":                              # sur son horloge interne à nouveau : son PLAY le lance seul
        tap(a, "PLAY")
        a.wait_for_function("window.__engine().playLight() === 'green'", timeout=4000)


# les natifs que tools/natif_clock.py sait mettre sur l'horloge de la page (la famille Felucca sauf FMDj, dont la version
# navigateur fait tourner LSDj, et Purple Monkey, qui ne lit pas l'horloge ; SPAMPY, Elixir, Obervave, Shineon, Mono2k, Cutador, Berlin)
CLOCK_NATIVES = """felucca bunker caravel choralroot coralflower drift estampie felucca8 flyfish fmini ghoulbox golana golanadz hortator
jiant loomfm1 maku melodee minitone mnm1 noizdemons pigeon gammawave rainbow skiff tessera tuna unholy waveloop
spampy elixir berlinan cutador mono2k obervave shineon""".split()


def test_every_clock_native_acks(page):
    """Tempo lié : chacun de ces natifs, choisi, répond qu'il suit l'horloge de la page (web_clock appelé dans son worklet)."""
    a, b = open_duo(page, 1600, 900)
    power(a)
    a.wait_for_function("window.__catalogue && window.__catalogue.some((e) => e.natif)")
    built = a.evaluate("window.__catalogue.filter((e) => e.natif).map((e) => e.id)")
    want = [i for i in CLOCK_NATIVES if i in built]
    assert len(want) >= len(CLOCK_NATIVES) - 3, sorted(set(CLOCK_NATIVES) - set(built))   # (un natif écarté ce jour-là)
    link(page)
    bad = []
    for i in want:
        if not a.evaluate(f"() => window.__useEngine(window.__catalogue.find((e) => e.id === '{i}'))"):
            bad.append(i + " (ne démarre pas)"); continue
        try:
            a.wait_for_function("window.__engine().clockOn === true", timeout=3000)
        except Exception:
            bad.append(f"{i} (horloge {a.evaluate('window.__engine().entry.natif_horloge')})")
    assert not bad, bad
