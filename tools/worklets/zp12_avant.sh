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
