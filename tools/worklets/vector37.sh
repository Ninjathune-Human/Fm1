#!/usr/bin/env bash
# VECTOR37 : sa version FM-1 (BOARD=fm1) sur le FM-1 simulé de ses tests d'hôte (tests/panel.h, BOARD_SMK37 0),
# compilée pour le navigateur par l'emcc de l'action avec notre conduite (vector37_sim.c) ; son simulateur web (web/sim)
# est celui du SMK-37. Ses en-têtes générés d'abord, comme web/sim/build.sh. Lancé à la racine du dépôt.
#   tools/worklets/vector37.sh <sortie.wasm> <version>
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
OUT=$(mkdir -p "$(dirname "$1")" && cd "$(dirname "$1")" && pwd)/$(basename "$1")
VERSION=$2
mkdir -p build/gen
python3 tools/gen_tables.py build/gen/mk_tables.h >/dev/null
[ -f build/gen/felucca_font.h ] || python3 tools/gen_font.py build/gen/felucca_font.h >/dev/null
EXPORTS=_sim_init,_sim_render,_sim_out_l,_sim_out_r,_sim_fb,_sim_btn,_sim_key,_sim_enc,_sim_master,_sim_midi,_sim_leds
emcc -O2 -std=gnu11 -w -sSTANDALONE_WASM --no-entry -sSTACK_SIZE=1048576 -sINITIAL_MEMORY=33554432 -sFILESYSTEM=0 \
    -sEXPORTED_FUNCTIONS="$EXPORTS" "-DMK_VERSION=\"$VERSION\"" -Ibuild/gen -Itests -o "$OUT" "$HERE/vector37_sim.c"
echo "vector37 : $OUT ($(wc -c < "$OUT") octets)"
