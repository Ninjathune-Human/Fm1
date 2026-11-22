# Module sample : édition du sample et des tranches, découpage intelligent — plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** éditer le sample entier (rognage) et chaque tranche aux deux potards (SELECT : début, MACRO : fin), valider par SEL, et découper en tranches dans les creux du son.

**Architecture:** `sample.html` seul. Les pages deviennent `edit` (hors menu), `sample`, `slice`, `sound`, `capture`, `send` ; « dans un menu » se lit désormais `S.page !== "edit"`, et `S.col` ne sert plus qu'à Capture et Envoi. Le découpage intelligent est une fonction pure de `sample-lib` (testée sous Node).

**Tech Stack:** HTML/JS vanilla mono-fichier, Canvas, Web Audio ; pytest + Playwright Chromium ; `node --test`.

**Spec:** `docs/superpowers/specs/2026-11-22-module-sample-edition.md` (complète `docs/superpowers/specs/2026-11-22-module-sample-ecran-non-tactile.md`).

## Global Constraints

- Code dans `sample.html` seulement ; tests dans `tests/test_sample.py` et `tests/sample.test.mjs`.
- Aucun nouveau bouton, aucune nouvelle touche clavier ; ASSIGN devient SEL (étiquette et nom de crochet).
- Le modèle d'une tranche reste `{ start, len, pitch, gain }` (ms, demi-tons, 0-100) ; `start` et `len` peuvent devenir fractionnaires (calage au passage à zéro), l'affichage arrondit.
- Ce que le changement rend orphelin part (`editColumn` pour Édition, `S.saveSoon` s'il n'a plus d'usage, la colonne tempo, `LAST_COL.edit`).
- Suites vertes : `tests/test_sample.py tests/test_backup.py tests/test_langue.py tests/test_aide.py::test_manuel_rubriques` ; `node --test tests/*.test.mjs` (2 échecs `fiches` déjà présents).
- Rien n'est poussé sur GitHub.

## Review Focus

1. Un réglage de tranche non validé, puis un pad d'une autre tranche, ou EDIT : la tranche revient exactement comme avant, au moteur aussi.
2. Un potard tourné d'un cran ne reste jamais bloqué par le calage au passage à zéro (le calage va dans le sens du geste).
3. Rognage validé : le moteur joue le sample rogné, les tranches et leurs réglages repartent de zéro, les sons propres des pads restent, et tout survit au rechargement.
4. Menus SAMPLE, TRANCHE, SON sans aucun sample : rien ne casse, l'écran dit « NO SAMPLE ».
5. Un son sans creux (sinus continu) ou du silence : les coupes restent près de leur place régulière, strictement croissantes.

---

### Task 1: Le découpage intelligent

**Files:**
- Modify: `sample.html` (bloc `sample-lib` : `smartBounds`, `snapZero` ; bloc `sample-store` : `makeSample` découpe avec `smartBounds`)
- Test: `tests/sample.test.mjs`, `tests/test_sample.py`

**Interfaces:**
- Produces: `snapZero(x: Float32Array, i: number, dir: -1|0|1, r: number) -> number` ; `smartBounds(x: Float32Array, rate: number, n = 16) -> Int32Array(n + 1)`.

Règles :
- `snapZero` : un passage à zéro en j veut dire `x[j-1]` et `x[j]` de signes opposés, ou `x[j] === 0`. `dir > 0` : le premier j ≥ i, jusqu'à i + r ; `dir < 0` : le premier j ≤ i, jusqu'à i − r ; `dir === 0` : le plus proche des deux côtés (égalité : vers l'avant). Aucun dans la fenêtre : i. Bornes [1, x.length − 1].
- `smartBounds` : `b[0] = 0`, `b[n] = x.length` ; pour chaque i de 1 à n − 1, la place régulière `c = round(N·i/n)` ; l'énergie par blocs de 5 ms ; dans [c − N/(4n), c + N/(4n)], le bloc le plus calme (égalité : le plus proche de c) ; sa position est c si ce bloc contient c, sinon son milieu ; puis `snapZero(x, ·, 0, 5 ms)`. Les bornes restent strictement croissantes.

- [ ] **Step 1: Écrire les tests**

```js
// tests/sample.test.mjs : ajouter smartBounds et snapZero à la liste extraite du bloc
test("snapZero : dans le sens du geste, sinon le plus proche", () => {
  const rate = 8000, x = Float32Array.from({ length: 800 }, (_, i) => Math.sin(2 * Math.PI * 100 * i / rate + 0.1));
  const zc = (j) => x[j - 1] * x[j] <= 0;
  const f = lib.snapZero(x, 10, 1, 100); assert.ok(f >= 10 && zc(f));
  for (let j = 10; j < f; j++) assert.ok(!zc(j));
  const b = lib.snapZero(x, 60, -1, 100); assert.ok(b <= 60 && zc(b));
  assert.equal(lib.snapZero(new Float32Array(100).fill(0.5), 50, 1, 20), 50);
});
test("smartBounds : les coupes tombent dans les creux proches", () => {
  const rate = 8000, unit = 1000, N = 16 * unit, x = new Float32Array(N);
  for (let i = 0; i < N; i++) { const p = i % unit; x[i] = p >= 100 && p < 200 ? 0 : 0.8 * Math.sin(2 * Math.PI * 220 * i / rate); }
  const b = lib.smartBounds(x, rate);
  assert.equal(b.length, 17); assert.equal(b[0], 0); assert.equal(b[16], N);
  for (let i = 1; i < 16; i++) { const p = b[i] - i * unit; assert.ok(p >= 100 && p <= 200, `coupe ${i} à ${p}`); }
});
test("smartBounds : silence et sinus continu, près de la place régulière", () => {
  const rate = 8000, N = 16000;
  assert.deepEqual([...lib.smartBounds(new Float32Array(N), rate)], [...lib.sliceBounds(N)]);
  const s = Float32Array.from({ length: N }, (_, i) => Math.sin(2 * Math.PI * 220 * i / rate));
  const b = lib.smartBounds(s, rate);
  for (let i = 1; i < 16; i++) { assert.ok(b[i] > b[i - 1]); assert.ok(Math.abs(b[i] - i * 1000) <= 250 + 40); }
});
```

```python
# tests/test_sample.py
def wav_gaps(path, rate=44100):
    """Seize notes d'une seconde/4, chacune suivie d'un silence placé après la limite régulière."""
    import math, struct, wave
    unit = rate // 4
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes(b"".join(struct.pack("<h", 0 if unit // 10 <= i % unit < unit // 5 else int(12000 * math.sin(2 * math.pi * 220 * i / rate))) for i in range(16 * unit)))
    return str(path), unit

def test_import_coupe_dans_les_creux(page, tmp_path):
    open_sample(page); power_sample(page)
    path, unit = wav_gaps(tmp_path / "g.wav")
    import_wav(page, path)
    sl, rate = page.evaluate("[Array.from(window.__sample.samples[window.__sample.cur].slices), window.__sample.samples[window.__sample.cur].rate]")
    for i in range(1, 16):                                      # (en secondes : l'import peut rééchantillonner)
        assert 0.025 - 0.001 <= sl[i] / rate - i * 0.25 <= 0.05 + 0.001, i
```

- [ ] **Step 2: Lancer, voir échouer** — `node --test tests/sample.test.mjs` → FAIL (`smartBounds` indéfini) ; `pytest -k creux` → FAIL (coupes régulières).
- [ ] **Step 3: Écrire `snapZero` et `smartBounds` ; `makeSample` utilise `smartBounds(ch[0], rate)`.**
- [ ] **Step 4: Lancer** les deux, puis `python -m pytest -q tests/test_sample.py` → PASS.
- [ ] **Step 5: Commit** `feat(sample): découpage dans les creux du son`.

### Task 2: SEL et les menus SAMPLE, TRANCHE, SON

**Files:**
- Modify: `sample.html` (panneau : étiquette SEL ; blocs `sample-screen` et `sample-send` : pages, crochets EDIT, SEL, SELECT, MACRO ; en-têtes et dessins)
- Test: `tests/test_sample.py`

**Interfaces:**
- Produces: `S.page ∈ { "edit", "sample", "slice", "sound", "capture", "send" }` ; `S.inMenu() -> boolean` (`S.page !== "edit"`) ; `S.marks = { sample, slice, sound }`, chacun `(which: 0|1, n: number, v: number) -> boolean` (0 : SELECT, 1 : MACRO), vides dans cette tâche (rendent `false`) ; `S.validate = { sample, slice, sound }` appelées par SEL dans ces pages, vides ici.

Règles :
- EDIT : `edit → sample → slice → sound → capture → edit` ; `send → edit`. `S.col` vaut 0 en entrant dans Capture ou Envoi, `null` ailleurs. La colonne tempo disparaît (`S.col === 4`, sa surbrillance, sa branche dans `editColumn`).
- SELECT : pages `sample`, `slice`, `sound` → `S.marks[page](0, n, v)` ; Capture, Envoi → `editColumn` (inchangé pour elles) ; `edit` → sample suivant (inchangé).
- MACRO : SEL ouvert (`S.assigning`) → la cible ; `sample`, `slice`, `sound` → `S.marks[page](1, n, v)` ; Capture (max 3), Envoi (max 1) → la colonne ; `edit` → `S.macroTurn`.
- SEL : hors menu, l'ancien ASSIGN (tenu, ou verrouillé d'un appui court) ; dans `sample`, `slice`, `sound`, un appui appelle `S.validate[page]()` ; dans Capture, Envoi : rien. Une autre touche ferme toujours la liste ouverte.
- En-têtes : `edit`, `slice`, `sound` gardent START | LENGTH | PITCH | GAIN ; surbrillance : `slice` → START et LENGTH, `sound` → PITCH et GAIN, `edit` → aucune. `sample` : START | END | LENGTH | LOOP (en secondes, et « N BARS » ou « ONE SHOT »), surbrillance START et END. Sans sample : « NO SAMPLE ».
- Zoom sur la tranche dans `slice` et `sound` ; tout le sample ailleurs.
- La liste de SEL dit « Turn MACRO, SEL to close ».

- [ ] **Step 1: Écrire les tests** (réécrire `test_pages`, `test_macro_choisit_la_colonne`, `test_zoom_suit_la_tranche`, les deux tests d'ASSIGN ; retirer `test_select_regle_la_colonne`, que Task 3 remplace ; `test_panneau` vérifie `[data-label='SEL']` et l'absence d'ASSIGN)

```python
def test_pages(page, tmp_path):
    with_sample(page, tmp_path)
    pg = lambda: page.evaluate("[window.__sample.page, window.__sample.col]")
    assert pg() == ["edit", None]
    for want in (["sample", None], ["slice", None], ["sound", None], ["capture", 0], ["edit", None]):
        tap(page, "[data-label='EDIT']"); assert pg() == want
    tap(page, "[data-label='SEND']"); assert pg() == ["send", 0]
    tap(page, "[data-label='EDIT']"); assert pg() == ["edit", None]

def test_macro_choisit_la_colonne(page, tmp_path):
    with_sample(page, tmp_path)
    for _ in range(4): tap(page, "[data-label='EDIT']")                    # Capture
    page.evaluate("window.__sample.turn('MACRO', 9, 0)")
    assert page.evaluate("window.__sample.col") == 3
    tap(page, "[data-label='SEND']"); page.evaluate("window.__sample.turn('MACRO', 9, 0)")
    assert page.evaluate("window.__sample.col") == 1

def test_zoom_suit_la_tranche(page, tmp_path):
    with_sample(page, tmp_path)
    page.evaluate("window.__sample.slice = 4"); tap(page, "[data-label='EDIT']"); tap(page, "[data-label='EDIT']")   # TRANCHE
    page.wait_for_timeout(50)
    z = page.evaluate("window.__sample.zoom")
    assert 0 < z["to"] - z["from"] < 0.5 and z["from"] < 4 / 16 < z["to"]
    for _ in range(3): tap(page, "[data-label='EDIT']")                    # hors menu
    page.wait_for_timeout(50)
    assert page.evaluate("window.__sample.zoom") == {"from": 0, "to": 1}

def test_sel_choisit_la_cible(page, tmp_path):        # (ex test_assign_choisit_la_cible, hors menu)
    with_sample(page, tmp_path)
    hold(page, "[data-label='SEL']", True)
    page.evaluate("window.__sample.turn('MACRO', 1, 0)")
    hold(page, "[data-label='SEL']", False)
    assert page.evaluate("[window.__sample.macro.target, window.__sample.assigning]") == ["RES", False]
    page.reload(); page.wait_for_selector("#panel [data-label='REC']")
    assert page.evaluate("window.__sample.macro.target") == "RES"

def test_sel_appui_court_verrouille(page, tmp_path):   # (ex test_assign_appui_court_verrouille)
    with_sample(page, tmp_path)
    tap(page, "[data-label='SEL']"); assert page.evaluate("window.__sample.assigning") is True
    page.evaluate("window.__sample.turn('MACRO', 2, 0)"); assert page.evaluate("window.__sample.macro.target") == "ECHO"
    tap(page, "[data-label='SEL']"); assert page.evaluate("window.__sample.assigning") is False
    tap(page, "[data-label='SEL']"); tap(page, "[data-label='EDIT']")
    assert page.evaluate("[window.__sample.assigning, window.__sample.page]") == [False, "sample"]

def test_sel_dans_un_menu_ne_choisit_pas_la_cible(page, tmp_path):
    with_sample(page, tmp_path)
    tap(page, "[data-label='EDIT']")                                       # SAMPLE
    tap(page, "[data-label='SEL']")
    assert page.evaluate("window.__sample.assigning") is False

def test_menus_sans_sample(page):
    open_sample(page); power_sample(page)
    for _ in range(3):
        tap(page, "[data-label='EDIT']")
        page.evaluate("window.__sample.turn('SELECT', 2, 0); window.__sample.turn('MACRO', -2, 0)")
        tap(page, "[data-label='SEL']")
    assert page.evaluate("window.__sample.page") == "sound"
```
Partout ailleurs dans les tests, `[data-label='ASSIGN']` devient `[data-label='SEL']`.

- [ ] **Step 2: Lancer, voir échouer** `-k "pages or macro_choisit or zoom_suit or sel_ or menus_sans or panneau"` → FAIL.
- [ ] **Step 3: Implémenter.**
- [ ] **Step 4: Lancer** `python -m pytest -q tests/test_sample.py` → PASS.
- [ ] **Step 5: Commit** `feat(sample): SEL et les menus SAMPLE, TRANCHE, SON`.

### Task 3: TRANCHE et SON, validés par SEL

**Files:**
- Modify: `sample.html` (bloc `sample-screen` : `S.marks.slice`, `S.marks.sound`, `S.validate.slice`, `S.validate.sound`, `S.pending` ; bloc `sample-gestures` : un pad qui change de tranche défait l'édition en cours)
- Test: `tests/test_sample.py`

**Interfaces:**
- Consumes: `S.marks`, `S.validate` (Task 2) ; `snapZero` (Task 1).
- Produces: `S.pending = { k, before } | null` ; `S.revert()`.

Règles :
- En entrant dans `slice` ou `sound` (et quand un pad choisit une autre tranche dans ces pages), `S.pending = { k: S.slice, before: copie de cols[k] }`. En quittant ces pages par EDIT ou SEND, ou en changeant de tranche, sans SEL : `S.revert()` remet `cols[k] = before` et l'envoie au moteur. Passer de `slice` à `sound` défait aussi un réglage de `slice` non validé.
- `S.marks.slice` : en trames, `sa = slices[k] + start·rate/1000`, `se = sa + len·rate/1000`. SELECT (0) déplace `sa` de `stepOf(n, v)` ms, calé par `snapZero(x, ·, sign(n), 5 ms)`, borné à [max(0, slices[k] − full), se − 10 ms] ; `se` ne bouge pas. MACRO (1) déplace `se` pareil, borné à [sa + 10 ms, min(N, slices[k] + 4·full)]. `full` = la tranche en trames. Puis `start = (sa − slices[k])·1000/rate`, `len = (se − sa)·1000/rate`, envoyés au moteur (message `slice`), sans sauvegarde.
- `S.marks.sound` : SELECT → `pitch ± n` borné ±24 ; MACRO → `gain ± n` borné [0, 100] ; envoyés au moteur.
- `S.validate.slice` / `.sound` : `S.save(s)`, puis `before` = la valeur courante.

- [ ] **Step 1: Écrire les tests**

```python
def to_menu(page, name):
    order = ["sample", "slice", "sound", "capture"]
    for _ in range(order.index(name) + 1): tap(page, "[data-label='EDIT']")

COLS = "window.__sample.samples[window.__sample.cur].cols"

def test_tranche_debut_garde_la_fin(page, tmp_path):
    with_sample(page, tmp_path); tap(page, "[data-pad='4']"); to_menu(page, "slice")
    c0 = page.evaluate(f"{{ ...{COLS}[4] }}")
    page.evaluate("window.__sample.turn('SELECT', 20, 0)")
    c1 = page.evaluate(f"{{ ...{COLS}[4] }}")
    assert c1["start"] > c0["start"] and abs((c1["start"] + c1["len"]) - (c0["start"] + c0["len"])) < 1e-6

def test_tranche_fin(page, tmp_path):
    with_sample(page, tmp_path); tap(page, "[data-pad='4']"); to_menu(page, "slice")
    c0 = page.evaluate(f"{{ ...{COLS}[4] }}")
    page.evaluate("window.__sample.turn('MACRO', -20, 0)")
    c1 = page.evaluate(f"{{ ...{COLS}[4] }}")
    assert c1["start"] == c0["start"] and c1["len"] < c0["len"]

def test_tranche_au_passage_a_zero(page, tmp_path):
    with_sample(page, tmp_path); tap(page, "[data-pad='4']"); to_menu(page, "slice")
    page.evaluate("window.__sample.turn('SELECT', 7, 0)")
    assert page.evaluate(f"""(() => {{ const s = window.__sample.samples[window.__sample.cur], c = s.cols[4];
      const j = Math.round(s.slices[4] + c.start * s.rate / 1000), x = s.ch[0]; return x[j - 1] * x[j] <= 0; }})()""")

def test_un_cran_bouge_toujours(page, tmp_path):
    with_sample(page, tmp_path); tap(page, "[data-pad='4']"); to_menu(page, "slice")
    starts = []
    for _ in range(5):
        page.evaluate("window.__sample.turn('SELECT', 1, 0)"); starts.append(page.evaluate(f"{COLS}[4].start"))
    assert all(b > a for a, b in zip(starts, starts[1:]))

def test_sel_valide_la_tranche(page, tmp_path):
    with_sample(page, tmp_path); tap(page, "[data-pad='4']"); to_menu(page, "slice")
    page.evaluate("window.__sample.turn('SELECT', 20, 0)"); tap(page, "[data-label='SEL']")
    kept = page.evaluate(f"{COLS}[4].start")
    page.reload(); page.wait_for_selector("#panel [data-label='REC']"); power_sample(page)
    assert abs(page.evaluate(f"{COLS}[4].start") - kept) < 1e-6

def test_sans_sel_la_tranche_revient(page, tmp_path):
    with_sample(page, tmp_path); tap(page, "[data-pad='4']"); to_menu(page, "slice")
    c0 = page.evaluate(f"{{ ...{COLS}[4] }}"); spy_sent(page)
    page.evaluate("window.__sample.turn('SELECT', 20, 0)")
    tap(page, "[data-label='EDIT']")                                       # vers SON, sans SEL
    assert page.evaluate(f"{{ ...{COLS}[4] }}") == c0
    assert page.evaluate("window.__sent.filter((m) => m.t === 'slice' && m.i === 4).pop().start") == c0["start"]

def test_un_autre_pad_defait(page, tmp_path):
    with_sample(page, tmp_path); tap(page, "[data-pad='4']"); to_menu(page, "slice")
    c0 = page.evaluate(f"{{ ...{COLS}[4] }}")
    page.evaluate("window.__sample.turn('MACRO', -20, 0)"); tap(page, "[data-pad='5']")
    assert page.evaluate(f"{{ ...{COLS}[4] }}") == c0

def test_son(page, tmp_path):
    with_sample(page, tmp_path); tap(page, "[data-pad='2']"); to_menu(page, "sound")
    page.evaluate("window.__sample.turn('SELECT', 3, 0); window.__sample.turn('MACRO', -10, 0)")
    assert page.evaluate(f"[{COLS}[2].pitch, {COLS}[2].gain]") == [3, 90]
    tap(page, "[data-label='SEL']"); tap(page, "[data-label='EDIT']")      # validé, puis Capture
    assert page.evaluate(f"[{COLS}[2].pitch, {COLS}[2].gain]") == [3, 90]
```

- [ ] **Step 2: Lancer, voir échouer** `-k "tranche or un_cran or sel_valide or sans_sel or autre_pad or test_son"` → FAIL.
- [ ] **Step 3: Implémenter.**
- [ ] **Step 4: Lancer** `python -m pytest -q tests/test_sample.py` → PASS.
- [ ] **Step 5: Commit** `feat(sample): TRANCHE et SON, validés par SEL`.

### Task 4: SAMPLE, le rognage

**Files:**
- Modify: `sample.html` (bloc `sample-screen` : `S.trim`, `S.marks.sample`, `S.validate.sample`, `drawSample`)
- Test: `tests/test_sample.py`

**Interfaces:**
- Consumes: `smartBounds`, `snapZero` (Task 1) ; `S.marks`, `S.validate` (Task 2).
- Produces: `S.trim = { a, b } | null` (trames).

Règles :
- En entrant dans `sample` : `S.trim = { a: 0, b: N }` ; en le quittant : `S.trim = null` (rien ne change).
- SELECT déplace `a`, MACRO `b`, de `stepOf(n, v) · N / 200` trames, calés par `snapZero(x, ·, sign(n), 5 ms)` ; `a ∈ [0, b − 0,1 s]`, `b ∈ [a + 0,1 s, N]`.
- Dessin : tout le sample, la partie hors de [a, b] assombrie, un repère à `a` et à `b`.
- SEL : si [a, b] ≠ [0, N] : `s.ch = s.ch.map((c) => c.slice(a, b))`, `s.slices = smartBounds(s.ch[0], s.rate)`, `s.bars`/`s.fit` par `fitBars` au tempo du moment, `s.cols` remis à zéro comme dans `makeSample`, `S.save(s)`, `S.select(S.cur)` (recharge le moteur) ; puis `S.trim = { a: 0, b: nouveau N }`. `s.pads` (sons propres des pads) ne change pas.

- [ ] **Step 1: Écrire les tests**

```python
CUR = "window.__sample.samples[window.__sample.cur]"

def test_rogner(page, tmp_path):
    with_sample(page, tmp_path, 4); to_menu(page, "sample")
    n0 = page.evaluate(f"{CUR}.ch[0].length")
    page.evaluate("window.__sample.turn('SELECT', 20, 0); window.__sample.turn('MACRO', -40, 0)")
    a, b = page.evaluate("[window.__sample.trim.a, window.__sample.trim.b]")
    assert 0 < a < b < n0
    tap(page, "[data-label='SEL']")
    assert page.evaluate(f"{CUR}.ch[0].length") == b - a
    assert page.evaluate(f"[{CUR}.slices.length, {CUR}.slices[16]]") == [17, b - a]
    assert page.evaluate(f"{CUR}.cols.every((c) => c.start === 0 && c.pitch === 0 && c.gain === 100)")
    assert page.evaluate("window.__engine().sample.ch[0].length") == b - a
    page.reload(); page.wait_for_selector("#panel [data-label='REC']"); power_sample(page)
    assert page.evaluate(f"{CUR}.ch[0].length") == b - a

def test_rogner_sans_sel(page, tmp_path):
    with_sample(page, tmp_path, 4); to_menu(page, "sample")
    n0 = page.evaluate(f"{CUR}.ch[0].length")
    page.evaluate("window.__sample.turn('SELECT', 20, 0)"); tap(page, "[data-label='EDIT']")
    assert page.evaluate(f"{CUR}.ch[0].length") == n0 and page.evaluate("window.__sample.trim") is None

def test_rogner_bornes(page, tmp_path):
    with_sample(page, tmp_path, 4); to_menu(page, "sample")
    page.evaluate("window.__sample.turn('SELECT', 900, 0)")
    a, b, rate = page.evaluate(f"[window.__sample.trim.a, window.__sample.trim.b, {CUR}.rate]")
    assert b - a >= 0.1 * rate - 1
```

- [ ] **Step 2: Lancer, voir échouer** `-k rogner` → FAIL.
- [ ] **Step 3: Implémenter.**
- [ ] **Step 4: Lancer la suite entière** (Global Constraints) → PASS.
- [ ] **Step 5: Commit** `feat(sample): SAMPLE, rogner le sample et le redécouper`.
