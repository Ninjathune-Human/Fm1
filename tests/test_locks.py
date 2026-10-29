"""Les verrous d'un pas (manuel 9.13)."""
from conftest import power_on

PREP = """() => { const fw = window.__fw; fw.loadPreset(fw.bank.findIndex((p) => p.engine === 'fm'));
  fw.G.knobBank = 'preset'; fw.pats[0].notes[2] = [{ n: 60, v: 100, len: 1 }]; fw.pressRec(); fw.S.cursor = 2; }"""


def lock(page, knob, n=1):
    page.evaluate(f"() => {{ const fw = window.__fw; fw.press('SEL'); fw.turn('KNOB{knob}', {n}); fw.release('SEL'); }}")


def test_lock_gesture(page):
    power_on(page)
    page.evaluate(PREP)
    before = page.evaluate("JSON.stringify(window.__fw.cur)")
    lock(page, 2, 1)                                                    # KNOB2 du preset FM : Feedback
    assert page.evaluate("window.__fw.msg.text").startswith("Lock Feedback ")
    l = page.evaluate("window.__fw.P.set[2].locks")
    assert len(l) == 1 and l[0]["sets"] == [["fm.fb", l[0]["v"]]]
    assert page.evaluate("JSON.stringify(window.__fw.cur)") == before   # le preset ne change pas
    assert not page.evaluate("window.__fw.dirty")
    assert page.evaluate("window.__fw.top()") is None or page.evaluate("window.__fw.stack.length") <= 1   # lâcher SEL n'ouvre rien
    lock(page, 2, 1)                                                    # le même réglage : le même verrou, une valeur de plus
    assert page.evaluate("window.__fw.P.set[2].locks.length") == 1
    assert page.evaluate("window.__fw.P.set[2].locks[0].v") == l[0]["v"] + 1


def test_lock_limits(page):
    power_on(page)
    page.evaluate(PREP)
    for k in (1, 2, 3, 4):
        lock(page, k)
    assert page.evaluate("window.__fw.P.set[2].locks.length") == 4
    page.evaluate("window.__fw.G.knobBank = 'reverb'")
    lock(page, 2)
    assert page.evaluate("window.__fw.msg.text") == "Step 3 has 4 locks"
    page.evaluate("window.__fw.P.set[2].locks = []; window.__fw.G.knobBank = 'filter'")
    lock(page, 1)                                                       # Filter Type
    assert page.evaluate("window.__fw.msg.text") == "Step 3 cannot lock this"
    lock(page, 2)
    assert page.evaluate("window.__fw.msg.text").startswith("Lock Filter Cutoff ")
    page.evaluate("window.__fw.G.knobBank = 'global'")
    lock(page, 1)
    assert page.evaluate("window.__fw.msg.text") == "Step 3 cannot lock this"


def test_brightness_locks_every_modulator(page):
    power_on(page)
    page.evaluate(PREP)
    page.evaluate("() => { const fw = window.__fw; fw.cur.fm.alg = 1; fw.cur.knobs[0] = 0; }")   # Brightness sur KNOB1
    lock(page, 1, -3)
    paths = sorted(p for p, _ in page.evaluate("window.__fw.P.set[2].locks[0].sets"))
    mods = page.evaluate("() => { const s = new Set(); ALG[0].mods.forEach((m) => m.forEach((x) => s.add(x))); return [...s].sort().map((i) => 'fm.ops.' + i + '.ol'); }")
    assert paths == sorted(mods)


def test_lock_rows_in_step_list(page):
    power_on(page)
    page.evaluate(PREP)
    lock(page, 2)
    names = page.evaluate("window.__fw.stepList(2).rows.map((r) => r.name)")
    assert names[:3] == ["C4", "Feedback", "Length"] and "Clear Locks" in names
    page.evaluate("() => { const fw = window.__fw; fw.stack = [{ list: () => fw.stepList(2), sel: 1, top: 0 }]; fw.enter(); }")   # SEL l'enlève
    assert page.evaluate("window.__fw.P.set[2].locks.length") == 0


def test_no_lock_when_not_recording(page):
    power_on(page)
    page.evaluate(PREP)
    page.evaluate("window.__fw.pressRec()")                            # fin de l'enregistrement
    fb = page.evaluate("window.__fw.cur.fm.fb")
    lock(page, 2, 1 if fb < 7 else -1)
    assert page.evaluate("window.__fw.cur.fm.fb") != fb                 # le bouton change le preset
    assert not page.evaluate("(window.__fw.P.set[2] || {}).locks || []")
