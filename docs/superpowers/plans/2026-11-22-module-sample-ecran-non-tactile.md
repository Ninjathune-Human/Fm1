# Module sample : écran non tactile, MACRO et ASSIGN — plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** l'écran du module n'est plus tactile ; un potard MACRO et un bloc de boutons 3 × 2 (FILE, EDIT, SEND / ASSIGN, PLAY, REC) donnent accès à tout ce qui s'y faisait au doigt.

**Architecture:** tout se passe dans `sample.html` (blocs `sample-panel`, `sample-page`, `sample-store`, `sample-screen`, `sample-gestures`). « Dans un menu » se lit `S.col != null` : aucun état nouveau pour les menus. MACRO a deux rôles : choisir la colonne dans un menu, régler sa cible assignée hors menu.

**Tech Stack:** HTML/JS vanilla mono-fichier, SVG, Canvas, Web Audio ; tests pytest + Playwright Chromium.

**Spec:** `docs/superpowers/specs/2026-11-22-module-sample-ecran-non-tactile.md` (et, pour le reste, `docs/superpowers/specs/2026-11-22-module-sample-design.md`).

## Global Constraints

- Un seul fichier de code touché : `sample.html` ; tests dans `tests/test_sample.py`.
- Aucune touche clavier nouvelle, aucun bouton au-delà des six du croquis, aucun changement d'`index.html`.
- Le code des gestes à l'écran est retiré, pas désactivé ; ce que ce retrait rend orphelin (fonctions, aides de test) part avec.
- Commentaires en français, dans le style du fichier ; pas d'emoji.
- Suites à garder vertes : `tests/test_sample.py tests/test_backup.py tests/test_langue.py tests/test_aide.py::test_manuel_rubriques` ; `node --test tests/*.test.mjs` (2 échecs de `fiches.test.mjs` déjà présents sur main, hors sujet).
- Rien n'est poussé sur GitHub.

## Review Focus

1. MACRO tourné pendant qu'un doigt est sur la zone XY : le doigt garde la main, la valeur de MACRO change, et le lever ramène à cette nouvelle valeur.
2. ASSIGN tenu dans un menu : MACRO change sa cible, pas la colonne.
3. Module éteint puis rallumé : la valeur de MACRO repart du neutre, sa cible est gardée.
4. FILE pendant un enregistrement ou module éteint : rien ne s'ouvre.
5. Fin d'une capture ou d'un import : retour hors menu (page Édition, aucune colonne).

---

### Task 1: Le panneau du croquis

**Files:**
- Modify: `sample.html` (bloc `sample-panel`, la disposition ; CSS `.device canvas` et `.start button`)
- Test: `tests/test_sample.py`

**Interfaces:**
- Produces: `panel.knobs.MACRO` ; `panel.caps.FILE`, `panel.caps.ASSIGN` ; `panel.center.platter = [1370, 272]`.

