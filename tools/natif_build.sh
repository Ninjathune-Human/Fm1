#!/usr/bin/env bash
# Compile un firmware depuis ses sources pour le navigateur, avec le script de son auteur, puis prépare
# natif/<id>/ pour le panneau. Lancé par l'action GitHub, un firmware par tâche.
#   tools/natif_build.sh <id> <dossier du dépôt du firmware> <script de compilation> <dossier de sortie>
# Sortie : <sortie>/<id>/{<nom>.wasm, worklet.js, LICENSE.txt, natif.json}, ou rien si la compilation échoue
# ou si le worklet ne parle pas un des deux protocoles connus (Felucca, X0X).
set -uo pipefail
ID=$1 REPO=$(cd "$2" && pwd) SCRIPT=$3 OUT=$4
mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd)
cd "$REPO"
touch /tmp/natif-start; sleep 1

# en-têtes générés, pour les firmwares de la famille Felucca qui les demandent (polices, tables, échantillons)
if [ -f tools/build.py ] && grep -q "def generate" tools/build.py; then
  python3 -c "import importlib.util as u; s=u.spec_from_file_location('b','tools/build.py'); b=u.module_from_spec(s); s.loader.exec_module(b); b.generate()" \
    || echo "natif $ID : génération des en-têtes en échec (on continue)"
fi

EMU_PREVIEW=0 bash "$SCRIPT" || { echo "natif $ID : la compilation a échoué"; exit 0; }

CANDIDATS=$(find . -name node_modules -prune -o -name '*.wasm' -newer /tmp/natif-start -print)
[ -n "$CANDIDATS" ] || { echo "natif $ID : aucun .wasm produit"; exit 0; }
WASM="" WORKLET=""
for w in $CANDIDATS; do                    # de préférence le .wasm qui a son worklet à côté
  k=$(ls "$(dirname "$w")"/worklet*.js 2>/dev/null | head -1)
  if [ -n "$k" ]; then WASM=$w WORKLET=$k; break; fi
done
if [ -z "$WASM" ]; then WASM=$(echo "$CANDIDATS" | head -1); WORKLET=$(ls "$(dirname "$SCRIPT")"/worklet*.js 2>/dev/null | head -1); fi
echo "natif $ID : .wasm produits : $(echo $CANDIDATS)"
[ -n "$WORKLET" ] || { echo "natif $ID : pas de worklet à côté du .wasm"; exit 0; }

if grep -q 'msg.leds' "$WORKLET" && grep -q 'type === "buttons"' "$WORKLET"; then DIALECT=felucca
elif grep -q 'web_lit_buttons() >>> 0, keys' "$WORKLET" && grep -q 'type === "buttons"' "$WORKLET"; then DIALECT=x0x
else echo "natif $ID : protocole du worklet inconnu"; exit 0; fi

D="$OUT/$ID"; mkdir -p "$D"
cp "$WASM" "$D/"
cp "$WORKLET" "$D/worklet.js"
# les modules que le worklet importe à côté de lui (import … from "./x.js"), sur deux niveaux
for f in "$WORKLET" $(grep -oE "from \"\./[^\"]+\.js\"" "$WORKLET" | sed -E 's/from "\.\/(.*)"/\1/' | sed "s#^#$(dirname "$WORKLET")/#"); do
  for m in $(grep -oE "from \"\./[^\"]+\.js\"" "$f" | sed -E 's/from "\.\/(.*)"/\1/'); do
    cp "$(dirname "$WORKLET")/$m" "$D/$m" || echo "natif $ID : module $m introuvable"
  done
done
LIC=$(ls LICENSE LICENSE.* COPYING 2>/dev/null | head -1); [ -n "$LIC" ] && cp "$LIC" "$D/LICENSE.txt"
# deux modifications, seulement : un nom de processeur propre à ce firmware (plusieurs dans la même page),
# et l'écran publié 60 fois par seconde au lieu de 30
sed -i -E "s/registerProcessor\(\"[^\"]+\"/registerProcessor(\"natif-$ID\"/" "$D/worklet.js"
sed -i 's#1 / 30#1 / 60#g' "$D/worklet.js"
# TextDecoder manque dans le fil audio de Chrome : quelques worklets s'en servent au chargement
sed -i '1i globalThis.TextDecoder ??= class { decode(b) { let s = ""; for (const c of b || []) s += String.fromCharCode(c); try { return decodeURIComponent(escape(s)); } catch (e) { return s; } } };' "$D/worklet.js"
grep -q "registerProcessor(\"natif-$ID\"" "$D/worklet.js" || { echo "natif $ID : nom de processeur introuvable"; rm -rf "$D"; exit 0; }
printf '{"wasm": "%s", "processeur": "natif-%s", "dialecte": "%s"}\n' "$(basename "$WASM")" "$ID" "$DIALECT" > "$D/natif.json"
echo "natif $ID : prêt ($DIALECT, $(basename "$WASM"), $(wc -c < "$WASM") octets)"
