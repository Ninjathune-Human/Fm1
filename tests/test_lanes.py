"""La vue Lane du séquenceur (manuel 9.2 à 9.5, 9.6.3, 9.12)."""
from conftest import power_on

B8 = """() => { const fw = window.__fw; fw.loadPreset(fw.bank.findIndex((p) => p.engine === 'b8'));
  fw.pats.forEach((p) => { p.notes = Array.from({ length: 64 }, () => []); p.set = []; p.steps = 32; });
  const P = fw.pats[0];
  P.notes[0] = [{ n: 17, v: 100, len: 1 }, { n: 48, v: 100, len: 1 }]; P.notes[2] = [{ n: 52, v: 90, len: 1 }];
  fw.stepSet(0).ratchet = 2; fw.seqOn(true); fw.showGrid(); }"""


def ev(page, js):
    return page.evaluate(js)


def sel_turn(page, knob, n):
    page.evaluate(f"() => {{ const fw = window.__fw; fw.press('SEL'); fw.turn('{knob}', {n}); fw.release('SEL'); }}")


def test_pattern_screen_and_view(page):
    power_on(page)
    ev(page, B8)
    assert ev(page, "window.__fw.stack[0].view") == "lanes"
    names = ev(page, "window.__fw.top().list().rows.map((r) => r.name)")
    assert names[:6] == ["Lead", "Bass", "SFX", "Drums", "Locks", "Pattern"] and "Time Multiplier" in names
    ev(page, "window.__fw.loadPreset(window.__fw.bank.findIndex((p) => p.engine === 'fm'))")
    assert ev(page, "window.__fw.top().list().rows.slice(0, 2).map((r) => r.name)") == ["Notes", "Locks"]
    ev(page, "window.__fw.G.seqView = 1; window.__fw.showGrid()")
    assert ev(page, "window.__fw.onGrid()")


def test_pages(page):
    power_on(page)
    ev(page, B8)
    assert ev(page, "window.__fw.viewPage()") == 0
    ev(page, "window.__fw.turn('ALGORITHM', 1)")                     # sur une lane : la page
    assert ev(page, "window.__fw.viewPage()") == 1 and ev(page, "window.__fw.S.ring") == 0   # le curseur blanc reste
    ev(page, "() => { const fw = window.__fw; fw.turn('ALGORITHM', -1); fw.pressRec(); fw.turn('ALGORITHM', 1); }")
    assert ev(page, "window.__fw.S.cursor") == 16                    # en pas à pas : le premier pas de la page
    ev(page, "() => { const fw = window.__fw; fw.top().sel = 0; for (let i = 0; i < 9; i++) fw.turnSelect(1); }")
    assert ev(page, "window.__fw.top().sel") == 4                    # en enregistrant : les lanes seulement


def test_open_lane_and_cursor(page):
    power_on(page)
    ev(page, B8)
    ev(page, "() => { const fw = window.__fw; fw.turnSelect(1); fw.enter(); }")   # Bass
    assert ev(page, "window.__fw.top().lane") == "bass"
    assert ev(page, "window.__fw.top().base") == 48                  # ouverte sur ses notes
    for _ in range(17):
        ev(page, "window.__fw.turn('ALGORITHM', 1)")
    assert ev(page, "[window.__fw.S.ring, window.__fw.viewPage()]") == [17, 1]
    ev(page, "window.__fw.turnSelect(1)")                            # SELECT : des notes plus graves
    assert ev(page, "window.__fw.top().base") == 47
    ev(page, "window.__fw.enter()")
    assert ev(page, "window.__fw.top().list().title") == "Step 18 Settings"


