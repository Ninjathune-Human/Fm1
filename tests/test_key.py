"""Jouer dans une tonalité avec le Note Engine (manuel 8.3 à 8.5), lu sur les notes que FM-1+VA envoie en MIDI."""
from test_midi import midi, sent  # noqa: F401  (la fixture et le Web MIDI simulé)

ON = 0x90


def ne(page, mode, **arp):
    sets = "".join(f"a.{k} = {v}; " for k, v in arp.items())
    page.evaluate(f"() => {{ const fw = window.__fw, a = fw.G.arp; a.on = 1; a.ne = {mode}; {sets} fw.sendGlobal(); window.__sent.length = 0; }}")


def ons(page):
    return [m[1] for m in sent(page) if m[0] == ON]


def test_auto_chord_in_c(midi):
    ne(midi, 2, key=1, chord=0)
    midi.evaluate("window.__fw.keyDown(62 - 53, 'd')")                 # Ré : Ré Fa La
    midi.wait_for_timeout(200)
    assert sorted(ons(midi)) == [62, 65, 69]
    midi.evaluate("window.__fw.G.arp.scale = 1; window.__fw.sendGlobal()")   # en Do mineur, tout de suite : Ré Fa La bémol
    midi.wait_for_timeout(200)
    assert [0x80, 69, 0] in sent(midi) and 68 in ons(midi)
    midi.evaluate("window.__fw.keyUp('d')")


def test_auto_chord_shared_note_once(midi):
    ne(midi, 2, key=1, chord=0)
    midi.evaluate("window.__fw.keyDown(60 - 53, 'c'); window.__fw.keyDown(64 - 53, 'e')")   # Do Mi Sol et Mi Sol Si
    midi.wait_for_timeout(200)
    assert sorted(ons(midi)) == [60, 64, 67, 71]
    midi.evaluate("window.__fw.keyUp('c')")
    midi.wait_for_timeout(200)
    assert [0x80, 60, 0] in sent(midi) and [0x80, 64, 0] not in sent(midi)
    midi.evaluate("window.__fw.keyUp('e')")


def test_auto_arp_pattern(midi):
    ne(midi, 1, key=1, chord=0, pattern=1, rate=9)                    # Up, en 1/32
    midi.evaluate("window.__fw.keyDown(67 - 53, 'g')")                 # Sol : Sol Si Ré
    midi.wait_for_timeout(700)
    midi.evaluate("window.__fw.keyUp('g')")
    assert ons(midi)[:6] == [67, 71, 74, 67, 71, 74]


def test_first_key_reads_the_arpeggio(midi):
    midi.evaluate("() => { const fw = window.__fw, a = fw.G.arp; a.ne = 1; a.arpeggio = 3; a.chord = 2; a.pattern = 0;"   # Major 8
                  " const r = fw.arpList().rows.find((x) => x.name === 'Key'); fw.turnRow(r, 1); }")
    a = midi.evaluate("window.__fw.G.arp")
    assert (a["key"], a["chord"], a["pattern"], a["scale"], a["voicing"], a["acc"]) == (1, 0, 4, 0, 0, 0)   # Triad, Up 8
    names = midi.evaluate("window.__fw.arpList().rows.map((r) => r.name)")
    assert "Chord" in names and "Pattern" in names and "Arpeggio" not in names
    midi.evaluate("() => { const fw = window.__fw, key = () => fw.arpList().rows.find((x) => x.name === 'Key');"
                  " fw.G.arp.chord = 1; fw.turnRow(key(), -1); fw.turnRow(key(), 1); }")   # Off, puis Do à nouveau
    assert midi.evaluate("window.__fw.G.arp.chord") == 1               # une seule fois : rien de perdu


def test_8bit_first_key(midi):
    names = midi.evaluate("""() => { const fw = window.__fw; fw.loadPreset(fw.bank.findIndex((p) => p.engine === 'b8'));
      const b = fw.cur.b8; b.bass.arp = 14; b.lead.arp = 3;                                     // Minor 7, Major 8
      const r = fw.editList().rows.find((x) => x.name === 'Key'); fw.turnRow(r, 1);
      return fw.partList('lead').rows.map((x) => x.name); }""")
    b = midi.evaluate("window.__fw.cur.b8")
    assert (b["key"], b["scale"], b["voicing"], b["acc"], b["follow"]) == (1, 0, 0, 0, 0)
    assert (b["bass"]["chord"], b["bass"]["pattern"], b["lead"]["chord"], b["lead"]["pattern"]) == (1, 1, 0, 4)   # Seventh Up, Triad Up 8
    assert "Chord" in names and "Pattern" in names and "Arpeggio" not in names
    assert midi.evaluate("window.__fw.dirty")
