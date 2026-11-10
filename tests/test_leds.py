"""Les LED des firmwares natifs, dialecte par dialecte : la part du temps où brille chaque LED sur l'appareil, d'après les
couches que chaque version navigateur donne et les constantes relevées dans ses sources (tools/natif_leds.py)."""
import os, subprocess, sys, json
from conftest import ROOT

# une image donnée à un NativeFirmware sans worklet : sa part par LED (0..13 boutons dans l'ordre du panneau, 14.. touches)
DUTY = """([dialect, led, frames, id]) => {
  const e = new NativeFirmware(document.createElement('canvas'), window.__fw, { id: id || 't', nom: 't', natif_dialecte: dialect, natif_led: led });
  for (const m of frames) e.onWorklet({ data: Object.assign({ type: 'frame' }, m) });
  const L = e.ledDuty();
  return { d: Array.from(L.d, (v) => Math.round(v * 10000) / 10000), br: Array.from(L.br), green: L.green, pk: L.pk, play: e.playLight(), pulse: L.pulse };
}"""
FX, SEL, ENV, PLAY = 0, 1, 2, 10
G_HI, G_LO = 3200 / 95000, 1600 / 95000


def duty(page, dialect, frames, led=None, fid=None):
    if not page.url.endswith("index.html"):
        page.goto(page.base + "index.html")
    return page.evaluate(DUTY, [dialect, led, frames, fid])


def near(a, b, eps=1e-3):
    return abs(a - b) < eps


def test_felucca_layers_duty(page):
    r = duty(page, "felucca", [{"leds": [1 << FX, 1, 1 << SEL, 0b110, 0, 1 << ENV, 1 << 3, 0b10100, 0]}])
    d = r["d"]
    assert d[FX] == 1 and d[14] == 1                                    # l'allumé
    assert near(d[SEL], G_HI) and near(d[15], G_HI)                     # la lueur (DIM HI)
    assert near(d[18], 1 / 8)                                           # le niveau moyen seul : une image sur 8
    assert near(d[16], 1 / 8 + 7 / 8 * G_HI)                            # dans la lueur aussi : la lueur les autres images
    assert r["br"][ENV] == 1 and r["br"][17] == 1 and near(r["pk"], 154 / 256)
    lo = duty(page, "felucca", [{"leds": [0, 0, 1 << SEL, 0, 1, 0, 0, 0]}])
    assert near(lo["d"][SEL], G_LO) and near(lo["pk"], 77 / 256)        # DIM LO
    # les constantes du firmware passent devant celles de felucca-bsp (DUELL : la lueur 1,6 µs, MEDIUM une image sur 4)
    du = duty(page, "felucca", [{"leds": [0, 0, 1 << SEL, 0, 0, 0, 0, 1, 0, 1 << FX] + [0] * 7}], led={"dim_ns": 1600, "mid_n": 4})
    assert near(du["d"][SEL], G_LO) and near(du["d"][14], 1 / 4) and near(du["d"][FX], 1 / 4)


def test_play_two_leds(page):
    """PLAY : sa LED rouge (la sienne) et une verte. Felucca : bit 14 la verte ; sa lueur sur la rouge."""
    r = duty(page, "felucca", [{"leds": [1 << 14, 0, 1 << PLAY, 0, 0, 0, 0, 0]}])
    assert r["green"] == 1 and r["play"] == "green" and near(r["d"][PLAY], G_HI)
    x = duty(page, "x0x", [{"buttons": 1 << PLAY, "keys": 0}], led={"glow_div": 4, "glow_def": 1})
    assert x["green"] == 1 and x["d"][PLAY] == 0 and x["play"] == "green"   # X0X : allumé sur la verte
    c = duty(page, "x0x", [{"buttons": 1 << PLAY, "keys": 0, "red": 1}])
    assert c["d"][PLAY] == 1 and c["green"] == 0 and c["play"] == "red"     # CARNAC en enregistrement : la rouge


