#!/usr/bin/env bash
# GATOR : son simulateur d'hôte (host/sim.c et l'appli, Plaits en C++) compilé pour le navigateur par l'emcc de
# l'action, avec notre conduite (gator_sim.c). Lancé à la racine du dépôt, après tools/build.py (natif_build.sh),
# dont on refait les tables à 44,1 kHz.
#   tools/worklets/gator.sh <sortie.wasm>
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
OUT=$1
GEN=build/gen APP=firmware/apps/gator
mkdir -p "$GEN" "$(dirname "$OUT")" build/natif/obj
python3 tools/gen_tables.py "$GEN/fw_tables.h" 44
[ -f "$GEN/felucca_font.h" ] && [ -f "$GEN/fw_logo.h" ] || { echo "gator : en-têtes générés absents (tools/build.py)"; exit 1; }
NAME=$(tr -d '\r\n' < "$APP/name.txt" 2>/dev/null || echo GATOR)
FLAGS=(-O2 -DFW_HOST -DFW_FS48=0 "-DFW_NAME=\"$NAME\"" '-DFW_VERSION="0.6"' -ffp-contract=off -w)
OBJS=()
for d in "$APP" $(cat "$APP/third_party.txt" 2>/dev/null); do
  for s in $(find "$d" -name '*.cc' | sort); do
    o=build/natif/obj/$(echo "$s" | tr / _).o
    em++ "${FLAGS[@]}" -std=c++11 -DTEST -fno-exceptions -fno-rtti -I"$APP" -Ifirmware/sys -Ithird_party/eurorack -c "$s" -o "$o"
    OBJS+=("$o")
  done
done
EXPORTS=_sim_init,_sim_store,_sim_store_len,_sim_store_size,_sim_block,_sim_btn,_sim_key,_sim_enc,_sim_master,_sim_midi
EXPORTS=$EXPORTS,_sim_frame,_sim_render,_sim_fb,_sim_leds
emcc "${FLAGS[@]}" -std=c11 -c -Ihost -Ifirmware/sys -I"$APP" -I"$GEN" "$HERE/gator_sim.c" -o build/natif/obj/gator_sim.o
em++ -O2 -sSTANDALONE_WASM --no-entry -sINITIAL_MEMORY=16MB -sSTACK_SIZE=512KB -sEXPORTED_FUNCTIONS="$EXPORTS" \
    -o "$OUT" build/natif/obj/gator_sim.o "${OBJS[@]}"
echo "gator : $OUT ($(wc -c < "$OUT") octets, ${#OBJS[@]} fichiers C++)"
