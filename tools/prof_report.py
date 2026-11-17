"""Résume un profil node (.cpuprofile) : le temps propre par module wasm (le cœur, le code compilé à la volée) et, pour le cœur,
par fonction.   python3 tools/prof_report.py profil.cpuprofile"""
import json, sys, collections
p = json.load(open(sys.argv[1]))
nodes = {n["id"]: n for n in p["nodes"]}
dt = p["timeDeltas"]; own = collections.Counter()
for s, d in zip(p["samples"], dt):
    own[s] += d
tot = sum(own.values()) or 1
mod = collections.Counter(); fn = collections.Counter()
for i, t in own.items():
    c = nodes[i]["callFrame"]; url = c.get("url", ""); name = c.get("functionName", "") or "(anon)"
    if url.startswith("wasm://"):
        m = "wasm-compilé-à-la-volée" if "wasm-function" in name and len(url) > 0 and name.startswith("wasm-function") else "wasm-cœur"
        mod[m] += t
        fn[name] += t
    else:
        mod["js:" + (url.rsplit("/", 1)[-1] or name)] += t
print("modules :", {k: f"{v / tot * 100:.1f} %" for k, v in mod.most_common(6)})
print("fonctions :", [(k[:70], f"{v / tot * 100:.1f} %") for k, v in fn.most_common(16)])
