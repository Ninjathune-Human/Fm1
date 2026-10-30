#!/usr/bin/env bash
# zp12 2.5 : son simulateur (sim/sim.c) inclut midi_uart.c, qui écrit les registres de l'UART de la prise TRS par
# leurs adresses (firmware/hal/fm1_uart.h, inclus par un chemin relatif : sim/hal ne peut pas le remplacer). En
# WebAssembly, ces adresses tombent dans la mémoire du programme, et l'instruction csync n'existe pas. Ici, les
# registres deviennent un tableau à part et csync une simple barrière : la prise TRS reste muette, le MIDI arrive
# par sim_midi (l'USB). Lancé à la racine du dépôt de zp12, avant sim/build.sh.
set -euo pipefail
F=firmware/hal/fm1_uart.h
sed -i -e 's/__asm__ volatile("csync" ::: "memory");/__asm__ volatile("" ::: "memory");/' \
       -e 's/(\*(volatile uint32_t \*)\(0x[0-9A-Fa-f]*u\))/(*(volatile uint32_t *)(fm1_mmio + \1))/' \
       -e 's/^#include "fm1_cc.h"$/#include "fm1_cc.h"\nstatic uint8_t fm1_mmio[0x52000] __attribute__((aligned(16)));/' "$F"
grep -q "fm1_mmio\[0x52000\]" "$F" && ! grep -q '"csync"' "$F" && ! grep -q '(volatile uint32_t \*)0x' "$F" || { echo "zp12 : fm1_uart.h n'a pas la forme attendue"; exit 1; }
echo "zp12 : registres de l'UART simulés ($F)"
# ses échantillons depuis le panneau : ce que fait son lien USB pour l'éditeur web (sp_link.c, RELOAD et ASSIGN),
# exporté du simulateur ; le reste (le répertoire, l'écriture des secteurs) est fait dans la flash simulée par
# tools/worklets/zp12.js avec web/zp12link.js de zp12
grep -q "sim_zl_reload" sim/sim.c || cat >> sim/sim.c <<'C'

/* (ajouté par le panneau FM-1+VA, tools/worklets/zp12_avant.sh) : sp_link.c's RELOAD and ASSIGN, for the samples
 * the page writes into the simulated flash */
EXPORT uint32_t sim_zl_reload(void)
{
    uint32_t i, n = 0;
    zu_load();
    for (i = 0; i < SP_NUSER; i++) n += sp_wave[KIT_NWAVE + i].n != 0u;
    ui_say(n ? "SAMPLES LOADED" : "NO SAMPLES");
    return n;
}
EXPORT uint32_t sim_zl_assign(uint32_t a)
{
    if (((a >> 8) & 63u) >= KIT_NWAVE + SP_NUSER || !sp_wave[(a >> 8) & 63u].n) return 2u;
    wave_set(a & 31u, (a >> 8) & 63u);
    return 0;
}
EXPORT uint32_t sim_zl_kit(void) { return KIT_NWAVE; }
C
grep -q "sim_zl_reload" sim/sim.c || { echo "zp12 : exports non ajoutés"; exit 1; }
echo "zp12 : RELOAD et ASSIGN exportés (sim/sim.c)"