def test_move_swap_copy_in_a_lane(page):
    power_on(page)
    ev(page, B8)
    ev(page, "() => { const fw = window.__fw; fw.turnSelect(1); fw.enter(); }")   # Bass, curseur sur le pas 1
    sel_turn(page, "ALGORITHM", 1)
    assert ev(page, "window.__fw.msg.text") == "Step 1 moved to 2"
    assert ev(page, "window.__fw.P.notes[1].map((x) => x.n)") == [48]
    assert ev(page, "window.__fw.P.notes[0].map((x) => x.n)") == [17]   # la batterie reste sur son pas
    assert ev(page, "window.__fw.P.set[0].ratchet") == 2              # ses réglages aussi : une autre lane y a des notes
    sel_turn(page, "ALGORITHM", 1)                                    # sur le pas 3, qui a une basse : échange
    assert ev(page, "window.__fw.msg.text") == "Steps 2, 3 swapped"
    assert ev(page, "[window.__fw.P.notes[1][0].n, window.__fw.P.notes[2][0].n]") == [52, 48]
    sel_turn(page, "SELECT", 3)                                       # une copie
    assert ev(page, "window.__fw.msg.text") == "Step 3 copied to 6"
    assert ev(page, "[window.__fw.P.notes[2][0].n, window.__fw.P.notes[5][0].n]") == [48, 48]


def test_flow_moves_the_whole_step(page):
    power_on(page)
    ev(page, B8)
    ev(page, "() => { const fw = window.__fw; fw.G.seqView = 1; fw.showGrid(); fw.stepSet(0).locks = [{ id: 'p0', eng: 'b8', c: 0, name: 'Drum Decay', v: 5, min: 0, max: 99, sets: [] }]; }")
    sel_turn(page, "ALGORITHM", 3)
    assert ev(page, "window.__fw.msg.text") == "Step 1 moved to 4"
    assert ev(page, "[window.__fw.P.notes[0].length, window.__fw.P.notes[3].length, window.__fw.P.set[3].locks.length, window.__fw.P.set[3].ratchet]") == [0, 2, 1, 2]
    ev(page, "() => { const fw = window.__fw; fw.press('SEL'); fw.turn('ALGORITHM', 2); fw.keyDown(3, 'k'); fw.keyUp('k'); fw.release('SEL'); }")
    assert ev(page, "[window.__fw.S.ring, window.__fw.P.notes[3].length]") == [3, 2]   # une touche : remis à sa place


def test_full_step(page):
    power_on(page)
    ev(page, B8)
    ev(page, """() => { const fw = window.__fw, P = fw.P;
      P.notes[0] = Array.from({ length: 9 }, (_, i) => ({ n: 17 + i, v: 100, len: 1 })); P.notes[1] = [{ n: 50, v: 100, len: 1 }];
      fw.turnSelect(1); fw.enter(); fw.S.ring = 1; }""")                # la lane Bass
    sel_turn(page, "ALGORITHM", -1)                                   # une dixième note sur un pas de neuf batteries : refusé
    assert ev(page, "[window.__fw.P.notes[0].length, window.__fw.P.notes[1].length]") == [9, 1]
    ev(page, "() => { const P = window.__fw.P; P.notes[0][8] = { n: 45, v: 100, len: 1 }; window.__fw.S.ring = 1; }")   # une basse parmi huit batteries
    sel_turn(page, "ALGORITHM", -1)                                   # elle s'efface devant la nouvelle, qui arrive
    assert ev(page, "window.__fw.P.notes[0].map((x) => x.n).filter((n) => n >= 29)") == [50]


def test_locks_lane_carries_locks(page):
    power_on(page)
    ev(page, B8)
    ev(page, "() => { const fw = window.__fw; fw.stepSet(2).locks = [{ id: 'p0', eng: 'b8', c: 0, name: 'Drum Decay', v: 5, min: 0, max: 99, sets: [] }]; fw.turnSelect(4); fw.enter(); fw.S.ring = 2; }")
    sel_turn(page, "ALGORITHM", 2)
    assert ev(page, "[window.__fw.P.set[2].locks.length, window.__fw.P.set[4].locks.length, window.__fw.P.notes[2][0].n]") == [0, 1, 52]
