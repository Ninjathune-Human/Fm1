"""Ajoute à fm1-emu la LED verte de PLAY, absente de son tableau de 41 LED.

Sur le FM-1, PLAY a deux LED : la rouge à la place du bouton dans la matrice, et une verte à une position
sans touche (colonne 8, ligne 1). fm1-emu ne compte que les positions qui ont une touche, la verte est perdue.
Ce script, lancé par l'action GitHub sur la copie de fm1-emu, la compte à part et l'expose (fm1_play_green),
puis la joint aux images du worklet (green). Rien d'autre ne change.
    python3 tools/fm1emu_vert.py <dossier fm1-emu> <worklet.js publié>
"""
import sys

emu, worklet = sys.argv[1], sys.argv[2]


def patch(path, pairs):
    s = open(path, encoding="utf-8").read()
    for old, new in pairs:
        assert s.count(old) == 1, f"{path} : motif introuvable ou multiple : {old[:60]!r}"
        s = s.replace(old, new)
    open(path, "w", encoding="utf-8").write(s)


patch(f"{emu}/crates/fm1-soc/src/periph.rs", [
    ("    led_acc: [u64; 41],\n", "    led_acc: [u64; 42],\n    /// PLAY's green LED (column 8, row 1, a position without a key): its on-fraction at the last led_take\n    pub play_green: f32,\n"),
    ("            led_acc: [0; 41],\n", "            led_acc: [0; 42],\n            play_green: 0.0,\n"),
    ("            for row in 1..5usize {\n                if lines & (1 << row) != 0 {\n                    let id = KEYMAP[row][col];",
     "            if col == 8 && lines & 2 != 0 {\n                self.led_acc[41] += dt;\n            }\n            for row in 1..5usize {\n                if lines & (1 << row) != 0 {\n                    let id = KEYMAP[row][col];"),
    ("        let mut out = [0f32; 41];\n",
     "        self.play_green = self.led_acc[41] as f32 / span;\n        self.led_acc[41] = 0;\n        let mut out = [0f32; 41];\n"),
])
patch(f"{emu}/crates/fm1-web/src/lib.rs", [
    ("#[no_mangle]\npub extern \"C\" fn fm1_leds() -> *const f32 {",
     "/// PLAY's green LED: its on-fraction over the same span as the last fm1_leds.\n#[no_mangle]\npub extern \"C\" fn fm1_play_green() -> f32 {\n    machine().map_or(0.0, |m| m.soc.periph.play_green)\n}\n\n#[no_mangle]\npub extern \"C\" fn fm1_leds() -> *const f32 {"),
])
patch(worklet, [
    ("{ type: \"frame\", seq: this.seq, lcd, leds, ms,", "{ type: \"frame\", seq: this.seq, lcd, leds, green: x.fm1_play_green ? x.fm1_play_green() : 0, ms,"),
])
print("fm1-emu : LED verte de PLAY ajoutée")
