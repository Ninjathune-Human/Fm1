"""L'enregistrement pas à pas, finitions (manuel 8.7.2, 9.8.1 à 9.8.5, 9.11)."""
from test_midi import midi, sent  # noqa: F401

B8 = """() => { const fw = window.__fw; fw.loadPreset(fw.bank.findIndex((p) => p.engine === 'b8'));
  fw.pats.forEach((p) => { p.notes = Array.from({ length: 64 }, () => []); p.set = []; p.steps = 16; });
  fw.seqOn(true); fw.showGrid(); }"""


def ev(page, js):
    return page.evaluate(js)


def key(page, n):                                                       # la touche qui joue la note n (OCT réglé pour elle)
    page.evaluate(f"() => {{ const fw = window.__fw; fw.octave = Math.floor(({n} - 53) / 12); const i = {n} - 53 - 12 * fw.octave; fw.keyDown(i, 'k'); fw.keyUp('k'); }}")


def open_lane(page, row):
    page.evaluate(f"() => {{ const fw = window.__fw; fw.top().sel = {row}; fw.enter(); fw.pressRec(); }}")


def test_drums_lane(midi):
    ev(midi, B8)
    open_lane(midi, 3)                                                  # Drums
    key(midi, 17)
    assert ev(midi, "[window.__fw.P.notes[0].map((x) => x.n), window.__fw.S.cursor]") == [[17], 0]   # le contour reste
    key(midi, 17)
    assert ev(midi, "window.__fw.P.notes[0].length") == 0               # la même batterie l'enlève
    key(midi, 48)                                                       # une basse depuis la lane Drums
    assert ev(midi, "[window.__fw.P.notes[0].map((x) => x.n), window.__fw.S.cursor, window.__fw.top().lane]") == [[48], 1, "bass"]
    key(midi, 20)                                                       # une batterie depuis la lane Bass : Drums, le contour reste
    assert ev(midi, "[window.__fw.P.notes[1].map((x) => x.n), window.__fw.S.cursor, window.__fw.top().lane]") == [[20], 1, "drums"]
    key(midi, 30)                                                       # un effet : la lane SFX
    assert ev(midi, "[window.__fw.top().lane, window.__fw.S.cursor]") == ["sfx", 1]


def test_full_step_refuses_in_drums_lane(midi):
    ev(midi, B8)
    ev(midi, "window.__fw.P.notes[0] = Array.from({ length: 9 }, (_, i) => ({ n: 17 + i, v: 100, len: 1 }))")
    open_lane(midi, 3)
    key(midi, 48)
    assert ev(midi, "[window.__fw.P.notes[0].length, window.__fw.S.cursor, window.__fw.top().lane]") == [9, 0, "drums"]
    key(midi, 27)                                                       # une dixième batterie prend la place de la plus ancienne
    assert ev(midi, "window.__fw.P.notes[0].map((x) => x.n)") == [18, 19, 20, 21, 22, 23, 24, 25, 27]


def test_chord_in_step_recording(midi):
    ev(midi, """() => { const fw = window.__fw; fw.loadPreset(fw.bank.findIndex((p) => p.engine === 'fm'));
      fw.pats[0].notes = Array.from({ length: 64 }, () => []); Object.assign(fw.G.arp, { on: 1, ne: 2, key: 1, scale: 0, acc: 0, voicing: 0, chord: 0 });
      fw.sendGlobal(); fw.seqOn(true); fw.showGrid(); fw.pressRec(); window.__sent.length = 0; }""")
    ev(midi, "() => { const fw = window.__fw; fw.octave = 0; fw.keyDown(62 - 53, 'k'); }")   # Ré : Ré Fa La
    midi.wait_for_timeout(200)
    assert sorted(ev(midi, "window.__fw.P.notes[0].map((x) => x.n)")) == [62, 65, 69]
    assert [d[1] for d in sent(midi) if d[0] == 0x90] == [62]           # on n'entend que la touche
    ev(midi, "() => { const fw = window.__fw; fw.keyUp('k'); fw.S.cursor = 0; fw.keyDown(62 - 53, 'k'); fw.keyUp('k'); }")
    assert ev(midi, "window.__fw.P.notes[0].length") == 0               # la touche à nouveau enlève tout l'accord


def test_rec_held_long_notes(midi):
    ev(midi, """() => { const fw = window.__fw; fw.loadPreset(fw.bank.findIndex((p) => p.engine === 'fm'));
      fw.pats[0].notes = Array.from({ length: 64 }, () => []); fw.seqOn(true); fw.showGrid(); fw.pressRec(); fw.press('REC'); }""")
    key(midi, 60)
    key(midi, 60)
    ev(midi, "window.__fw.release('REC')")
    assert ev(midi, "[window.__fw.P.notes[0].map((x) => [x.n, x.len]), window.__fw.P.notes[1].length, window.__fw.S.rec, window.__fw.S.cursor]") \
        == [[[60, 3]], 0, "step", 2]
    ev(midi, "() => { window.__fw.press('REC'); window.__fw.release('REC'); }")   # une pression seule : la fin de l'enregistrement
    assert ev(midi, "window.__fw.S.rec") is None


def test_open_step_takes_the_keys(midi):
    ev(midi, B8)
    ev(midi, "() => { const fw = window.__fw; fw.pressRec(); fw.S.cursor = 3; fw.seqEnter(); }")
    key(midi, 50)
    key(midi, 53)
    assert ev(midi, "[window.__fw.P.notes[3].map((x) => x.n), window.__fw.S.cursor]") == [[50, 53], 3]
    ev(midi, "window.__fw.pressRec()")                                  # finir l'enregistrement ferme la liste
    assert ev(midi, "window.__fw.top().step") is None


def test_rec_from_pattern_settings(midi):
    ev(midi, B8)
    ev(midi, "() => { const fw = window.__fw; fw.pressSeq(); fw.pressRec(); }")
    assert ev(midi, "[window.__fw.stack.length, window.__fw.S.rec]") == [1, "step"]
