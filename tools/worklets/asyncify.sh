#!/usr/bin/env bash
# Compile un firmware écrit pour une page Emscripten (sa boucle rend la main par emscripten_sleep) en WebAssembly
# pour notre worklet tools/worklets/asyncify.js : Zig (wasm32-wasi, en bibliothèque), notre emscripten.h, puis la
# passe Asyncify de Binaryen sur emscripten_sleep. Lancé à la racine du dépôt du firmware.
#   tools/worklets/asyncify.sh <sortie.wasm> <options du compilateur et sources…>
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
OUT=$1; shift
ZIG=${ZIG:-zig}
WASM_OPT=${WASM_OPT:-wasm-opt}
mkdir -p "$(dirname "$OUT")"
$ZIG cc -target wasm32-wasi -mexec-model=reactor -O2 -g0 -w -I"$HERE/shim" "$@" \
    -Wl,--strip-debug -Wl,--export-dynamic -Wl,--export=__main_void -Wl,--export=malloc -Wl,-z,stack-size=1048576 -o "$OUT.brut"
$WASM_OPT "$OUT.brut" --enable-bulk-memory --enable-nontrapping-float-to-int --enable-sign-ext --enable-mutable-globals \
    --asyncify --pass-arg=asyncify-imports@env.emscripten_sleep -O2 -o "$OUT"
rm -f "$OUT.brut"
echo "asyncify : $OUT ($(wc -c < "$OUT") octets)"
