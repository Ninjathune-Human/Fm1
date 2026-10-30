#!/usr/bin/env bash
# Hortator : le simulateur de sa page (tools/build_sim.sh, étape 3), compilé par l'emcc de l'action plutôt que dans
# Docker, avec notre entrée MIDI (hortator_sim.c). Lancé à la racine du dépôt, après la génération des en-têtes
# (build/gen, par tools/build.py, que natif_build.sh lance).
#   tools/worklets/hortator.sh <sortie.wasm>
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
OUT=$1
GEN=build/gen
mkdir -p "$GEN" "$(dirname "$OUT")"
awk '/static const int8_t FM1_KEYMAP/,/^};/' firmware/hal/fm1_input.h > "$GEN/sim_keymap.h"
grep -q FM1_KEYMAP "$GEN/sim_keymap.h" || { echo "hortator : FM1_KEYMAP introuvable"; exit 1; }
VERSION=$(cat VERSION.txt 2>/dev/null || echo DEV)
EXPORTS=_sim_init,_sim_render,_sim_btn,_sim_key,_sim_enc,_sim_master,_sim_leds,_sim_key_leds,_sim_fb,_sim_audio,_sim_flash
EXPORTS=$EXPORTS,_sim_flash_reset,_sim_flash_dirty,_sim_flash_clean,_sim_playing,_sim_midi
emcc -O2 -sSTANDALONE_WASM --no-entry -sINITIAL_MEMORY=8MB -sSTACK_SIZE=256KB -sEXPORTED_FUNCTIONS="$EXPORTS" \
    -Wno-unused-function -Wno-int-to-pointer-cast -Wno-macro-redefined "-DFELUCCA_VERSION=\"DRUM-$VERSION\"" \
    -I"$GEN" -Ifirmware/src -Itests -o "$OUT" "$HERE/hortator_sim.c"
echo "hortator : $OUT ($(wc -c < "$OUT") octets)"
