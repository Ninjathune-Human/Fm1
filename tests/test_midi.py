"""MIDI de FM-1+VA (manuel, section 11), sur un Web MIDI simulé : une entrée et une sortie."""
import pytest

from conftest import power_on

MOCK = """(() => {
  const sent = [], input = { id: "in1", name: "Clavier", state: "connected", onmidimessage: null };
  const output = { id: "out1", name: "Synth", state: "connected", send: (d) => sent.push({ t: performance.now(), d: Array.from(d) }) };
  window.__sent = sent;
  window.__in = (bytes) => input.onmidimessage && input.onmidimessage({ data: new Uint8Array(bytes) });
  const access = { inputs: new Map([["in1", input]]), outputs: new Map([["out1", output]]), onstatechange: null };
  Object.defineProperty(navigator, "requestMIDIAccess", { configurable: true, value: () => Promise.resolve(access) });
})();"""

# ce que la page envoie au worklet, pour lire bend et profondeurs
SPY = """() => { const p = window.__fw.node.port, post = p.postMessage.bind(p); window.__posts = [];
  p.postMessage = (m, t) => { window.__posts.push(m); return post(m, t); }; }"""


@pytest.fixture
def midi(page):
    page.add_init_script(MOCK)
    power_on(page)
    page.wait_for_function("window.__fw.mi.outs.length === 1")
    return page


def send(page, *msgs):
    for m in msgs:
        page.evaluate(f"window.__in({list(m)})")


def rms(page):
    return page.evaluate("""() => { const an = window.__fw.analyser, d = new Float32Array(an.fftSize);
      an.getFloatTimeDomainData(d); let s = 0; for (const x of d) s += x * x; return Math.sqrt(s / d.length); }""")


def peak_hz(page, lo, hi):
    return page.evaluate(f"""() => {{
      const an = window.__fw.analyser, sr = an.context.sampleRate, d = new Float32Array(an.frequencyBinCount);
      an.getFloatFrequencyData(d);
      const hz = (i) => i * sr / an.fftSize;
      let best = -1;
      for (let i = 1; i < d.length - 1; i++) if (hz(i) > {lo} && hz(i) < {hi} && (best < 0 || d[i] > d[best])) best = i;
      const a = d[best - 1], b = d[best], c = d[best + 1];
      return hz(best + 0.5 * (a - c) / (a - 2 * b + c)); }}""")


def sent(page):
    return page.evaluate("window.__sent.map((x) => x.d)")


def test_note_on_plays_and_note_off_ends(midi):
    send(midi, [0x90, 69, 100])
    midi.wait_for_timeout(400)
    assert rms(midi) > 0.005
    assert 69 in midi.evaluate("[...window.__fw.lit]")
    send(midi, [0x80, 69, 0])
    midi.wait_for_timeout(2500)
    assert 69 not in midi.evaluate("[...window.__fw.lit]")
    assert not [m for m in sent(midi) if m[0] & 0xF0 == 0x90]       # une note reçue n'est pas renvoyée


def test_pitch_bend_follows_bend_up(midi):
    midi.evaluate("window.__fw.analyser.fftSize = 32768")
    send(midi, [0xE0, 0x7F, 0x7F], [0x90, 69, 100])                  # tout en haut : Bend Up 12, une octave
    midi.wait_for_timeout(1200)
    assert abs(peak_hz(midi, 820, 940) - 880) <= 6
    send(midi, [0x80, 69, 0], [0xE0, 0, 0x40])


def test_channels(midi):
    midi.evaluate("window.__fw.G.midiCh = 1")
    send(midi, [0x92, 69, 100])                                      # canal 3 : ignoré
    midi.wait_for_timeout(300)
    assert 69 not in midi.evaluate("[...window.__fw.lit]")
    # canal 2, le FX Channel : CC 12 allume la distorsion, CC 1 est le type de filtre, CC 64 est jeté
    send(midi, [0xB1, 12, 127], [0xB1, 1, 2], [0xB1, 64, 127])
    fx = midi.evaluate("[window.__fw.cur.fx.dist.on, window.__fw.cur.fx.filter.type, window.__fw.mi.sus]")
    assert fx == [1, 2, False]
    send(midi, [0xB1, 2, 127])                                       # gardé au maximum de Cutoff
    assert midi.evaluate("window.__fw.cur.fx.filter.cutoff") == 127
    send(midi, [0xB1, 7, 40])                                        # CC 7 sur le FX Channel : Reverb Mix
    assert midi.evaluate("window.__fw.cur.fx.reverb.mix") == 40
    send(midi, [0xB0, 7, 0])                                         # CC 7 sur le MIDI Channel : le volume
    assert midi.evaluate("window.__fw.G.master") == 0


