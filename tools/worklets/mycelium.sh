#!/usr/bin/env bash
# MYCELIUM : ses sources viennent dans une archive (Mycelium-FM1-1.0-Quellcode.zip) ; extraite, ses en-têtes générés
# (tools/build.py), puis son test d'interface compilé pour le navigateur par l'emcc de l'action, avec notre conduite
# (mycelium_sim.c). Lancé à la racine du dépôt.
#   tools/worklets/mycelium.sh <sortie.wasm>
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
OUT=$(mkdir -p "$(dirname "$1")" && cd "$(dirname "$1")" && pwd)/$(basename "$1")
rm -rf build/src && mkdir -p build/src
python3 -c 'import sys, zipfile; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])' Mycelium-FM1-1.0-Quellcode.zip build/src
cd build/src/mycelium-fm1
# son logo est rendu depuis un SVG (tools/gen_mycelium_logo.py : rsvg-convert), absent de l'image de l'action
command -v rsvg-convert >/dev/null || sudo apt-get install -y -q librsvg2-bin >/dev/null || {
  # (apt injoignable : resvg, par pip, derrière une commande du même nom ; le logo n'en diffère qu'aux bords lissés)
  python3 -m pip install -q resvg-py
  SHIM=$(mktemp -d)
  printf '%s\n' '#!/usr/bin/env python3' 'import sys, resvg_py' 'a = sys.argv[1:]' \
    'sys.stdout.buffer.write(bytes(resvg_py.svg_to_bytes(svg_path=a[-1], width=int(a[a.index("-w") + 1]))))' \
    > "$SHIM/rsvg-convert"
  chmod +x "$SHIM/rsvg-convert"; PATH="$SHIM:$PATH"
}
python3 -c "import importlib.util as u; s=u.spec_from_file_location('b','tools/build.py'); b=u.module_from_spec(s); s.loader.exec_module(b); b.generate()"
[ -f build/gen/felucca_tables.h ] || { echo "mycelium : en-têtes générés absents"; exit 1; }
EXPORTS=_sim_init,_sim_frame,_sim_render,_sim_btn,_sim_key,_sim_enc,_sim_master,_sim_midi,_sim_leds,_sim_fb,_sim_audio
emcc -O2 -sSTANDALONE_WASM --no-entry -sINITIAL_MEMORY=32MB -sALLOW_MEMORY_GROWTH=1 -sSTACK_SIZE=1MB \
    -sEXPORTED_FUNCTIONS="$EXPORTS" -ffp-contract=off -w -Wno-macro-redefined \
    -Ibuild/gen -Ifirmware/src -Ifirmware/hal -Itests -o "$OUT" "$HERE/mycelium_sim.c" -lm
echo "mycelium : $OUT ($(wc -c < "$OUT") octets)"
