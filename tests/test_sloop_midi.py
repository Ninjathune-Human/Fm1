"""SLOOP : un fichier MIDI dans une piste, par le protocole de son éditeur (SysEx sur l'USB du FM-1 émulé)."""
import os

import pytest

from conftest import ROOT, lit_pixels, power_on
from test_picker import click_row, ready

# le cœur compilé par l'action, avec l'USB ouvert à la page (tools/fm1emu_usb.py)
USB = os.path.exists(os.path.join(ROOT, "runtime/worklet.js")) and "usb-plug" in open(os.path.join(ROOT, "runtime/worklet.js"), encoding="utf-8").read()


def vlq(n):
    a = [n & 0x7F]
    n >>= 7
    while n:
        a.insert(0, 0x80 | (n & 0x7F))
        n >>= 7
    return a


def smf(notes, ppq=96):
    """Un fichier MIDI de format 0 : notes [(t, durée, note, vélocité)], canal 1, 120 BPM."""
    ev = []
    for t, dur, key, vel in notes:
        ev += [(t, 1, [0x90, key, vel]), (t + dur, 0, [0x80, key, 0])]
    ev.sort(key=lambda e: (e[0], e[1]))
    body, last = [0, 0xFF, 0x51, 3, 0x07, 0xA1, 0x20, 0, 0xFF, 0x03, 4] + list(b"Test"), 0
    for t, _, b in ev:
        body += vlq(t - last) + b
        last = t
    body += [0, 0xFF, 0x2F, 0]
    u32 = lambda n: list(n.to_bytes(4, "big"))
    return bytes([0x4D, 0x54, 0x68, 0x64] + u32(6) + [0, 0, 0, 1, 0, ppq] + [0x4D, 0x54, 0x72, 0x6B] + u32(len(body)) + body)


MELODY = [(0, 24, 60, 100), (24, 24, 62, 90), (48, 48, 64, 80), (96, 24, 67, 110), (96, 24, 71, 110)]


def open_sloop(page):
    power_on(page)
    page.set_default_timeout(30000)
    page.click("#fw-picker")
    click_row(page, "sloop")
    ready(page, "SLOOP", timeout=60000)
    page.wait_for_function("() => document.getElementById('smf-box').hidden === false")
    for _ in range(20):                                   # l'écran de démarrage
        page.wait_for_timeout(500)
        if lit_pixels(page) >= 1000:
            break


def test_button_only_for_sloop(page):
    """Fichier MIDI… : sous le FM-1 avec SLOOP seulement, à sa place, et caché avec un autre firmware."""
    open_sloop(page)
    page.click("#fw-picker")
    click_row(page, "monohull")
    ready(page, "Monohull", timeout=60000)
    assert page.evaluate("document.getElementById('smf-box').hidden") is True


@pytest.mark.skipif(USB, reason="le cœur a l'USB : test_import_into_track le remplace")
def test_without_usb_core_says_so(page, tmp_path):
    """Avec un cœur sans USB (celui d'avant), choisir un fichier le dit, sans rien envoyer."""
    open_sloop(page)
    f = tmp_path / "test.mid"
    f.write_bytes(smf(MELODY))
    page.set_input_files("#smf", str(f))
    page.wait_for_function("() => document.getElementById('status').textContent.includes(\"n'a pas l'USB\")", timeout=10000)
    assert page.evaluate("document.getElementById('smf-pop').hidden") is True


@pytest.mark.skipif(not USB, reason="le cœur de ce dossier n'a pas l'USB (celui de l'action l'a)")
def test_import_into_track(page, tmp_path):
    """Un .mid dans la piste 1 : l'aperçu, l'import, puis SLOOP lui-même rend les mêmes pas et la longueur."""
    open_sloop(page)
    f = tmp_path / "test.mid"
    f.write_bytes(smf(MELODY))
    page.set_input_files("#smf", str(f))
    page.wait_for_function("() => !document.getElementById('smf-pop').hidden", timeout=30000)
    pop = page.locator("#smf-pop")
    assert "5 notes" in pop.inner_text()
    pop.locator("select").nth(1).select_option("0")      # Piste 1
    page.wait_for_timeout(1000)                           # (l'aperçu se refait pour cette piste)
    pop.locator("button.pri").click()
    page.wait_for_function("() => document.getElementById('status').textContent.includes('notes dans la piste 1')", timeout=60000)
    got = page.evaluate("""async (bytes) => {
      const L = new window.__SloopLink(window.__engine());
      await L.open();
      const div = await L.divOf(0);
      const plan = SLOOP.toSteps(SLOOP.readSmf(Uint8Array.from(bytes)).tracks[0].notes, 96, div, L.info.nstep);
      const steps = [];
      for (let i = 0; i < 8; i++) { const a = await L.rq(SLOOP.CMD.TRACK_STEP, [0, i]); steps.push({ n: a[2], notes: a.slice(3, 3 + a[2]), time: a[7] }); }
      const lenReply = await L.rq(SLOOP.CMD.TRACK_PARAM, [0, L.pLen]);
      const want = plan.steps.slice(0, 8).map((s) => ({ n: s.n, notes: s.notes.slice(0, s.n), time: s.time }));
      return { steps, want, len: (lenReply[2] | (lenReply[3] << 7)) - 8192, wantLen: plan.len };
    }""", list(smf(MELODY)))
    assert got["steps"] == got["want"], got
    assert got["len"] == got["wantLen"], got