def test_sustain_pedal_holds(midi):
    send(midi, [0xB0, 64, 127], [0x90, 60, 100], [0x80, 60, 0])
    midi.wait_for_timeout(500)
    assert 60 in midi.evaluate("[...window.__fw.lit]")
    send(midi, [0xB0, 64, 0])
    midi.wait_for_timeout(2500)
    assert 60 not in midi.evaluate("[...window.__fw.lit]")


def test_program_change(midi):
    send(midi, [0xC0, 9])
    assert midi.evaluate("window.__fw.idx") == 9


def test_preset_ccs(midi):
    midi.evaluate("window.__fw.loadPreset(0)")
    send(midi, [0xB0, 73, 127])                                      # Attack : l'enveloppe s'allume d'abord
    env = midi.evaluate("[window.__fw.cur.env.on, window.__fw.cur.env.a, window.__fw.dirty]")
    assert env == [1, 100, True]
    if midi.evaluate("window.__fw.cur.engine") == "fm":
        send(midi, [0xB0, 58, 127])
        assert midi.evaluate("window.__fw.cur.fm.alg") == 32


def test_panel_ccs(midi):
    send(midi, [0xB0, 107, 127], [0xB0, 107, 0])                     # GLO
    assert midi.evaluate("window.__fw.stack[0].root") == "glo"
    send(midi, [0xB0, 119, 127])                                     # SELECT vers le bas, tenu : il répète
    midi.wait_for_timeout(700)
    send(midi, [0xB0, 119, 0])
    sel = midi.evaluate("window.__fw.top().sel")
    assert sel >= 3
    midi.wait_for_timeout(300)
    assert midi.evaluate("window.__fw.top().sel") == sel


def test_keys_send_notes_local_off_silent(midi):
    midi.evaluate("window.__fw.keyDown(16, 'a'); window.__fw.keyUp('a')")
    midi.wait_for_timeout(200)
    assert [0x90, 69, 100] in sent(midi) and [0x80, 69, 0] in sent(midi)
    midi.evaluate("window.__fw.G.local = 0; window.__fw.G.outCh = 3; window.__fw.sendGlobal()")
    midi.wait_for_timeout(2500)
    midi.evaluate("window.__fw.keyDown(16, 'b')")
    midi.wait_for_timeout(400)
    assert [0x92, 69, 100] in sent(midi)
    assert 69 not in midi.evaluate("[...window.__fw.lit]")           # rien ne sonne
    midi.evaluate("window.__fw.keyUp('b')")


def test_send_cc_without_echo(midi):
    midi.evaluate("window.__fw.loadPreset(0); window.__fw.G.sendCC = 1; window.__fw.changed(true); window.__fw.G.knobBank = 'reverb'")
    midi.evaluate("window.__fw.turn('KNOB3', 3)")                    # Reverb Mix, sur le FX Channel (2)
    midi.wait_for_timeout(100)
    mix = midi.evaluate("window.__fw.cur.fx.reverb.mix")
    assert [0xB1, 7, mix] in sent(midi)
    n = len(sent(midi))
    send(midi, [0xB1, 7, 10])                                        # reçu : jamais renvoyé
    midi.wait_for_timeout(100)
    assert len(sent(midi)) == n


def test_send_program_change(midi):
    midi.evaluate("window.__fw.G.sendPC = 1; window.__fw.loadPreset(4)")
    assert [0xC0, 4] in sent(midi)
    n = len(sent(midi))
    send(midi, [0xC0, 7])                                            # reçu : pas renvoyé
    assert len(sent(midi)) == n


def test_midi_cc_bank(midi):
    midi.evaluate("window.__fw.G.knobBank = 'midicc'; window.__fw.turn('KNOB1', 2)")
    assert [0xB0, 74, 66] in sent(midi)


def test_mapping(midi):
    midi.evaluate(SPY)
    send(midi, [0xB0, 1, 127])
    ctl = midi.evaluate("window.__posts.filter((m) => m.t === 'ctl').pop()")
    assert ctl["modP"] == 1 and ctl["modA"] == 0
    send(midi, [0xB0, 2, 0])                                         # le souffle, le plus profond à 0 : Amplitude
    assert midi.evaluate("window.__posts.filter((m) => m.t === 'ctl').pop().modA") == 1
    midi.evaluate("window.__fw.G.map.mod = 0; window.__fw.midiCtl()")
    assert midi.evaluate("window.__posts.filter((m) => m.t === 'ctl').pop().modP") == 0


def seq_ready(page):
    page.evaluate("""() => { const fw = window.__fw;
      fw.pats[0].notes[0] = [{ n: 60, v: 100, len: 1 }]; fw.pats[0].notes[4] = [{ n: 64, v: 100, len: 1 }];
      fw.seqOn(true); fw.sendSeq();
      window.__pos = []; const on = fw.onPos.bind(fw); fw.onPos = (m) => { window.__pos.push(m); on(m); }; }""")


