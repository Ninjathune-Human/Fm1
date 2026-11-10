#!/usr/bin/env python3
"""Le tempo lié du Duo sans réglage : la page met l'horloge d'un firmware natif sur la sienne, puis la lui rend. Lancé par
natif_build.sh :
  natif_clock.py patch <dépôt>         avant la compilation : là où le firmware lit son réglage d'horloge, « suivre l'USB »
                                       tant que la page le demande (web_clock(1)) ; le réglage lui-même n'est jamais écrit
                                       (il reste celui des projets et des sauvegardes), web_clock(0) rend le sien
  natif_clock.py worklet <worklet.js> <processeur>   après : un message { type: "clock", on } appelle web_clock, et le
                                       worklet répond { type: "clock", on } une fois fait

Le MIDI de la page arrive à ces firmwares comme par l'USB (source 1)."""
import os, re, sys

SKIP = {"third_party", "node_modules", "vendor", "tests", "test", ".git", "build", "ref", "reference"}
FORCE = "web_clock_ext"
# (fichiers, motif, remplacement) : chaque lecture du réglage, « l'horloge reçue » tant que la page le demande
GCLOCK = re.compile(r"(?<![&\w.])song\.g\[G_CLOCK\](?!\s*=[^=])")
RULES = [
    # la famille Felucca : CLK (song.g[G_CLOCK] : 0 INT, 1 USB, 2 TRS ; felucca-base, Duell, 3 AUTO), lu par son séquenceur et
    # son horloge ; USB plutôt qu'AUTO (qui ne prend un port qu'après ses premières impulsions : le Start de la page passerait)
    (lambda f, t: os.path.basename(f) in ("seq.c", "midi_clock.c"), GCLOCK,
     lambda m, t: f"({FORCE} ? 1 : song.g[G_CLOCK])"),
    # la famille Sloop (SPAMPY) : SYNC (song.g[G_SYNC] : 0 OFF, 1 USB, 2 TRS), lu par mclk_on et mclk_event
    (lambda f, t: re.search(r"\bmclk_on\b", t), re.compile(r"(?<![&\w])song\.g\[G_SYNC\](?!\s*=[^=])"),
     lambda m, t: f"({FORCE} ? 1 : song.g[G_SYNC])"),
    # Elixir : le BPM réglé sur EXT, relu à chaque bloc
    (None, re.compile(r"\bsq\.sync_ext = par\[PAR_BPM\] <= 1u;"),
     lambda m, t: f"sq.sync_ext = {FORCE} || par[PAR_BPM] <= 1u;"),
    # Obervave, Shineon : SYNC AUTO (une horloge reçue mène) ou INTERNAL (elle est ignorée)
    (None, re.compile(r"\bif \(set\.sync_int && \(st == 0xF8u"),
     lambda m, t: f"if (set.sync_int && !{FORCE} && (st == 0xF8u"),
    # Mono2k : SYNC IN (OFF, USB, TRS, BOTH : les bits 1 USB, 2 TRS)
    (None, re.compile(r"(static inline int clk_from\(void\) \{ return )syin_choice\(store_\.set\[S_SYNI\]\);"),
     lambda m, t: f"{m.group(1)}{FORCE} ? 3 : syin_choice(store_.set[S_SYNI]);"),
    # ChoralRoot (son propre séquenceur, pas celui de Felucca) : CLOCK IN, lu par cr_midi_in ; CoralFlower, par cf_out.c
    (lambda f, t: os.path.basename(f) == "cr_out.c", re.compile(r"(?<![&\w.])cr_route\.clock_in(?!\s*=[^=])"),
     lambda m, t: f"({FORCE} || cr_route.clock_in)"),
    (lambda f, t: os.path.basename(f) == "cf_out.c", re.compile(r"(?<![&\w.])cfp_cfg\.clock_in(?!\s*=[^=])"),
     lambda m, t: f"({FORCE} || cfp_cfg.clock_in)"),
    # Cutador : SYNC (project.par[P_SYNC] : 0 INT, 1 USB, 2 TRS), lu par son moteur (pas par l'annulation, qui compare)
    (lambda f, t: f.replace(os.sep, "/").endswith("/cad.c"),
     re.compile(r"(?<![&\w.])project\.par\[P_SYNC\](?!\s*(=[^=]|!=\s*undo_project))"),
     lambda m, t: f"({FORCE} ? 1 : project.par[P_SYNC])"),
]
# Berlin : son mode d'horloge (rt.ext) ne change qu'à l'arrêt, par rt_set_sync, qui remet son moteur en ordre : web_clock
# l'appelle, et lui rend son propre mode au déliage
BERLIN = re.compile(r"^void rt_set_sync\(int ext\)", re.M)
BERLIN_EXPORT = ('\nstatic int web_clock_was = -1;   /* (FM-1 : le tempo lié du Duo ; son propre mode, rendu au déliage) */\n'
                 '#pragma push_macro("__attribute__")\n#undef __attribute__\n'
                 '__attribute__((used, visibility("default"), weak, export_name("web_clock"))) void web_clock(int on)\n'
                 '{\n    if (on) { if (web_clock_was < 0) web_clock_was = rt.ext; rt_set_sync(1); }\n'
                 '    else if (web_clock_was >= 0) { rt_set_sync(web_clock_was); web_clock_was = -1; }\n}\n'
                 '#pragma pop_macro("__attribute__")\n')
