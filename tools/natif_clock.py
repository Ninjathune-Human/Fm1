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
# (motif, remplacement) : chaque lecture du réglage, « 1 » (USB) tant que la page le demande
RULES = [
    # la famille Felucca : CLK (song.g[G_CLOCK] : 0 INT, 1 USB, 2 TRS), lu par le séquenceur à chaque bloc
    (re.compile(r"\b(clock_mode|selected_clock)\s*=\s*\(uint32_t\)song\.g\[G_CLOCK\];"),
     lambda m: f"{m.group(1)} = {FORCE} ? 1u : (uint32_t)song.g[G_CLOCK];"),
    # felucca-base (Duell) : CLK a aussi AUTO, lu par clock_src()
    (re.compile(r"(static uint32_t clock_src\(void\)\s*\{\s*uint32_t m = )\(uint32_t\)song\.g\[G_CLOCK\];"),
     lambda m: f"{m.group(1)}{FORCE} ? 1u : (uint32_t)song.g[G_CLOCK];"),
    # la famille Sloop (SPAMPY) : SYNC (song.g[G_SYNC] : 0 OFF, 1 USB, 2 TRS), lu par mclk_on et mclk_event
    (re.compile(r"(?<![&\w])song\.g\[G_SYNC\](?!\s*=[^=])"),
     lambda m: f"({FORCE} ? 1 : song.g[G_SYNC])"),
    # Elixir : le BPM réglé sur EXT, relu à chaque bloc
    (re.compile(r"\bsq\.sync_ext = par\[PAR_BPM\] <= 1u;"),
     lambda m: f"sq.sync_ext = {FORCE} || par[PAR_BPM] <= 1u;"),
    # Obervave, Shineon : SYNC AUTO (une horloge reçue mène) ou INTERNAL (elle est ignorée)
    (re.compile(r"\bif \(set\.sync_int && \(st == 0xF8u"),
     lambda m: f"if (set.sync_int && !{FORCE} && (st == 0xF8u"),
    # Mono2k : SYNC IN (OFF, USB, TRS, BOTH : les bits 1 USB, 2 TRS)
    (re.compile(r"(static inline int clk_from\(void\) \{ return )syin_choice\(store_\.set\[S_SYNI\]\);"),
     lambda m: f"{m.group(1)}{FORCE} ? 3 : syin_choice(store_.set[S_SYNI]);"),
    # Cutador : SYNC (project.par[P_SYNC] : 0 INT, 1 USB, 2 TRS), lu par son moteur (pas par l'annulation, qui compare)
    (re.compile(r"(?<![&\w.])project\.par\[P_SYNC\](?!\s*(=[^=]|!=\s*undo_project))"),
     lambda m: f"({FORCE} ? 1 : project.par[P_SYNC])"),
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
EXPORT = ('\n#pragma push_macro("__attribute__")\n#undef __attribute__\n'
          f'__attribute__((used, visibility("default"), weak, export_name("web_clock"))) void web_clock(int on) {{ {FORCE} = on != 0; }}'
          '   /* (FM-1 : le tempo lié du Duo) */\n#pragma pop_macro("__attribute__")\n')


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
        for rule, to in RULES:
            if rule is RULES[2][0] and not re.search(r"\bmclk_on\b", new):   # (SYNC : seulement le séquenceur de la famille Sloop)
                continue
            if rule is RULES[6][0] and not f.replace(os.sep, "/").endswith("/cad.c"):   # (Cutador : son moteur seulement)
                continue
            new = rule.sub(to, new)
        if new != text:                        # (un seul fichier le définit et l'exporte : beaucoup s'incluent les uns les autres)
            head = f"extern int {FORCE};\n" if done else f"int {FORCE};   /* (FM-1 : le tempo lié du Duo, web_clock) */\n"
            open(f, "w", encoding="utf-8").write(head + new + ("" if done else EXPORT))
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
