#!/usr/bin/env bash
# Melodee : son test d'interface (tests/ui_test.c) compilé pour le navigateur par l'emcc de l'action, avec notre
# conduite (melodee_sim.c). Lancé à la racine du dépôt, après la génération des en-têtes (build/gen, par
# tools/build.py, que natif_build.sh lance).
#   tools/worklets/melodee.sh <sortie.wasm>
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
OUT=$1
GEN=build/gen
mkdir -p "$GEN" "$(dirname "$OUT")"
[ -f "$GEN/melodee_tables.h" ] || { echo "melodee : en-têtes générés absents (tools/build.py)"; exit 1; }
awk '/static const int8_t FM1_KEYMAP/,/^};/' firmware/hal/fm1_input.h > "$GEN/sim_keymap.h"
grep -q FM1_KEYMAP "$GEN/sim_keymap.h" || { echo "melodee : FM1_KEYMAP introuvable"; exit 1; }
EXPORTS=_sim_init,_sim_frame,_sim_render,_sim_btn,_sim_key,_sim_enc,_sim_master,_sim_midi,_sim_leds,_sim_fb,_sim_audio
emcc -O2 -sSTANDALONE_WASM --no-entry -sINITIAL_MEMORY=32MB -sALLOW_MEMORY_GROWTH=1 -sSTACK_SIZE=1MB \
    -sEXPORTED_FUNCTIONS="$EXPORTS" -ffp-contract=off -w -Wno-macro-redefined \
    -DMELODEE_USB_AUDIO=1 -I"$GEN" -Ifirmware/src -Itests -o "$OUT" "$HERE/melodee_sim.c" -lm
echo "melodee : $OUT ($(wc -c < "$OUT") octets)"