def test_x0x_glow(page):
    """La famille X0X : les boutons éteints luisent une image sur GLOW_DIV (glow_on à l'allumage, ou ce qu'exporte web_glow),
    PLAY sur sa verte ; ses touches tamisées une image sur 4, CARNAC sur dimDiv."""
    led = {"glow_div": 4, "glow_def": 1}
    r = duty(page, "x0x", [{"buttons": 1 << FX, "keys": 0, "dim": 0b11}], led)
    assert r["d"][FX] == 1 and r["d"][SEL] == 0.25 and r["green"] == 0.25 and r["d"][14] == 0.25 and r["d"][16] == 0
    off = duty(page, "x0x", [{"buttons": 0, "keys": 0, "glow": 0}], led)
    assert off["d"][SEL] == 0 and off["green"] == 0                      # éteinte dans son menu
    tribe = duty(page, "x0x", [{"buttons": 0, "keys": 0, "dimb": 1 << SEL, "glow": -1}], {"glow_div": 4, "glow_def": 0})
    assert tribe["d"][SEL] == 0.25 and tribe["d"][FX] == 0               # (TRIBE : sans lueur à l'allumage)
    carnac = duty(page, "x0x", [{"buttons": 0, "keys": 0, "dim": 1, "dimDiv": 2}])
    assert carnac["d"][14] == 0.5
    assert duty(page, "x0x", [{"buttons": 0, "keys": 0}])["d"][SEL] == 0   # sans constantes relevées : rien d'inventé


def test_fm1_base(page):
    """fm1-base : la lueur de felucca-bsp à sa force (1 DIM LO, 2 DIM HI), le niveau moyen dans la lueur."""
    r = duty(page, "base", [{"buttons": 0, "keys": 0, "dimButtons": 1 << SEL, "dimKeys": 0b11, "gl": 1, "mid": 0b10}])
    assert near(r["d"][SEL], G_LO) and near(r["d"][14], G_LO) and near(r["d"][15], 1 / 12 + 11 / 12 * G_LO)
    hi = duty(page, "base", [{"buttons": 0, "keys": 0, "dimButtons": 1 << SEL, "dimKeys": 0, "gl": 2}])
    assert near(hi["d"][SEL], G_HI)


def test_niagara_levels(page):
    """NIAGARA : ses boutons à un niveau 0..255, la part des images le carré (plat_fm1.c plat_leds), une sur 32 au moins."""
    r = duty(page, "x0x", [{"buttons": 0, "keys": 0, "levels": [255, 128, 1, 0] + [0] * 10}])
    assert r["d"][0] == 1 and near(r["d"][1], (128 / 255) ** 2) and near(r["d"][2], 1 / 32) and r["d"][3] == 0


def test_choralroot_levels(page):
    """ChoralRoot : 2 allumé ; 1 la lueur, 3 le niveau du milieu, 4 un plus faible (DIM2 9,6 µs, FAINT 1,3 µs)."""
    leds = [1, 2, 3, 4] + [0] * 23 + [0] * 14 + [0]
    r = duty(page, "choralroot", [{"leds": leds}], led={"dim_ns": 3200, "dim2_ns": 9600, "faint_ns": 1300})
    d = r["d"]
    assert near(d[14], G_HI) and d[15] == 1 and near(d[16], 9600 / 95000) and near(d[17], 1300 / 95000)
    assert page.evaluate("fromChoralRoot([3, 2].concat(new Array(40).fill(0)))")[1] == 2   # le milieu n'est pas allumé


def test_mono2k_threshold(page):
    """mono2k : sur l'appareil, une LED est allumée à partir du quart (64/255), boutons et touches pareil."""
    l = [63, 64] + [0] * 25 + [63, 64] + [0] * 12
    page.goto(page.base + "index.html")
    assert page.evaluate("(l) => fromMono2k(l)", l) == [0b10, 0b10]


def test_duell_levels(page):
    """DUELL : les niveaux du clavier (/240) et les touches jouées qui pulsent du haut au creux."""
    kl = 30 | 120 << 8 | 240 << 16 | 200 << 24
    leds = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1 << 1, 1 << 2, 1 << 0, 1 << 3, kl, 60, 900]
    r = duty(page, "felucca", [{"leds": leds}], led={"dim_ns": 1600, "mid_n": 4})
    d = r["d"]
    assert near(d[14], 30 / 240) and near(d[15], 120 / 240) and d[16] == 1 and r["br"][17] == 2
    assert r["pulse"] == {"hi": 200 / 240, "lo": 60 / 240, "ms": 900}


def test_shim_duty(page):
    """Nos worklets (Hortator, MNM-1, Ravel) donnent la part de chaque LED ; la lueur de PLAY de Ravel est sur la verte."""
    duty_arr = [0.06] * 14 + [0.25] * 27
    r = duty(page, "felucca", [{"leds": [1 << FX, 0], "duty": duty_arr, "breath": [1 << SEL, 0]}])
    assert r["d"][FX] == 1 and r["br"][SEL] == 1 and near(r["d"][ENV], 0.06) and near(r["d"][14], 0.25)
    rv = duty(page, "felucca", [{"leds": [0, 0], "duty": [0] * 41, "greenDuty": 1 / 6}])
    assert near(rv["green"], 1 / 6)