Valeurs (unités du panneau, viewBox 1640 × 990) :
- Plaque des boutons : `plate(95, 262, 382, 228, 34)`. Rangée 1 (y 319) : FILE x 156, EDIT x 286, SEND x 416. Rangée 2 (y 425) : ASSIGN x 156, PLAY/STOP x 286, REC x 416. Boutons de 100 × 80, comme aujourd'hui.
- `knob(481, 147, "MACRO", false)`.
- Écran : cadre à x0 = 548, largeur 586, hauteur 373 (le rapport de l'image LCD 526 × 300 est gardé). Les cinq rectangles gardent leurs décalages actuels par rapport au cadre (ombre x0+4 / y 82 ; cadre x0 / y 70 ; arête x0+1 / y 71, W-2, H-2 ; fond x0+12 / y 82, W-24, H-24 ; verre x0+43 / y 113, W-86, H-86).
- CSS : `.device canvas { left: 36.159%; top: 11.616%; width: 30.244%; height: 28.586% }` ; `.start button { left: 51.280%; top: 25.909% }`.
- Platine : `PX = 1370` (son bord droit s'aligne sur celui de la zone XY).

- [ ] **Step 1: Écrire les tests**

```python
def test_panneau(page):                      # (remplace l'actuel : 6 touches, 3 molettes)
    open_sample(page)
    assert page.locator("#panel .cap").count() == 6
    assert page.locator("#panel [data-knob]").count() == 3
    ...                                       # le reste de l'actuel, inchangé

def test_disposition_du_croquis(page):
    open_sample(page)
    box = lambda sel: page.locator(sel).bounding_box()
    c = {n: box(f"[data-label='{n}']") for n in ("FILE", "EDIT", "SEND", "ASSIGN", "PLAY", "REC")}
    assert c["FILE"]["x"] < c["EDIT"]["x"] < c["SEND"]["x"]
    assert c["ASSIGN"]["x"] < c["PLAY"]["x"] < c["REC"]["x"]
    assert abs(c["FILE"]["y"] - c["SEND"]["y"]) < 2 and c["ASSIGN"]["y"] > c["FILE"]["y"] + 40
    m, s, scr, pl = box("[data-knob='MACRO']"), box("[data-knob='SELECT']"), box("#screen"), box("#platter")
    assert m["x"] > s["x"] + s["width"] and m["x"] + m["width"] < scr["x"]
    assert scr["x"] + scr["width"] < pl["x"]
```
Et `PX, PY = 1370, 272` dans les constantes des tests de platine.

- [ ] **Step 2: Lancer, voir échouer** — `python -m pytest -q tests/test_sample.py -k "panneau or disposition"` → FAIL (4 touches, 2 molettes).
- [ ] **Step 3: Dessiner le panneau** aux valeurs ci-dessus.
- [ ] **Step 4: Lancer** `-k "panneau or disposition or platine or scratch or relache or lancer"` → PASS.
- [ ] **Step 5: Commit** `feat(sample): le panneau du croquis (MACRO, six touches)`.

### Task 2: L'écran ne se touche plus ; le zoom suit la tranche

**Files:**
- Modify: `sample.html` (bloc `sample-screen` : retrait de `lcdXY`, des écouteurs `pointer*` de `#screen`, de `lift`, `touches`, `S.pinch`, `S.chipX`, `S.targetChipX`, de `fx` s'il n'a plus d'usage ; `drawEdit` calcule le zoom)
- Test: `tests/test_sample.py` (retrait de `test_colonne_et_select`, `test_poignee`, `test_pincer`, `test_tranche_touchee`, `test_puces`, `test_glisser_une_valeur`, `test_poignee_de_fin`, `test_puce_de_cible`, `test_puce_file_au_lever_du_doigt`, puis des aides `lcd_touch` et `lcd_point` si plus rien ne s'en sert)

**Interfaces:**
- Produces: `S.zoom` reste `{ from, to }` (fractions), calculé à chaque dessin de la page Édition.

Zoom : colonne active 0 (START) ou 1 (LENGTH) sur Édition → la tranche `S.slice` (de `slices[k] + start` à cette position + `len`) occupe la moitié centrale de l'écran : marge de la moitié de sa largeur de chaque côté, bornée à [0, 1]. Sinon `{ from: 0, to: 1 }`.

- [ ] **Step 1: Écrire les tests**

```python
def test_ecran_ne_se_touche_pas(page, tmp_path):
    with_sample(page, tmp_path)
    before = page.evaluate("[window.__sample.col, window.__sample.slice, JSON.stringify(window.__sample.zoom)]")
    for x, y in ((55, 30), (200, 120), (380, 68)):
        b = page.evaluate("(() => { const r = document.getElementById('screen').getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; })()")
        cx, cy = b[0] + x / 440 * b[2], b[1] + y / 240 * b[3]
        for kind in ("pointerdown", "pointerup"):
            page.dispatch_event("#screen", kind, {"pointerId": 1, "clientX": cx, "clientY": cy, "isPrimary": True, "pointerType": "touch"})
    assert page.evaluate("[window.__sample.col, window.__sample.slice, JSON.stringify(window.__sample.zoom)]") == before

def test_pad_choisit_la_tranche(page, tmp_path):
    with_sample(page, tmp_path)
    tap(page, "[data-pad='8']")
    assert page.evaluate("window.__sample.slice") == 8

def test_zoom_suit_la_tranche(page, tmp_path):
    with_sample(page, tmp_path)
    page.evaluate("window.__sample.slice = 4; window.__sample.col = 0")
    page.wait_for_timeout(50)
    z = page.evaluate("window.__sample.zoom")
    assert 0 < z["to"] - z["from"] < 0.5 and z["from"] < 4 / 16 < z["to"]
    page.evaluate("window.__sample.col = 2"); page.wait_for_timeout(50)
    assert page.evaluate("window.__sample.zoom") == {"from": 0, "to": 1}
```
(Le dessin tourne à chaque image : l'attente de 50 ms suffit ; si `drawScreen` n'est pas appelé à chaque image, l'exposer en `S.drawScreen` et l'appeler dans le test.)

- [ ] **Step 2: Lancer, voir échouer** `-k "ne_se_touche or pad_choisit or zoom_suit"` → FAIL sur `test_ecran_ne_se_touche_pas` et `test_zoom_suit_la_tranche` (`test_pad_choisit_la_tranche` couvre un comportement existant et passe déjà).
- [ ] **Step 3: Retirer le code tactile de l'écran, calculer le zoom dans `drawEdit`.**
- [ ] **Step 4: Lancer** `python -m pytest -q tests/test_sample.py` → PASS (moins les tests retirés).
- [ ] **Step 5: Commit** `feat(sample): l'écran ne se touche plus ; le zoom suit la tranche réglée`.

### Task 3: Les menus : EDIT, SEND, MACRO pour la colonne, SELECT pour la valeur

**Files:**
- Modify: `sample.html` (blocs `sample-screen` : crochet EDIT, crochet MACRO ; `sample-send` : SEND ouvre l'Envoi en colonne 0 ; `sample-store` : `S.capture` met la colonne 0 en ouvrant Capture, la fin d'une capture et `S.importFile` remettent `S.col = null`)
- Test: `tests/test_sample.py` (`test_pages` réécrit)

**Interfaces:**
- Consumes: `panel.knobs.MACRO` (Task 1).
- Produces: `S.macroTurn(n) -> boolean` est appelé par le crochet MACRO hors menu (Task 4 le définit ; ici, un appel protégé `S.macroTurn && S.macroTurn(n)`).

Règles :
- EDIT : Édition hors menu → Édition, colonne 0 ; Édition en menu → Capture, colonne 0 ; Capture ou Envoi → Édition hors menu.
- SEND hors de l'Envoi → Envoi, colonne 0 (au lieu de `null`).
- MACRO dans un menu : `S.col = clamp(S.col + n, 0, max)`, `max` = 4 sur Édition (le tempo), 3 sur Capture, 1 sur Envoi. Rend `true` si la colonne a bougé.
- SELECT : inchangé (colonne active → valeur ; aucune colonne → sample suivant).

- [ ] **Step 1: Écrire les tests**

```python
def test_pages(page, tmp_path):
    with_sample(page, tmp_path)
    st = lambda: page.evaluate("[window.__sample.page, window.__sample.col]")
    assert st() == ["edit", None]
    for want in (["edit", 0], ["capture", 0], ["edit", None]):
        tap(page, "[data-label='EDIT']"); assert st() == want
    tap(page, "[data-label='SEND']"); assert st() == ["send", 0]
    tap(page, "[data-label='EDIT']"); assert st() == ["edit", None]
    tap(page, "[data-label='REC']"); page.wait_for_function("window.__sample.page === 'capture'")
    assert st() == ["capture", 0]
    tap(page, "[data-label='REC']")

def test_macro_choisit_la_colonne(page, tmp_path):
    with_sample(page, tmp_path)
    tap(page, "[data-label='EDIT']")
    page.evaluate("window.__sample.turn('MACRO', 9, 0)")
    assert page.evaluate("window.__sample.col") == 4                       # le tempo, en dernier
    tap(page, "[data-label='SEND']"); page.evaluate("window.__sample.turn('MACRO', 9, 0)")
    assert page.evaluate("window.__sample.col") == 1

def test_select_regle_la_colonne(page, tmp_path):
    with_sample(page, tmp_path)
    tap(page, "[data-label='EDIT']")                                       # START
    page.evaluate("window.__sample.turn('SELECT', 3, 0)")
    assert page.evaluate("window.__sample.samples[window.__sample.cur].cols[window.__sample.slice].start") == 3

def test_cible_par_select(page, tmp_path):
    with_sample(page, tmp_path)
    send_key(page)
    first = page.evaluate("window.__sample.target")
    page.evaluate("window.__sample.turn('SELECT', 1, 0)")
    assert page.evaluate("window.__sample.target") != first
```

- [ ] **Step 2: Lancer, voir échouer** `-k "pages or macro_choisit or select_regle or cible_par_select"` → FAIL (`test_pages`, `test_macro_choisit_la_colonne`, `test_select_regle_la_colonne`, `test_cible_par_select` : la colonne de l'Envoi est `null` aujourd'hui).
- [ ] **Step 3: Implémenter les règles.**
- [ ] **Step 4: Lancer** `python -m pytest -q tests/test_sample.py` → PASS.
- [ ] **Step 5: Commit** `feat(sample): les menus au panneau (EDIT, SEND, MACRO, SELECT)`.

### Task 4: MACRO assignable et ASSIGN

**Files:**
- Modify: `sample.html` (bloc `sample-gestures` : `S.macro`, `S.macroTurn`, retour de la zone XY vers la base ; bloc `sample-screen` : ASSIGN tenu, le dessin de la liste ; bloc `sample-page` : la cible gardée par `keep("macro")`)
- Test: `tests/test_sample.py`

**Interfaces:**
- Consumes: le crochet MACRO de Task 3.
- Produces: `S.macro = { target, base: { x, y, amount, feedback } }` ; `S.MACRO_TARGETS = ["FILTER", "RES", "ECHO", "FEEDBACK", "TEMPO"]` ; `S.assigning: boolean` ; `S.macroTurn(n) -> boolean`.

Règles :
- Cible par défaut FILTER ; gardée par `keep("macro", target)`, relue au chargement (une valeur inconnue redonne FILTER).
- Base neutre `{ x: 0.5, y: 0, amount: 0, feedback: 0 }`, remise au neutre à chaque mise sous tension.
- `S.macroTurn(n)` : FILTER `x ± n/36` borné [0, 1] ; RES `y ± n/36` [0, 1] ; ECHO `amount ± n/36` [0, 1] ; FEEDBACK `feedback ± n/40` [0, 0.9] ; TEMPO `S.bpm = S.bpm + n`. Hors TEMPO, le message `filter` ou `echo` part au moteur seulement si aucun doigt n'est sur la zone XY (`!S.touch.xy`).
- Zone XY : au lever du dernier doigt, la rampe de 250 ms mène le filtre et l'écho vers la base, plus vers le neutre ; en passant de deux doigts à un, l'écho revient à la base.
- ASSIGN appuyé : `S.assigning = true`, l'écran montre la liste des cinq cibles, la cible courante en surbrillance ; MACRO tourné fait défiler la cible (bornée, sans boucle), et l'enregistre ; ASSIGN relâché : `S.assigning = false`. Pendant ASSIGN, MACRO ne touche ni la colonne ni la base.

- [ ] **Step 1: Écrire les tests**

```python
def hold(fr, sel, down):
    fr.dispatch_event(sel, "pointerdown" if down else "pointerup", {"pointerId": 9, "isPrimary": True})

def test_macro_filtre_hors_menu(page, tmp_path):
    with_sample(page, tmp_path); spy_sent(page)
    page.evaluate("window.__sample.turn('MACRO', 9, 0)")
    assert abs(page.evaluate("window.__sample.macro.base.x") - 0.75) < 1e-9
    assert page.evaluate("window.__sent.some((m) => m.t === 'filter' && Math.abs(m.x - 0.75) < 1e-9)")

def test_assign_choisit_la_cible(page, tmp_path):
    with_sample(page, tmp_path)
    tap(page, "[data-label='EDIT']")                                       # dans un menu
    hold(page, "[data-label='ASSIGN']", True)
    assert page.evaluate("window.__sample.assigning") is True
    page.evaluate("window.__sample.turn('MACRO', 1, 0)")
    hold(page, "[data-label='ASSIGN']", False)
    assert page.evaluate("[window.__sample.macro.target, window.__sample.col]") == ["RES", 0]
    page.reload(); page.wait_for_selector("#panel [data-label='REC']")
    assert page.evaluate("window.__sample.macro.target") == "RES"

def test_xy_revient_a_macro(page, tmp_path):
    with_sample(page, tmp_path)
    page.evaluate("window.__sample.turn('MACRO', -9, 0)")                  # x 0.25
    ptr(page, "#xy", "pointerdown", *xy_at(0.9, 0.5)); ptr(page, "#xy", "pointerup", *xy_at(0.9, 0.5))
    page.wait_for_timeout(400)
    assert abs(page.evaluate("window.__sample.touch.filter.x") - 0.25) < 1e-6

def test_macro_pendant_le_doigt(page, tmp_path):
    with_sample(page, tmp_path)
    ptr(page, "#xy", "pointerdown", *xy_at(0.9, 0.5))
    spy_sent(page); page.evaluate("window.__sample.turn('MACRO', 9, 0)")
    assert page.evaluate("window.__sent.some((m) => m.t === 'filter')") is False
    ptr(page, "#xy", "pointerup", *xy_at(0.9, 0.5)); page.wait_for_timeout(400)
    assert abs(page.evaluate("window.__sample.touch.filter.x") - 0.75) < 1e-6

def test_macro_tempo(page, tmp_path):
    with_sample(page, tmp_path)
    page.evaluate("window.__sample.macro.target = 'TEMPO'")
    b = page.evaluate("window.__sample.bpm"); page.evaluate("window.__sample.turn('MACRO', 3, 0)")
    assert page.evaluate("window.__sample.bpm") == b + 3

def test_macro_neutre_au_rallumage(page, tmp_path):
    with_sample(page, tmp_path)
    page.evaluate("window.__sample.turn('MACRO', 9, 0)")
    page.click("#power"); page.click("#power"); page.wait_for_function("window.__sample.on")
    assert page.evaluate("window.__sample.macro.base.x") == 0.5
```

- [ ] **Step 2: Lancer, voir échouer** `-k "macro or assign or xy_revient"` → FAIL (`S.macro` indéfini).
- [ ] **Step 3: Implémenter.**
- [ ] **Step 4: Lancer** `python -m pytest -q tests/test_sample.py` → PASS.
- [ ] **Step 5: Commit** `feat(sample): MACRO assignable et ASSIGN`.

### Task 5: FILE

**Files:**
- Modify: `sample.html` (bloc `sample-store` : FILE ouvre `S.chooseFile()` au relâcher ; `SOURCES`/`SRC_LABEL` et `S.sources()` sans `file`)
- Test: `tests/test_sample.py` (`test_micro_refuse_montre_les_sources` réécrit)

**Interfaces:**
- Consumes: `panel.caps.FILE` (Task 1).

Règles : FILE relâché, module allumé, aucun enregistrement en cours → `S.chooseFile()` ; FILE appuyé ne fait rien (Safari n'ouvre la fenêtre qu'au lever du doigt).

- [ ] **Step 1: Écrire les tests**

```python
def test_file_au_relacher(page, tmp_path):
    open_sample(page); power_sample(page)
    page.evaluate("window.__opened = 0; window.__sample.chooseFile = () => window.__opened++; 0")
    hold(page, "[data-label='FILE']", True); assert page.evaluate("window.__opened") == 0
    hold(page, "[data-label='FILE']", False); assert page.evaluate("window.__opened") == 1

def test_file_ouvre_le_choix(page):
    open_sample(page); power_sample(page)
    with page.expect_file_chooser() as fc:
        page.click("[data-label='FILE']")
    assert fc.value is not None

def test_file_pendant_une_capture(page):
    open_sample(page); power_sample(page)
    page.evaluate("window.__sample.capt.thresh = null; window.__opened = 0; window.__sample.chooseFile = () => window.__opened++; 0")
    tap(page, "[data-label='REC']"); page.wait_for_function("!!window.__sample.recording")
    tap(page, "[data-label='FILE']")
    assert page.evaluate("window.__opened") == 0
    tap(page, "[data-label='REC']")

def test_sources_sans_file(page):
    open_sample(page); power_sample(page)
    assert "file" not in page.evaluate("Object.keys(window.__sample.sources())")

def test_micro_refuse_montre_les_sources(page):        # (réécrit : la page Capture reste)
    page.add_init_script("navigator.mediaDevices.getUserMedia = () => Promise.reject(new DOMException('refusé', 'NotAllowedError'))")
    open_sample(page); power_sample(page)
    tap(page, "[data-label='REC']")
    page.wait_for_function("window.__sample.page === 'capture'")
    assert page.evaluate("window.__sample.col") == 0
```
`hold` vient de Task 4.

- [ ] **Step 2: Lancer, voir échouer** `-k "file or sources_sans or micro_refuse"` → FAIL (pas de touche FILE active, `file` encore dans les sources).
- [ ] **Step 3: Implémenter.**
- [ ] **Step 4: Lancer la suite entière** (Global Constraints) → PASS.
- [ ] **Step 5: Commit** `feat(sample): FILE au panneau, la source fichier quitte Capture`.
