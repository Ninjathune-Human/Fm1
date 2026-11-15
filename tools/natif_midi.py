"""Le MIDI de la page jusqu'aux firmwares natifs dont la version navigateur ne le lit pas. Le tempo lié du Duo en a besoin.

Après la compilation, les firmwares fm1-base dont le worklet, d'une version de fm1-base sans sa partie « midi », ne le lit
pas : CTL-1, Del Rio, FRASIL, LOOM-8, MODELAR (protocole X0X), AMB-1, ECHOFIELD, Polly (protocole fm1-base). Leur .wasm a
déjà l'entrée, web_midi_in(port, paquet USB-MIDI), que la partie « midi » des versions plus récentes appelle (GRAINE). Ce
script ajoute au worklet la branche qui fait, de ce que la page envoie, un paquet du port USB : { type: "midi", b0, b1, b2 }
en protocole X0X, { type: "app", part: "midi", data } en protocole fm1-base. Rien sans cette entrée, ni pour un worklet
qui lit déjà le MIDI. Le worklet de BERLINAN (protocole X0X) lit, lui, des paquets : il reçoit aussi les octets.
    python3 tools/natif_midi.py worklet <worklet.js publié> <.wasm> <dialecte>

Avant la compilation, les versions navigateur des familles X0X (X0X, X0X RMX, FOMNI, MIN-1) et AMB (DUB-1,
NACHTFAHRT, DARK-1, HYP-1, PERF-1), dont le simulateur a une file d'entrée MIDI (plat_midi_in) que leur page ne remplit
pas : le harnais (web/emu/*_web.c) exporte web_midi_in(port, paquet), qui la remplit comme le port USB de l'appareil ;
leur worklet, de la même forme que ceux de fm1-base, reçoit ensuite la branche ci-dessus. (TRIBE n'a pas de file : son
moteur ne lit pas le MIDI.) Tessera (web/sim) : son web_midi passe par midi_enqueue, qui date le paquet pour l'horloge.
    python3 tools/natif_midi.py patch <dépôt>
"""
import glob, os, re, sys

PACKET = ('      const cin = s >= 0xF8 ? 0xF : s >= 0x80 && s < 0xF0 ? s >> 4 : 0;\n'
          '      if (cin) this.ex.web_midi_in(0, (cin | s << 8 | (b1 & 0x7F) << 16 | (b2 & 0x7F) << 24) >>> 0);\n')
FORMS = {
    "x0x": ('    } else if (m.type === "master") {\n',
            '    } else if (m.type === "midi") {   // (Fm1, tools/natif_midi.py) un paquet USB-MIDI, port USB\n'
            '      const s = m.b0 & 0xFF, b1 = m.b1, b2 = m.b2;\n' + PACKET),
    "base": ('    } else if (m.type === "app" && this.app.message) {\n',
             '    } else if (m.type === "app" && m.part === "midi") {   // (Fm1, tools/natif_midi.py) un paquet USB-MIDI, port USB\n'
             '      const s = m.data[0] & 0xFF, b1 = m.data[1] | 0, b2 = m.data[2] | 0;\n' + PACKET),
}

QUEUE = "static uint32_t min_q[MQ], mi_w, mi_r;"
EXPORT = """
/* (Fm1, tools/natif_midi.py) le MIDI de la page dans la file d'entrée du simulateur, comme par le port USB */
#pragma push_macro("__attribute__")
#undef __attribute__
__attribute__((used, visibility("default"))) void web_midi_in(uint32_t port, uint32_t pkt)
{
    (void)port;
    if (mi_w - mi_r < MQ) min_q[mi_w++ % MQ] = pkt;
}
#pragma pop_macro("__attribute__")
"""


PKTS = "for (const p of m.pkts) this.ex.web_midi_in(m.port | 0, p >>> 0);"
PKTS_X0X = ("for (const p of m.pkts || [m.b0 >= 0xF8 ? 0xF | m.b0 << 8 : (m.b0 & 0xFF) >> 4 | (m.b0 & 0xFF) << 8 | (m.b1 & 0x7F) << 16 | (m.b2 & 0x7F) << 24]) "
            "this.ex.web_midi_in(m.port | 0, p >>> 0);   // (Fm1, tools/natif_midi.py) ou les octets du protocole X0X")


def worklet(path, wasm, dialect):
    s = open(path, encoding="utf-8").read()
    if dialect == "x0x" and s.count(PKTS) == 1:     # BERLINAN : lit des paquets, la page lui envoie les octets
        open(path, "w", encoding="utf-8").write(s.replace(PKTS, PKTS_X0X))
        print("MIDI de la page en paquets (web_midi_in)")
        return
    if dialect not in FORMS or b"\x0bweb_midi_in" not in open(wasm, "rb").read():
        return                                     # (pas d'entrée MIDI dans le .wasm)
    s = open(path, encoding="utf-8").read()
    at, branch = FORMS[dialect]
    if 'type === "midi"' in s or 'name: "midi"' in s or "this.ex.web_master" not in s or s.count(at) != 1:
        return                                     # (il lit déjà le MIDI, ou ce n'est pas un worklet de cette forme)
    open(path, "w", encoding="utf-8").write(s.replace(at, branch + at))
    print("MIDI de la page ouvert (web_midi_in)")


BARE = ("    midi_in_q[mi_w % MQ] = (status >> 4) | status << 8 | (d1 & 127u) << 16 | (d2 & 127u) << 24;\n"
        "    mi_w++;\n    return 1;\n")
ENQUEUE = "    return (uint32_t)midi_enqueue((status >> 4) | status << 8 | (d1 & 127u) << 16 | (d2 & 127u) << 24, 1u);   /* (Fm1, tools/natif_midi.py) */\n"


def patch(root):
    # Tessera (web/sim) : web_midi pose le paquet seul dans la file, sans l'heure ni le port que l'horloge MIDI y lit ;
    # midi_enqueue, celle du port USB (usb.c, dans le même fichier compilé), les y met
    usb = os.path.join(root, "firmware", "src", "usb.c")
    if os.path.exists(usb) and "static int midi_enqueue(uint32_t pkt, uint32_t source)" in open(usb, encoding="utf-8").read():
        for h in sorted(glob.glob(os.path.join(root, "web", "sim", "*.c"))):
            text = open(h, encoding="utf-8").read()
            if text.count(BARE) == 1:
                open(h, "w", encoding="utf-8").write(text.replace(BARE, ENQUEUE))
                print(f"MIDI par la file du port USB ({os.path.relpath(h, root)})")
    for h in sorted(glob.glob(os.path.join(root, "web", "emu", "*_web.c"))):
        text = open(h, encoding="utf-8").read()
        m = re.search(r'#include "([^"]*host[^"]*\.c)"', text)
        if "web_midi_in" in text or not m:
            continue
        host = os.path.normpath(os.path.join(os.path.dirname(h), m.group(1)))
        if os.path.exists(host) and QUEUE in open(host, encoding="utf-8").read():
            open(h, "a", encoding="utf-8").write(EXPORT)
            print(f"entrée MIDI exportée ({os.path.relpath(h, root)})")


if __name__ == "__main__" and sys.argv[1:2] == ["worklet"]:
    worklet(*sys.argv[2:5])
elif __name__ == "__main__" and sys.argv[1:2] == ["patch"]:
    patch(sys.argv[2])