def test_clock_out_and_transport(midi):
    seq_ready(midi)
    midi.evaluate("window.__fw.G.clockOut = 2; window.__fw.sendGlobal()")
    midi.wait_for_timeout(300)
    assert [0xF8] not in sent(midi)                                  # Playing : rien avant PLAY
    midi.evaluate("window.__fw.seqPlay()")
    midi.wait_for_timeout(1000)
    midi.evaluate("window.__fw.seqPlay()")
    midi.wait_for_timeout(200)
    msgs = sent(midi)
    start = msgs.index([0xFA])
    assert msgs[start + 1] == [0xF8]                                 # Start, l'impulsion du pas 1, puis ses notes
    assert [0x90, 60, 100] in msgs[start + 2:]
    assert [0xFC] in msgs
    t = midi.evaluate("window.__sent.filter((x) => x.d[0] === 0xF8).map((x) => x.t)")
    n = len(t) - 1
    assert 40 <= n / ((t[-1] - t[0]) / 1000) <= 56                   # 48 par seconde à 120


def test_clock_in_start_stop_continue(midi):
    seq_ready(midi)
    midi.evaluate("window.__fw.G.sync = 1; window.__fw.sendGlobal()")
    # une horloge à 125 (20 ms l'impulsion), puis Start
    midi.evaluate("window.__clk = setInterval(() => window.__in([0xF8]), 20)")
    midi.wait_for_timeout(400)
    send(midi, [0xFA])
    midi.wait_for_timeout(1500)
    pos = midi.evaluate("window.__pos")
    assert pos[0]["step"] == 0
    at = [p["at"] for p in pos]
    d = sorted(b - a for a, b in zip(at, at[1:]))
    assert 0.10 <= d[len(d) // 2] <= 0.14                            # six impulsions le pas (1/16)
    send(midi, [0xFC])
    midi.wait_for_timeout(200)
    assert not midi.evaluate("window.__fw.S.playing")
    last = midi.evaluate("window.__pos[window.__pos.length - 1].step")
    midi.evaluate("window.__pos = []")
    send(midi, [0xFB])
    midi.wait_for_timeout(500)
    assert midi.evaluate("window.__pos[0].step") == (last + 1) % 16
    midi.evaluate("clearInterval(window.__clk)")
    assert [0xFA] not in sent(midi)                                  # pas d'horloge renvoyée en la suivant


def test_dx7_single_voice(midi):
    data = [0] * 155
    for k in range(6):
        data[k * 21 + 16] = 99                                       # Output Level
        data[k * 21 + 18] = 1                                        # Coarse
    data[134] = 4                                                    # algorithme 5
    data[145:155] = [ord(c) for c in "MIDI PATCH"]
    msg = [0xF0, 0x43, 0x00, 0x00, 0x01, 0x1B] + data + [(-sum(data)) & 0x7F, 0xF7]
    send(midi, msg)
    assert midi.evaluate("[window.__fw.cur.name, window.__fw.cur.fm.alg, window.__fw.dirty]") == ["MIDI PATCH", 5, True]


def test_arp_midi_in(midi):
    midi.evaluate("window.__fw.G.arp.on = 1; window.__fw.sendGlobal()")
    send(midi, [0x90, 60, 90])                                       # MIDI In On : l'arpégiateur la joue, et l'envoie
    midi.wait_for_timeout(600)
    send(midi, [0x80, 60, 0])
    assert [0x90, 60, 90] in sent(midi)
    midi.evaluate("window.__sent.length = 0; window.__fw.G.arp.midiIn = 0; window.__fw.sendGlobal()")
    send(midi, [0x90, 62, 90])                                       # Off : jouée tout droit, pas envoyée
    midi.wait_for_timeout(600)
    assert 62 in midi.evaluate("[...window.__fw.lit]")
    send(midi, [0x80, 62, 0])
    assert not [m for m in sent(midi) if m[0] == 0x90]


def test_seq_output_ext(midi):
    seq_ready(midi)
    midi.evaluate("window.__fw.pats[0].notes[0][0].len = 16; window.__fw.sendSeq(); window.__fw.seqPlay()")
    midi.wait_for_timeout(300)
    assert "q60" in midi.evaluate("[...window.__fw.lit]")            # Int + Ext : elle sonne
    midi.evaluate("window.__fw.seqPlay()")
    midi.evaluate("window.__fw.G.seqOut = 2; window.__fw.G.seqCh = 5; window.__fw.sendGlobal(); window.__fw.seqPlay()")
    midi.wait_for_timeout(300)
    assert [0x94, 60, 100] in sent(midi)                             # Seq Channel 5
    assert "q60" not in midi.evaluate("[...window.__fw.lit]")        # Ext : rien ne sonne
    midi.evaluate("window.__fw.seqPlay()")
