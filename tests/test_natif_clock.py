"""Le tempo lié du Duo sans réglage (tools/natif_clock.py) : là où un firmware natif lit son réglage d'horloge, « suivre l'USB »
tant que la page le demande, sans jamais écrire ce réglage ; et son worklet qui transmet le message de la page."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/natif_clock.py"


def run(*a):
    return subprocess.run([sys.executable, str(TOOL), *a], capture_output=True, text=True, check=True).stdout


def test_patch_reads_not_writes(tmp_path):
    src = tmp_path / "firmware/src"
    src.mkdir(parents=True)
    (src / "seq.c").write_text(
        "static void seq_block(void) {\n"
        "    uint32_t i, run, clock_mode = (uint32_t)song.g[G_CLOCK];\n"           # Felucca, Hortator
        "    uint32_t selected_clock = (uint32_t)song.g[G_CLOCK];\n"              # Melodee, Tessera
        "    if (song.g[G_CLOCK] && (uint32_t)song.g[G_CLOCK] == src) pulse();\n"   # Hortator, MNM-1 : la porte de l'horloge
        "}\n")
    (src / "midi_clock.c").write_text(
        "static uint32_t clock_src(void)\n{\n    uint32_t m = (uint32_t)song.g[G_CLOCK];\n"   # felucca-base (Duell)
        "    return m == CLK_AUTO ? midi_clock.lock : m < CLK_AUTO ? m : 0u;\n}\n")
    (tmp_path / "web/emu").mkdir(parents=True)
    (tmp_path / "web/emu/seq.c").write_text("uint32_t clock_mode = (uint32_t)song.g[G_CLOCK];\n")   # (la version navigateur : pas elle)
    out = run("patch", str(tmp_path))
    seq, clk = (src / "seq.c").read_text(), (src / "midi_clock.c").read_text()
    assert seq.count("(uint32_t)(web_clock_ext ? 1 : song.g[G_CLOCK])") == 3 and "if ((web_clock_ext ? 1 : song.g[G_CLOCK]) &&" in seq
    assert clk.count("uint32_t m = (uint32_t)(web_clock_ext ? 1 : song.g[G_CLOCK]);") == 1   # (USB, même là où AUTO existe)
    # chacun le définit et l'exporte une fois par unité de compilation, faiblement (beaucoup s'incluent les uns les autres)
    assert seq.startswith("#ifndef FM1_WEB_CLOCK") and clk.startswith("#ifndef FM1_WEB_CLOCK")
    assert "__attribute__((weak)) int web_clock_ext;" in seq and seq.count('export_name("web_clock")') == 1
    assert "web_clock" not in (tmp_path / "web/emu/seq.c").read_text()
    assert out.count("horloge du tempo lié") == 2
    assert run("patch", str(tmp_path)) == ""                                     # (une seconde fois : rien)


def test_sync_of_sloop_and_elixir(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "a/seq.c").write_text(
        "static int mclk_on(void) { return song.g[G_SYNC] && mclk.alive; }\n"
        "static void mclk_event(uint32_t st, uint32_t src) { if (!song.g[G_SYNC] || src != (uint32_t)song.g[G_SYNC]) return; }\n"
        "void load(void) { song.g[G_SYNC] = (int16_t)lights_sync; }\n")
    (tmp_path / "a/project.c").write_text("void p(void) { if ((uint32_t)song.g[G_SYNC] != lights_sync) lights_sync = 1; }\n")
    (tmp_path / "b").mkdir()
    (tmp_path / "b/engine.c").write_text("static void engine_block(void) { sq.sync_ext = par[PAR_BPM] <= 1u; }\n")
    (tmp_path / "c").mkdir()
    (tmp_path / "c/cr_out.c").write_text("static void cr_midi_in(void) { if (cr_cin_mode != cr_route.clock_in) { cr_cin_mode = cr_route.clock_in; } }\n"
                                         "void ui(void) { cr_route.clock_in = 1; }\n")
    run("patch", str(tmp_path / "a")); run("patch", str(tmp_path / "b")); run("patch", str(tmp_path / "c"))
    cr = (tmp_path / "c/cr_out.c").read_text()
    assert cr.count("(web_clock_ext || cr_route.clock_in)") == 2 and "cr_route.clock_in = 1;" in cr   # (ChoralRoot)
    seq = (tmp_path / "a/seq.c").read_text()
    assert seq.count("(web_clock_ext ? 1 : song.g[G_SYNC])") == 3
    assert "song.g[G_SYNC] = (int16_t)lights_sync;" in seq                        # (le réglage, jamais écrit par nous)
    assert "web_clock" not in (tmp_path / "a/project.c").read_text()              # (seulement le séquenceur, mclk_on)
    assert "sq.sync_ext = web_clock_ext || par[PAR_BPM] <= 1u;" in (tmp_path / "b/engine.c").read_text()


def test_worklet_forwards_clock(tmp_path):
    w = tmp_path / "worklet.js"
    w.write_text(
        "class Felucca extends AudioWorkletProcessor {\n"
        "  constructor() { super(); this.ex = null; this.port.onmessage = (e) => this.onMessage(e.data); }\n"
        "  onMessage(m) { if (m.type === 'load') this.ex = globalThis.__ex; }\n"
        "  process() { return true; }\n"
        "}\n"
        'registerProcessor("natif-felucca", Felucca);\n')
    assert "horloge du tempo lié" in run("worklet", str(w), "natif-felucca")
    js = ("let P; const calls = []; globalThis.registerProcessor = (n, c) => { P = c; };"
          "globalThis.AudioWorkletProcessor = class { constructor() { const l = []; this.port = { set onmessage(f) { l.push(f); },"
          "  addEventListener: (t, f) => l.push(f), fire: (d) => l.forEach((f) => f({ data: d })), postMessage: (m) => calls.push(m.type + m.on) }; } };"
          "globalThis.__ex = { web_clock: (on) => calls.push(on) };"
          "(0, eval)(require('fs').readFileSync(process.argv[1], 'utf8'));"
          "const p = new P({}); p.port.fire({ type: 'clock', on: true });"          # (avant le chargement : gardé)
          "p.process(); p.port.fire({ type: 'load' }); p.process(); p.process(); p.port.fire({ type: 'clock', on: false });"
          "console.log(JSON.stringify(calls));")
    out = subprocess.run(["node", "-e", js, str(w)], capture_output=True, text=True, check=True)
    assert out.stdout.strip() == '[1,"clocktrue",0,"clockfalse"]', out.stdout + out.stderr   # (et la réponse, une fois fait)
    assert run("worklet", str(w), "natif-felucca").startswith("worklet : horloge inchangée")
