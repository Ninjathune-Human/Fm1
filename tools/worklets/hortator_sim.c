/* SPDX-License-Identifier: GPL-3.0-only
 * Hortator (deadactive/hortator, GPL-3.0) pour le panneau : son simulateur (tests/sim_core.c, inchangé) et une
 * entrée MIDI, que sa page n'a pas. Un message arrive comme usb_app8.c range un paquet USB-MIDI : l'horloge et
 * Start / Continue / Stop en code 0xF, les messages de canal sur leur propre code. */
#include "sim_core.c"

uint32_t sim_midi(uint32_t st, uint32_t d1, uint32_t d2)
{
    if (st == 0xF8u || st == 0xFAu || st == 0xFBu || st == 0xFCu)
        return (uint32_t)midi_enqueue(0xFu | st << 8, 1u);
    if (st < 0x80u || st >= 0xF0u)
        return 1u;
    return (uint32_t)midi_enqueue((st >> 4) | st << 8 | (d1 & 127u) << 16 | (d2 & 127u) << 24, 1u);
}