# en tête de chaque fichier modifié, une fois par unité de compilation (beaucoup s'incluent les uns les autres, et certains
# ne sont pas compilés, comme le séquenceur de Felucca sous ChoralRoot) : faibles, d'une unité à l'autre ils n'en font qu'un
HEAD = ('#ifndef FM1_WEB_CLOCK   /* (FM-1 : le tempo lié du Duo, web_clock ; tools/natif_clock.py) */\n#define FM1_WEB_CLOCK\n'
        '#pragma push_macro("__attribute__")\n#undef __attribute__\n'
        f'__attribute__((weak)) int {FORCE};\n'
        f'__attribute__((used, visibility("default"), weak, export_name("web_clock"))) void web_clock(int on) {{ {FORCE} = on != 0; }}\n'
        '#pragma pop_macro("__attribute__")\n#endif\n')


def sources(root):
    for d, dirs, names in os.walk(root):
        dirs[:] = [x for x in dirs if x not in SKIP]
        p = d.replace(os.sep, "/")
        if "/web/" in p + "/" or "/host/" in p + "/":   # (le séquenceur de l'appareil, que la version navigateur inclut)
            continue
        yield from (os.path.join(d, n) for n in names if n.endswith(".c"))


def patch(root):
    done = []
    for f in sources(root):
        text = open(f, encoding="utf-8", errors="replace").read()
        if FORCE in text or "web_clock_was" in text:
            continue
        if BERLIN.search(text) and "rt.ext = ext ? 1 : 0;" in text and not done:
            open(f, "w", encoding="utf-8").write(text + BERLIN_EXPORT)
            done.append(f.replace(os.sep, "/"))
            continue
        new = text
        for where, rule, to in RULES:
            if where is None or where(f, text):
                new = rule.sub(lambda m: to(m, text), new)
        if new != text:
            open(f, "w", encoding="utf-8").write(HEAD + new)
            done.append(f.replace(os.sep, "/"))
    return done


WRAP = ('const __fm1Clock = (C) => class extends C {   /* (FM-1) le tempo lié du Duo : { type: "clock", on } appelle web_clock */\n'
        '  constructor(o) { super(o); this.port.addEventListener("message", (e) => { if (e.data && e.data.type === "clock") { this.__clk = e.data.on ? 1 : 0; this.__fm1Clk(); } }); }\n'
        '  __fm1Clk() { for (const v of Object.values(this)) { const x = v && typeof v.web_clock === "function" ? v : v && v.exports && typeof v.exports.web_clock === "function" ? v.exports : null;\n'
        '    if (x) { x.web_clock(this.__clk); this.port.postMessage({ type: "clock", on: !!this.__clk }); this.__clk = undefined; return; } } }\n'
        '  process(i, o, p) { if (this.__clk !== undefined) this.__fm1Clk(); return super.process(i, o, p); }\n'
        '};\n')


def worklet(f, name):
    text = open(f, encoding="utf-8").read()
    reg = re.compile(r'registerProcessor\("' + re.escape(name) + r'",\s*([A-Za-z_$][\w$]*)\s*\)')
    if "__fm1Clock" in text or not reg.search(text):
        return False
    text = WRAP + reg.sub(lambda m: f'registerProcessor("{name}", __fm1Clock({m.group(1)}))', text, count=1)
    open(f, "w", encoding="utf-8").write(text)
    return True


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "patch":
        for p in patch(sys.argv[2]):
            print("horloge du tempo lié :", p)
    elif len(sys.argv) > 3 and sys.argv[1] == "worklet":
        print("worklet : horloge du tempo lié" if worklet(sys.argv[2], sys.argv[3]) else "worklet : horloge inchangée")
    else:
        sys.exit("natif_clock.py patch <dépôt> | worklet <worklet.js> <processeur>")
