#!/usr/bin/env bash
# Cut-A-Dor : son moteur (cad.c) et son interface (app/ui.c) compilés pour le navigateur par l'emcc de l'action,
# avec notre plateforme (cutador_sim.c). Lancé à la racine du dépôt ; ses en-têtes générés sont dans build/gen.
#   tools/worklets/cutador.sh <sortie.wasm>
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
OUT=$1
mkdir -p "$(dirname "$OUT")"
[ -f build/gen/felucca_font.h ] || { echo "cutador : build/gen absent"; exit 1; }
EXPORTS=_sim_init,_sim_store,_sim_store_len,_sim_store_size,_sim_block,_sim_btn,_sim_key,_sim_enc,_sim_master,_sim_midi
EXPORTS=$EXPORTS,_sim_frame,_sim_render,_sim_fb,_sim_leds
emcc -O2 -sSTANDALONE_WASM --no-entry -sINITIAL_MEMORY=16MB -sSTACK_SIZE=512KB -sEXPORTED_FUNCTIONS="$EXPORTS" \
    -DEN_HOST -std=c11 -ffp-contract=off -w -Ibuild/gen -Ifirmware/src -Ifirmware/src/dsp \
    -o "$OUT" "$HERE/cutador_sim.c" firmware/src/dsp/cad.c
echo "cutador : $OUT ($(wc -c < "$OUT") octets)"