def test_natif_leds_tool(tmp_path):
    """natif_leds.py : les constantes relevées dans les sources, et les exports ajoutés aux versions navigateur."""
    (tmp_path / "firmware/hal").mkdir(parents=True)
    (tmp_path / "firmware/src/app").mkdir(parents=True)
    (tmp_path / "host").mkdir()
    (tmp_path / "firmware/hal/fm1_input.h").write_text("#define FM1_LED_DIM_NS 1600u\n#define FM1_LED_MID_N 4u\n#define FM1_LED_DIM_LO_NS 1600u\n")
    (tmp_path / "firmware/src/app/plat_fm1.c").write_text("#define GLOW_DIV 4u\nstatic uint8_t glow_on = 0;\n")
    (tmp_path / "host/a_host.c").write_text("static int glow_on = 1;\nvoid plat_glow(int on) { glow_on = on; }\n")
    (tmp_path / "host/b_host.c").write_text("void plat_glow(int on) { (void)on; }\nvoid plat_backlight(int level) { (void)level; }\n")
    tool = os.path.join(ROOT, "tools/natif_leds.py")
    c = json.loads(subprocess.run([sys.executable, tool, "consts", str(tmp_path)], capture_output=True, text=True, check=True).stdout)
    assert c == {"dim_ns": 1600, "mid_n": 4, "dim_lo_ns": 1600, "glow_div": 4, "glow_def": 0}
    subprocess.run([sys.executable, tool, "patch", str(tmp_path)], check=True, capture_output=True)
    a, b = (tmp_path / "host/a_host.c").read_text(), (tmp_path / "host/b_host.c").read_text()
    assert "int web_glow(void) { return glow_on != 0; }" in a
    assert "web_glow_v = on != 0; plat_glow_0(on);" in b and "static void plat_glow_0(int on) { (void)on; }" in b
    assert "web_back_v = level & 3;" in b and "int web_backlight(void)" in b
    w = tmp_path / "worklet.js"
    w.write_text('const msg = { type: "frame", buttons: ex.web_lit_buttons() >>> 0, keys: 0 };')
    subprocess.run([sys.executable, tool, "worklet", str(w)], check=True, capture_output=True)
    assert "glow: ex.web_glow ? ex.web_glow() | 0 : -1" in w.read_text()
    for f in ("host/a_host.c", "host/b_host.c"):                       # du C qui se compile
        r = subprocess.run(["cc", "-fsyntax-only", "-x", "c", "-", "-include", "stdint.h"], input=(tmp_path / f).read_text(), capture_output=True, text=True)
        assert r.returncode == 0, r.stderr


def test_native_led_exports(page):
    """Les natifs compilés par l'action : leurs constantes relevées (natif.json "led"), et les couches que natif_leds.py
    exporte (la lueur des boutons X0X, la force de celle de fm1-base) ou que nos worklets calculent (Hortator, Ravel)."""
    import pytest
    from conftest import power_on
    from test_emu import use
    m = json.load(open(os.path.join(ROOT, "natif/manifest.json"))) if os.path.exists(os.path.join(ROOT, "natif/manifest.json")) else {}
    if "x0x" not in m:
        pytest.skip("pas de natif/")
    assert m["x0x"].get("led", {}).get("glow_div") == 4 and m["duell"].get("led", {}).get("mid_n") == 4
    power_on(page)
    page.set_default_timeout(30000)
    raw = """(keys) => new Promise((done) => { const e = window.__engine(), f = e.onWorklet.bind(e), seen = {};
      e.onWorklet = (ev) => { for (const k of keys) if (ev.data && ev.data[k] !== undefined) seen[k] = ev.data[k]; f(ev); };
      setTimeout(() => done(seen), 2500); })"""
    want = {"x0x": ["glow"], "ctl": ["gl", "mid"], "hortator": ["duty", "breath"], "mnm1": ["duty"], "ravel": ["duty"]}
    for fid, keys in want.items():
        if fid not in m:
            continue
        assert use(page, fid) is True
        page.wait_for_timeout(1500)
        seen = page.evaluate(raw, keys)
        assert all(k in seen for k in keys), (fid, seen)
        if fid == "x0x":
            assert seen["glow"] in (0, 1), seen                         # exportée (et non -1, inconnue)
        if fid == "ctl":
            assert seen["gl"] in (0, 1, 2), seen
