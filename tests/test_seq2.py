"""Le séquenceur, deuxième partie (manuel 9.11 à 9.18) : réglages d'un pas, d'une note, du pattern, lu sur ce qu'envoie le MIDI."""
from test_midi import midi, sent  # noqa: F401

SETUP = """([steps, rate]) => { const fw = window.__fw;
  fw.pats.forEach((p, i) => { Object.assign(p, { steps, rate, chain: -1, repeats: 1, preset: -1, set: [] }); p.notes = Array.from({ length: 64 }, () => []); });
  fw.pats[0].notes[0] = [{ n: 60, v: 100, len: 1 }];
  fw.seqOn(true); fw.sendSeq(); window.__sent.length = 0;
  window.__pos = []; const on = fw.onPos.bind(fw); fw.onPos = (m) => { window.__pos.push(m); on(m); }; }"""


def setup(page, steps=4, rate=3):                                    # 1/4 à 120 : un pas toutes les 0,5 s
    page.evaluate(SETUP, [steps, rate])


def play(page, ms):
    page.evaluate("window.__fw.seqPlay()")
    page.wait_for_timeout(ms)
    page.evaluate("window.__fw.seqPlay()")


def timed(page):
    return page.evaluate("window.__sent.map((x) => [x.t, x.d])")


def test_ratchet_accent_transpose(midi):
    setup(midi)
    midi.evaluate("() => { const st = window.__fw.stepSet(0); Object.assign(st, { ratchet: 3, acc: 1, tr: 2 }); window.__fw.sendSeq(); }")
    play(midi, 450)
    ons = [d for d in sent(midi) if d[0] == 0x90]
    assert ons == [[0x90, 62, 127]] * 3


def test_length_and_tie(midi):
    setup(midi)
    midi.evaluate("() => { const fw = window.__fw; fw.stepSet(0).len = 1; fw.pats[0].notes[0][0].tie = 1; fw.sendSeq(); }")   # 1/2, tenu sur le pas suivant
    play(midi, 1800)
    pos = midi.evaluate("window.__pos")
    assert abs(pos[0]["dur"] - 1.0) < 0.02 and abs(pos[1]["dur"] - 0.5) < 0.02
    t = timed(midi)
    on = next(x for x, d in t if d[:2] == [0x90, 60])
    off = next(x for x, d in t if d[:2] == [0x80, 60])
    assert 1.3 <= (off - on) / 1000 <= 1.55                             # 1 s, puis 80 % du pas suivant


def test_chance_always_by_default_and_gate(midi):
    setup(midi)
    midi.evaluate("() => { window.__fw.stepSet(0).gate = 20; window.__fw.sendSeq(); }")
    play(midi, 400)
    t = timed(midi)
    on = next(x for x, d in t if d[:2] == [0x90, 60])
    off = next(x for x, d in t if d[:2] == [0x80, 60])
    assert 0.07 <= (off - on) / 1000 <= 0.16                            # 20 % de 0,5 s


def test_repeats_and_preset(midi):
    setup(midi, steps=1, rate=7)                                        # un pas de 1/16 : 125 ms
    midi.evaluate("""() => { const fw = window.__fw; fw.loadPreset(0);
      Object.assign(fw.pats[0], { chain: 1, repeats: 3 }); Object.assign(fw.pats[1], { chain: 0, preset: 5 }); fw.sendSeq(); }""")
    play(midi, 800)
    pats = [p["pat"] for p in midi.evaluate("window.__pos")]
    assert pats[:5] == [0, 0, 0, 1, 0]
    assert midi.evaluate("window.__fw.idx") == 5                       # le Preset du pattern 2, gardé au retour sur 1 (Off)


def test_time_multiplier_round_trips(midi):
    setup(midi, steps=8, rate=7)
    before = midi.evaluate("""() => { const P = window.__fw.pats[0]; P.notes[2] = [{ n: 64, v: 90, len: 3, tie: 1 }]; window.__fw.stepSet(2).ratchet = 2;
      return JSON.stringify([P.notes.slice(0, 8), P.steps]); }""")
    midi.evaluate("window.__fw.stretch()")
    st = midi.evaluate("[window.__fw.P.steps, window.__fw.P.notes[4][0].len, window.__fw.P.set[4].ratchet, window.__fw.P.notes[5].length]")
    assert st == [16, 7, 2, 0]
    midi.evaluate("window.__fw.squeeze(false)")
    assert midi.evaluate("window.__fw.q") is None                       # des jumeaux vides : pas de question
    assert midi.evaluate("JSON.stringify([window.__fw.P.notes.slice(0, 8), window.__fw.P.steps])") == before
    midi.evaluate("window.__fw.inPlace(2); window.__fw.inPlace(0.5)")
    assert midi.evaluate("window.__fw.P.rate") == 7
    midi.evaluate("window.__fw.P.rate = 0; window.__fw.inPlace(2)")
    assert midi.evaluate("window.__fw.msg.text") == "Rate already 1/1"
    midi.evaluate("window.__fw.P.rate = 9; window.__fw.inPlace(0.5)")
    assert midi.evaluate("window.__fw.msg.text") == "Rate already 1/32"
    midi.evaluate("window.__fw.P.notes[1] = [{ n: 62, v: 90, len: 1 }]; window.__fw.squeeze(false)")
    assert midi.evaluate("window.__fw.q.title") == "Squeeze to 1/2x?"


def test_copy_repeater(midi):
    setup(midi, steps=14, rate=7)
    midi.evaluate("window.__fw.P.notes[13] = [{ n: 67, v: 90, len: 4, tie: 1 }]; window.__fw.copyRepeater()")
    assert midi.evaluate("[window.__fw.P.steps, window.__fw.msg.text, window.__fw.P.notes[13][0].len, window.__fw.P.notes[13][0].tie, window.__fw.P.notes[27][0].n]") \
        == [28, "Repeated to 28 steps", 1, 0, 67]
    midi.evaluate("window.__fw.P.steps = 40; window.__fw.copyRepeater()")
    assert midi.evaluate("[window.__fw.P.steps, window.__fw.msg.text]") == [64, "Trimmed to 64 steps"]
    midi.evaluate("window.__fw.copyRepeater()")
    assert midi.evaluate("window.__fw.msg.text") == "Already 64 steps"


def test_step_and_note_lists(midi):
    setup(midi)
    rows = midi.evaluate("window.__fw.stepList(0).rows.map((r) => r.name + '=' + (r.kind === 'value' ? valText(r) : ''))")
    assert rows == ["C4=100", "Length=1/4", "Ratchet=Off", "Gate=Pattern", "Chance=Always", "Transpose=0", "Accent=Off", "Tie & Slide=Off",
                    "Copy Step=", "Paste Step=", "Clear Step="]
    # SEL sur la note ouvre sa liste ; Copy Step puis Paste Step sur un autre pas
    midi.evaluate("""() => { const fw = window.__fw; fw.showGrid(); fw.seqEnter(); fw.enter(); }""")
    assert midi.evaluate("window.__fw.top().list().title") == "Note Settings"
    midi.evaluate("""() => { const fw = window.__fw; fw.back(); fw.stepList(0).rows.find((r) => r.name === 'Copy Step').run();
      fw.stepList(3).rows.find((r) => r.name === 'Paste Step').run(); }""")
    assert midi.evaluate("window.__fw.P.notes[3][0].n") == 60
    midi.evaluate("window.__fw.press('GLO'); window.__fw.release('GLO')")
    assert midi.evaluate("window.__fw.S.stepClip") is None             # oubliée en quittant le séquenceur
