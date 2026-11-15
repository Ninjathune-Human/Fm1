"""Le MIDI de la page jusqu'aux firmwares fm1-base dont le worklet, d'une version de fm1-base sans sa partie « midi »,
ne le lit pas : CTL-1, Del Rio, FRASIL, LOOM-8, MODELAR (protocole X0X), AMB-1, ECHOFIELD, Polly (protocole fm1-base).
Leur .wasm a déjà l'entrée, web_midi_in(port, paquet USB-MIDI), que la partie « midi » des versions plus récentes
appelle (GRAINE). Ce script ajoute au worklet la branche qui fait, de ce que la page envoie, un paquet du port USB :
{ type: "midi", b0, b1, b2 } en protocole X0X, { type: "app", part: "midi", data } en protocole fm1-base. Rien sans
cette entrée, ni pour un worklet qui lit déjà le MIDI. Le tempo lié du Duo en a besoin.
    python3 tools/natif_midi.py worklet <worklet.js publié> <.wasm> <dialecte>
"""
import sys

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


def worklet(path, wasm, dialect):
    if dialect not in FORMS or b"\x0bweb_midi_in" not in open(wasm, "rb").read():
        return                                     # (pas d'entrée MIDI dans le .wasm)
    s = open(path, encoding="utf-8").read()
    at, branch = FORMS[dialect]
    if 'type === "midi"' in s or 'name: "midi"' in s or "this.ex.web_master" not in s or s.count(at) != 1:
        return                                     # (il lit déjà le MIDI, ou ce n'est pas un worklet fm1-base)
    open(path, "w", encoding="utf-8").write(s.replace(at, branch + at))
    print("MIDI de la page ouvert (web_midi_in)")


if __name__ == "__main__" and sys.argv[1:2] == ["worklet"]:
    worklet(*sys.argv[2:5])
