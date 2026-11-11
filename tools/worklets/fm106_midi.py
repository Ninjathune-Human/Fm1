#!/usr/bin/env python3
"""FM-106 (PatttF/fm-106) : la file MIDI de sa version navigateur (web/emu/fm106_web.c). L'index d'écriture y est
ramené à 0..255 à chaque message ((midi_w + 1u) & 255u), celui de lecture non : après 256 messages, ils ne se
rejoignent plus, et le firmware relit sa file en boucle sans plus rien recevoir (au tempo lié du Duo, l'horloge en
envoie 48 par seconde : au bout de 5 s, un Start ne le lance plus). Les deux indices comptent désormais sans fin,
masqués seulement pour lire la file, comme ceux du firmware sur l'appareil. Lancé à la racine de son dépôt, avant
la compilation (NATIF_AVANT, tools/natif.json)."""
import sys

F = "web/emu/fm106_web.c"
OLD = ("    uint32_t next = (midi_w + 1u) & 255u;\n"
       "    if (next == (midi_r & 255u)) return 0; /* full */\n")
NEW = "    if (midi_w - midi_r >= 255u) return 0; /* full */\n"

text = open(F, encoding="utf-8").read()
if OLD not in text or "    midi_w = next;\n" not in text:
    sys.exit(f"fm106_midi.py : {F} n'a plus la file attendue")
text = text.replace(OLD, NEW).replace("    midi_w = next;\n", "    midi_w++;\n", 1)
open(F, "w", encoding="utf-8").write(text)
print("fm106 : file MIDI de la version navigateur corrigée")
