#!/usr/bin/env bash
# SPAMPY : son test d'interface compilé pour le navigateur par l'emcc de l'action, avec notre conduite
# (spampy_sim.c). Lancé à la racine du dépôt. Les sources de SPAMPY 1.0 (r1007) ne sont que dans l'archive de sa
# version (SOURCE.zip, sans tests/) : extraite, les tests du dépôt posés dessus, ses en-têtes générés (tools/build.py).
#   tools/worklets/spampy.sh <sortie.wasm> [URL de l'archive des sources]
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
OUT=$(mkdir -p "$(dirname "$1")" && cd "$(dirname "$1")" && pwd)/$(basename "$1")
if [ -n "${2:-}" ]; then
  rm -rf build/src && mkdir -p build/src
  curl -sSL -o build/src.zip "$2"
  python3 -c 'import sys, zipfile; z = zipfile.ZipFile(sys.argv[1]); z.extractall(sys.argv[2], [n for n in z.namelist() if not n.startswith("__MACOSX")])' build/src.zip build/src
  ROOT=$(find build/src -mindepth 1 -maxdepth 1 -type d | head -1)
  cp -r tests "$ROOT/"
  cd "$ROOT"
fi
python3 "$HERE/../natif_clock.py" patch . | sed "s/^/spampy : /"   # (le tempo lié du Duo : ces sources-ci, extraites après)
python3 -c "import importlib.util as u; s=u.spec_from_file_location('b','tools/build.py'); b=u.module_from_spec(s); s.loader.exec_module(b); b.generate()"
[ -f build/gen/felucca_tables.h ] || { echo "spampy : en-têtes générés absents"; exit 1; }
EXPORTS=_sim_init,_sim_frame,_sim_render,_sim_btn,_sim_key,_sim_enc,_sim_master,_sim_midi,_sim_leds,_sim_fb,_sim_audio
emcc -O2 -sSTANDALONE_WASM --no-entry -sINITIAL_MEMORY=32MB -sALLOW_MEMORY_GROWTH=1 -sSTACK_SIZE=1MB \
    -sEXPORTED_FUNCTIONS="$EXPORTS" -ffp-contract=off -w -Wno-macro-redefined \
    -Ibuild/gen -Ifirmware/src -Ifirmware/hal -Itests -o "$OUT" "$HERE/spampy_sim.c" -lm
echo "spampy : $OUT ($(wc -c < "$OUT") octets)"
