"""Accélère le cœur fm1-emu sans rien changer de ce qu'il calcule : le compilateur à la volée (WebAssembly) fait lui-même ce
qu'il laissait à une fonction d'aide, appelée à chaque instruction (lancée par l'action GitHub sur la copie de fm1-emu).

  1. les multiplications-accumulations flottantes (ops 7 et 8 : d = d + a * b, d = d - a * b), jusque-là confiées à
     l'exécuteur, deviennent des instructions f32 du bloc compilé (Melodee en appelait 5 millions par seconde) ;
     fop_selftest (web/jit.test.mjs) les compare à l'exécuteur sur les valeurs limites, NaN compris.
    python3 tools/fm1emu_perf.py <dossier fm1-emu>
"""
import sys

emu = sys.argv[1]


def patch(path, pairs):
    s = open(path, encoding="utf-8").read()
    for old, new in pairs:
        assert s.count(old) == 1, f"{path} : motif introuvable ou multiple : {old[:60]!r}"
        s = s.replace(old, new)
    open(path, "w", encoding="utf-8").write(s)


JIT = f"{emu}/crates/fm1-core/src/jit_wasm.rs"

MAC = '''                    7 | 8 => {
                        // d = d + a * b, d = d - a * b (perf: the multiply-accumulates of fm1_core::fpu_d, two roundings,
                        // the product taking b first as op 2 does)
                        g.ld_reg(d);
                        g.op(F32_REINTERPRET_I32);
                        g.ld_reg(b);
                        g.op(F32_REINTERPRET_I32);
                        g.ld_reg(a);
                        g.op(F32_REINTERPRET_I32);
                        g.op(F32_MUL);
                        g.op(if op == 7 { F32_ADD } else { F32_SUB });
                    }
'''

patch(JIT, [
    ("matches!(op, 0..=3 | 5 | 6 | 0x0f", "matches!(op, 0..=3 | 5 | 6 | 7 | 8 | 0x0f"),
    ("                    5 | 6 => {\n                        // a' = a != a ? b : a;", MAC + "                    5 | 6 => {\n                        // a' = a != a ? b : a;"),
    ("let (b2, b3) = if op <= 6 {", "let (b2, b3) = if op <= 8 {"),
    ("let binary = op <= 6;", "let binary = op <= 8;"),
])
