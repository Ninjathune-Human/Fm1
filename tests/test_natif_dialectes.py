"""Les protocoles natifs ChoralRoot, sim et MEL : ce que le panneau envoie, et ce qu'il lit des trames.
Sans firmware : un NativeFirmware dont le worklet est remplacé par un relevé des messages."""
import pytest


def make(page, dialecte):
    page.goto(page.base + "index.html")
    page.evaluate("""(d) => {
      const n = new NativeFirmware(document.getElementById('screen'), window.__fw, { id: 'essai-' + d, nom: 'Essai', natif_dialecte: d });
      window.__sent = []; n.node = { port: { postMessage: (m) => window.__sent.push(m) } };
      window.__n = n; }""", dialecte)


def sent(page):
    return page.evaluate("window.__sent.splice(0)")


def frame(page, m):
    page.evaluate("(m) => window.__n.onWorklet({ data: m })", m)


def test_sim_envoie(page):
    make(page, "sim")
    page.evaluate("window.__n.press('PLAY'); window.__n.release('PLAY'); window.__n.press('FX')")
    page.evaluate("window.__n.keyDown(5, 'a'); window.__n.keyUp('a')")
    page.evaluate("window.__n.turn('KNOB1', 2); window.__n.turn('PRESETS', -1); window.__n.turn('MASTER', 3)")
    m = sent(page)
    assert m[:3] == [{"t": "btn", "b": 12, "down": 1}, {"t": "btn", "b": 12, "down": 0}, {"t": "btn", "b": 2, "down": 1}]
    assert m[3:5] == [{"t": "key", "k": 5, "down": 1}, {"t": "key", "k": 5, "down": 0}]
    assert m[5:7] == [{"t": "enc", "e": 2, "steps": 2}, {"t": "enc", "e": 6, "steps": -1}]
    assert m[7]["t"] == "master" and 0 <= m[7]["v"] <= 1023


def test_sim_relache_tout(page):
    make(page, "sim")
    page.evaluate("window.__n.press('FX'); window.__n.keyDown(3, 'a'); window.__sent.length = 0; window.__n.releaseAll()")
    m = sent(page)
    assert {"t": "btn", "b": 2, "down": 0} in m and {"t": "key", "k": 3, "down": 0} in m and len(m) == 2


def test_sim_lit(page):
    make(page, "sim")
    frame(page, {"t": "frame", "leds": (1 << 12) | (1 << 2), "keys": 1 << 3, "glow": 0})
    assert page.evaluate("[window.__n.playLight(), window.__n.buttonLit('FX'), window.__n.buttonLit('OCT-'), window.__n.keyLit(3), window.__n.keyLit(4)]") \
        == ["green", True, False, True, False]


def test_sim_ecran_sans_inversion(page):
    """L'écran de la famille sim est dans l'ordre de la machine : 0xF800 s'affiche rouge."""
    make(page, "sim")
    px = page.evaluate("""() => { const e = window.__n; e.fb = new Uint16Array(240 * 240).fill(0xF800); e.fbNew = true; e.draw();
      const c = document.getElementById('screen'); return Array.from(c.getContext('2d').getImageData(c.width >> 1, c.height >> 1, 1, 1).data); }""")
    assert px[0] > 200 and px[1] < 40 and px[2] < 40, px


def test_sim_garde_sa_memoire(page):
    make(page, "sim")
    page.evaluate("window.__n.onWorklet({ data: { t: 'store', data: new Uint8Array(18).fill(4).buffer } })")
    page.wait_for_function("window.__n.pendingSave === null", timeout=5000)
    got = page.evaluate("nativeFlash.get('essai-sim').then((s) => new Uint8Array(s)[0])")
    assert got == 4
    # au démarrage suivant, la mémoire revient dans les options du processeur
    o = page.evaluate("window.__n.nodeOptions(new ArrayBuffer(8), new Uint8Array(18).fill(4).buffer, 512)")
    assert o["processorOptions"]["master"] == 512 and o["processorOptions"]["store"] is not None
    assert page.evaluate("window.__n.loadMessage(new ArrayBuffer(8), null, 512)") is None


def test_mel_envoie_et_lit(page):
    make(page, "mel")
    page.evaluate("window.__n.press('SEL'); window.__n.keyDown(2, 'a'); window.__n.turn('KNOB4', 1)")
    assert sent(page) == [{"type": "button", "id": 3, "down": True}, {"type": "keys", "mask": 4}, {"type": "enc", "id": 5, "n": 1}]
    # OCT- (bit 0) et la touche 20 (bit 14 + 20 = 34 : bit 2 du second mot)
    frame(page, {"type": "frame", "leds": [1, 1 << 2], "settings": [1, 2, 3], "load": 0.2})
    assert page.evaluate("[window.__n.buttonLit('OCT-'), window.__n.keyLit(20), window.__n.keyLit(19), window.__n.load]") == [True, True, False, 0.2]
    page.wait_for_function("window.__n.pendingSave === null", timeout=5000)
    assert page.evaluate("nativeFlash.get('essai-mel')") == [1, 2, 3]
    assert page.evaluate("window.__n.loadMessage(new ArrayBuffer(8), [1, 2, 3], 700)")["settings"] == [1, 2, 3]


def test_choralroot_envoie_et_lit(page):
    make(page, "choralroot")
    page.evaluate("window.__n.press('FX'); window.__n.turn('ALGORITHM', -2)")
    assert sent(page) == [{"type": "buttons", "mask": 1}, {"type": "enc", "role": 1, "n": -2}]
    leds = [0] * 42
    leds[5], leds[6], leds[27 + 10] = 2, 1, 2          # touche 5 allumée, touche 6 tamisée, PLAY rouge
    frame(page, {"type": "frame", "leds": leds, "load": 37})
    assert page.evaluate("[window.__n.keyLit(5), window.__n.keyLit(6), window.__n.playLight(), window.__n.load]") == [True, False, "red", 0.37]
    leds[41] = 2
    frame(page, {"type": "frame", "leds": leds})
    assert page.evaluate("window.__n.playLight()") == "green"


def test_choralroot_memoire(page):
    make(page, "choralroot")
    page.evaluate("window.__n.onWorklet({ data: { type: 'flash', data: new Uint8Array(16).fill(9).buffer } })")
    page.wait_for_function("window.__n.pendingSave === null", timeout=5000)
    assert page.evaluate("nativeFlash.get('essai-choralroot').then((s) => new Uint8Array(s)[3])") == 9
    m = page.evaluate("(() => { const m = window.__n.loadMessage(new ArrayBuffer(8), new Uint8Array(16).buffer, 300); return [m.type, m.master, m.flash instanceof ArrayBuffer]; })()")
    assert m == ["load", 300, True]
    # après des réglages d'usine, la mémoire enregistrée est {} : le firmware démarre à neuf
    assert page.evaluate("window.__n.loadMessage(new ArrayBuffer(8), {}, 300).flash") is None


@pytest.mark.parametrize("d", ["felucca", "x0x"])
def test_familles_existantes_inchangees(page, d):
    make(page, d)
    page.evaluate("window.__n.press('FX'); window.__n.keyDown(1, 'a'); window.__n.turn('SELECT', 1)")
    assert sent(page) == [{"type": "buttons", "mask": 1}, {"type": "keys", "mask": 2}, {"type": "enc", "role": 0, "n": 1}]
    m = page.evaluate("window.__n.loadMessage(new ArrayBuffer(8), {}, 1)")
    assert ("store" in m) == (d == "x0x") and ("sectors" in m) == (d == "felucca")
