# Module sample et scratch, plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal :** une page `sample.html`, faite comme un FM-1, qui capte un son (micro, FM-1 voisin, fichier), le découpe, le déforme au doigt (platine, zone XY, pads) et l'envoie dans Pigeon ou zp12, jouée dans le Duo à la place de FM1-B, sur l'horloge du tempo lié.

**Architecture :** une page autonome. Ses fonctions pures vivent dans un bloc `<script id="sample-lib">`, testé sous Node ; son son dans un AudioWorklet inclus (`<script type="text/worklet" id="sample-worklet">`) ; son panneau est dessiné en SVG d'après `buildPanel()` d'`index.html` et la maquette (`docs/superpowers/specs/2026-11-22-module-sample/maquette.mjs`, fonction `panel({ kind: "module2" })`). Elle présente au Duo l'interface d'un moteur (`window.__engine()`). `index.html` ne change qu'en trois endroits : la section « Modules » de la liste de FM1-B, le cadre B du Duo, et `window.__takeSamples`.

**Tech Stack :** HTML/CSS/JS sans dépendance, Web Audio (AudioWorklet), IndexedDB, Node 22 (`node --test`), Python 3 + pytest + Playwright (Chromium).

**Spec :** `docs/superpowers/specs/2026-11-22-module-sample-design.md`

## Global Constraints

- Web seulement : rien ne change dans `ios/`.
- Pas de dépendance ; `sample.html` autonome, polices reprises des `@font-face` d'`index.html` (Barlow Semi Condensed 500 et 600, M PLUS Rounded 1c 700) ; en-tête `SPDX-License-Identifier: GPL-3.0-only` et crédit du dessin (DUB-1, sbegueria/fm1-dub).
- `index.html` : seulement la section « Modules » de FM1-B, `?choisir`, le cadre B du Duo (`fm1.duo.b`, `allow`) et `window.__takeSamples`.
- Panneau, unités du FM-1 (1640 × 990) : MASTER (135, 147), SELECT (308, 147) ; plaque (95, 262, 252 × 228) ; EDIT (156, 319), SEND (286, 319), PLAY/STOP (156, 425), REC (286, 425), 100 × 80 ; écran, cadre (422, 70, 616 × 390) ; platine centre (1336, 272), puits 206, couronne de 32 LED à 192, disque 174 ; pads, plaque (62, 560, 810 × 365), x = 123 + 93 i, y 659 et 825, fente 43 ; zone XY (902, 560, 676 × 365).
- Écran : 440 × 240 pixels, 1,25 unité par pixel ; thème Green (#0a1210, #eef7f3, #84a299, #a3d6c7) ; Barlow Semi Condensed ; textes de l'écran en anglais.
- Pages de l'écran : `capture`, `edit`, `send`. Colonnes, exactement : SOURCE, INPUT, THRESH, LENGTH ; START, LENGTH, PITCH, GAIN ; TO, SONG, PADS, SIZE.
- Sources, exactement : `mic`, `fm1`, `file`, `tab` (puces MIC, FM-1, FILE, TAB). Cibles : `pigeon`, `zp12`, `file`, `erase` (PIGEON, ZP12, FILE, ERASE).
- `getUserMedia({ audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false } })`.
- Un tour de platine = 1,8 s de son (`TURN_SECONDS = 1.8`) ; roll en doubles croches ; boucles de 1, 2, 4 ou 8 mesures ; capture de 16 s au plus.
- Mémoire : base IndexedDB `fm1-samples` (version 1, magasin `samples`) ; réglages sous `fm1.sample.` ; dans la sauvegarde, un champ `samples` à part, comme `copies`.
- Interface de la page en FR / EN (`fm1.lang`) : « Module sample » / « Sample module » ; pas d'emoji, pas de tiret cadratin.
- Mêmes molettes que le FM-1 : `Encoder` et `Haptics` recopiés d'`index.html`.

## Review Focus

1. Micro refusé ou absent : la puce MIC grisée et la raison à l'écran, les autres sources intactes (Tâche 6, `test_mic_refuse`).
2. FM1-A éteint, ou changé de firmware, pendant une capture depuis le FM-1 : la capture s'arrête proprement, rien ne plante (Tâche 6, `test_capture_fm1_interrompue`).
3. Fichier très court (0,05 s) ou très long (10 min) : le court se joue en une fois sans boucle, le long est coupé à 16 s avec un message (Tâche 6, `test_fichier_court_et_long`).
4. FM1-A n'est ni Pigeon ni zp12, ou il est éteint : seules FILE et ERASE sont proposées (Tâche 10, `test_cibles_selon_fm1a`).
5. Tempo changé, ou délié, pendant la lecture : la boucle suit le nouveau tempo dans le temps qui suit, déliée elle repart sur son propre tempo sans s'emballer (Tâche 5, `test_tempo_change_et_delie`).

---

### Tâche 1 : la bibliothèque pure `sample-lib`

**Files :**
- Create : `sample.html` (le seul bloc `<script id="sample-lib">` pour l'instant, dans une page minimale)
- Create : `tests/sample.test.mjs`

**Interfaces :**
- Produces (globales du bloc, chargées par `vm` comme `fm1-lib`) :
  - `TURN_SECONDS = 1.8`, `MAX_SECONDS = 16`, `BARS = [1, 2, 4, 8]`
  - `fitBars(seconds: number, bpm: number) -> { bars: 1|2|4|8|null, rate: number }` : les mesures qui demandent le moins de changement de vitesse ; `rate` = durée du sample / durée de la boucle ; au-delà d'une demi-octave (`|log2(rate)| > 0.5`), `{ bars: null, rate: 1 }`
  - `sliceBounds(frames: number, n = 16) -> Int32Array(n + 1)` : parts égales, arrondies, de 0 à `frames`
  - `encodeWav(channels: Float32Array[], sampleRate: number) -> Uint8Array` : RIFF PCM 16 bits, bornes à 32767 et -32768
  - `makeClock() -> { feed(byte: number, tMs: number): void, running: boolean, bpm: number|null, beats(tMs: number): number }` : suit l'horloge MIDI (0xFA remet à zéro et lance, 0xF8 compte, 0xFC arrête) ; `bpm` d'après les 24 dernières impulsions ; `beats` extrapole entre deux impulsions
  - `rollSeconds(bpm: number) -> number` : 60 / bpm / 4

- [ ] **Step 1 : écrire les tests**

```js
test("fitBars", () => {
  assert.deepEqual(plain(lib.fitBars(4, 120)), { bars: 2, rate: 1 });
  assert.equal(lib.fitBars(3.8, 120).bars, 2); assert.ok(Math.abs(lib.fitBars(3.8, 120).rate - 0.95) < 1e-9);
  assert.deepEqual(plain(lib.fitBars(16, 120)), { bars: 8, rate: 1 });
  assert.deepEqual(plain(lib.fitBars(0.05, 120)), { bars: null, rate: 1 });
});
test("sliceBounds", () => {
  const b = lib.sliceBounds(44100); assert.equal(b.length, 17); assert.equal(b[0], 0); assert.equal(b[16], 44100); assert.equal(b[8], 22050);
});
test("encodeWav", () => {
  const w = lib.encodeWav([Float32Array.of(1, -1, 0)], 44100), t = (o, n) => String.fromCharCode(...w.slice(o, o + n));
  assert.equal(t(0, 4), "RIFF"); assert.equal(t(8, 4), "WAVE"); assert.equal(w.length, 44 + 6);
  const d = new DataView(w.buffer); assert.equal(d.getUint32(24, true), 44100); assert.equal(d.getInt16(44, true), 32767); assert.equal(d.getInt16(46, true), -32768);
});
test("makeClock : tempo et phase à 64 mesures", () => {
  const c = lib.makeClock(), per = 60000 / (120 * 24);
  c.feed(0xfa, 0);
  let n = 0, t = 0;
  for (; n < 64 * 4 * 24; n++) { t = n * per + (n % 2 ? 2 : -2); c.feed(0xf8, t); }   // ±2 ms de gigue
  assert.ok(Math.abs(c.bpm - 120) < 0.5);
  assert.ok(Math.abs(c.beats(n * per) - 256) * 0.5 < 128 / 44100, "écart inférieur à 128 échantillons");
  c.feed(0xfc, t); assert.equal(c.running, false);
});
test("rollSeconds", () => assert.equal(lib.rollSeconds(120), 0.125));
```

- [ ] **Step 2 : vérifier qu'ils échouent**

Run : `node --test tests/sample.test.mjs`
Expected : FAIL (« bloc <script id="sample-lib"> absent »)

- [ ] **Step 3 : écrire les fonctions dans `sample.html`**

`makeClock` : la phase vient du nombre d'impulsions reçues, jamais d'une intégration du tempo estimé (pas de dérive) ; l'extrapolation entre deux impulsions est bornée à une impulsion.

- [ ] **Step 4 : vérifier qu'ils passent**

Run : `node --test tests/sample.test.mjs`
Expected : PASS (5 tests)

- [ ] **Step 5 : commit** `feat(sample): fonctions pures du module (tempo, découpe, wav, horloge)`

---

### Tâche 2 : le panneau, l'écran éteint et la ligne du dessous

**Files :**
- Modify : `sample.html`
- Modify : `tests/conftest.py` (arguments de Chromium : `--use-fake-device-for-media-stream`, `--use-fake-ui-for-media-stream`)
- Create : `tests/test_sample.py`

**Interfaces :**
- Produces :
  - SVG `#panel` (viewBox `0 0 1640 990`) ; commandes `[data-label="EDIT"|"SEND"|"PLAY"|"REC"]` (classe `cap`), molettes `[data-knob="MASTER"|"SELECT"]`, pads `.key[data-pad="0".."15"]`, `#platter`, `#xy`
  - canvas `#screen` (440 × 240) ; bouton `#go` « Allumer » ; ligne `.deck` avec `.skins` (six pastilles, `SKINS` d'`index.html`), `#fw-picker` (« Firmware » + « Module sample »), interrupteur `#power`
  - `window.__sample = { on: boolean, page: "capture"|"edit"|"send", skin: string }`

- [ ] **Step 1 : écrire les tests**

```python
def open_sample(page):
    page.goto(page.base + "sample.html")
    page.wait_for_selector("#panel [data-label='REC']")

def test_panneau(page):
    open_sample(page)
    assert page.locator("#panel .cap").count() == 4
    assert page.locator("#panel [data-knob]").count() == 2
    assert page.locator("#panel .key[data-pad]").count() == 16
    assert page.is_visible("#platter") and page.is_visible("#xy")
    assert page.evaluate("(() => { const c = document.getElementById('screen'); return [c.width, c.height]; })()") == [440, 240]
    assert page.locator(".deck .skins .swatch").count() == 6
    assert "Module sample" in page.inner_text("#fw-picker")

def test_langue_et_coloris(page):
    page.add_init_script("localStorage.setItem('fm1.lang', 'en')")
    open_sample(page)
    assert "Sample module" in page.inner_text("#fw-picker")
    page.click(".deck .skins .swatch >> nth=3")
    assert page.evaluate("window.__sample.skin") == "navy"

def test_allumer(page):
    open_sample(page)
    page.click("#go")
    page.wait_for_function("window.__sample.on && window.__sample.page === 'edit'")
    assert page.get_attribute("#power", "aria-checked") == "true"
```

- [ ] **Step 2 : vérifier qu'ils échouent** : Run : `python -m pytest -q tests/test_sample.py` ; Expected : FAIL

- [ ] **Step 3 : dessiner le panneau** d'après `panel({ kind: "module2" })` de la maquette, avec les matières et le coloris de `buildPanel()` ; sans animation CSS : les lumières viennent de `--i` (Tâche 9). Molettes : `Encoder` et `Haptics` recopiés, MASTER règle le volume (Tâche 3), SELECT est branché à la Tâche 7. La ligne `.deck` reprend les classes d'`index.html` pour que la page du Duo y place ses onglets.

- [ ] **Step 4 : vérifier qu'ils passent** : Run : `python -m pytest -q tests/test_sample.py` ; Expected : PASS

- [ ] **Step 5 : commit** `feat(sample): panneau du module au format du FM-1`

---

### Tâche 3 : le moteur audio

**Files :**
- Modify : `sample.html` (bloc `<script type="text/worklet" id="sample-worklet">`, processeur `"sample"`, et sa classe de page `SampleEngine`)
- Modify : `tests/test_sample.py`

**Interfaces :**
- Produces :
  - messages vers le worklet : `{ t: "load", ch: Float32Array[], rate, slices: Int32Array, fit: number }`, `{ t: "play", on: boolean }`, `{ t: "sync", beats: number, bpm: number }`, `{ t: "pad", i: number, on: boolean }`, `{ t: "roll", i: number, on: boolean }`, `{ t: "scratch", pos: number|null }` (secondes ; `null` relâche), `{ t: "reverse", on: boolean }`, `{ t: "cut", on: boolean }`, `{ t: "filter", x: number, y: number }` (0..1 ; x 0,5 = neutre), `{ t: "echo", amount: number, feedback: number }`, `{ t: "master", v: number }`, `{ t: "slice", i: number, start: number, len: number, pitch: number, gain: number }`
  - messages du worklet, environ 60 par seconde : `{ t: "pos", beats: number, slice: number, disc: number, bpm: number }` (disc : angle du disque, en radians)
  - `SampleEngine` : `on`, `playing`, `an` (AnalyserNode relié à la sortie), `send(msg)`, `load(sample)`, `play(on)`, `pos` (dernier `pos` reçu)
  - `window.__engine()` rend l'instance (Tâche 5 y ajoute l'interface du Duo)

- [ ] **Step 1 : écrire les tests** (un sample de test : 2 s de sinus à 440 Hz, chargé par `window.__engine().load(...)` depuis un `Float32Array`)

```python
def rms_out(page):
    return page.evaluate("() => { const a = window.__engine().an, d = new Float32Array(a.fftSize); a.getFloatTimeDomainData(d); return Math.sqrt(d.reduce((s, x) => s + x * x, 0) / d.length); }")

def test_lecture_et_master(page): ...       # play → rms_out > 0.05 ; master 0 → rms_out < 0.001
def test_cut(page): ...                     # cut on → rms_out < 0.001 ; cut off → > 0.05
def test_filtre(page): ...                  # sinus 4 kHz : filter x 0.05 (passe-bas fermé) → rms < 30 % de celui à x 0.5
def test_scratch_tient_la_position(page): ...  # scratch pos 0.5 tenue 300 ms → pos.beats ne bouge pas ; null → reprend
def test_roll(page): ...                    # roll i 0 à 120 BPM pendant 1 s → 8 attaques (enveloppe), ± 1
```

- [ ] **Step 2 : vérifier qu'ils échouent**

- [ ] **Step 3 : écrire le worklet** : lecture à vitesse variable avec interpolation cubique ; boucle de `fit` × durée ; `scratch` mène la position (la boucle continue dessous : au relâchement, la lecture revient à la position de la boucle, « slip ») ; moteur du disque avec une inertie d'environ 200 ms au départ et à l'arrêt ; filtre à variable d'état (passe-bas à gauche, passe-haut à droite, résonance en y) ; écho au huitième pointé du tempo.

- [ ] **Step 4 : vérifier qu'ils passent** ; **Step 5 : commit** `feat(sample): moteur audio du module`

---

### Tâche 4 : le cadre B du Duo et la section « Modules »

**Files :**
- Modify : `index.html` (le Duo, l. 7391-7600 : `src` du cadre B, `allow`, `__duo.useB` ; la liste des firmwares, `renderSections()` l. 6761 : section « Modules » en tête quand `FM1_ID === "b"` et dans le Duo ; au chargement, `?choisir` ouvre la liste par `openSheet()`)
- Modify : `sample.html` (`#fw-picker`)
- Modify : `tests/test_sample.py`

**Interfaces :**
- Produces :
  - `window.__duo.useB(kind: "fm1"|"sample", opts?: { choisir?: boolean })` : garde `fm1.duo.b`, charge `sample.html?fm1=b` ou `?fm1=b` (`&choisir`) dans le cadre B
  - les deux iframes : `allow="midi; autoplay; microphone; display-capture"`
  - l'entrée de la section : `.fw-item[data-id="sample"]`, nom « Module sample »
  - `#fw-picker` du module : dans le Duo `parent.__duo.useB("fm1", { choisir: true })`, seul `location.href = "index.html"`

- [ ] **Step 1 : écrire les tests**

```python
def test_choisir_le_module_dans_b(page): ...   # Duo ; liste de FM1-B ; clic sur [data-id=sample] → cadre B sur sample.html, localStorage fm1.duo.b == "sample"
def test_revenir_a_un_fm1(page): ...           # depuis le module, #fw-picker → cadre B sur index.html?fm1=b&choisir, la liste est ouverte, fm1.duo.b == "fm1"
def test_module_garde_au_rechargement(page): ... # fm1.duo.b = "sample" avant chargement → cadre B sur sample.html
def test_pas_de_section_modules_ailleurs(page): ... # Solo et FM1-A : aucun [data-id=sample]
def test_allow_micro(page): ...                # les deux iframes ont microphone dans allow
```

- [ ] **Step 2 : vérifier qu'ils échouent**

- [ ] **Step 3 : modifier `index.html`** aux seuls endroits listés

- [ ] **Step 4 : vérifier qu'ils passent, et que le Duo existant passe** : Run : `python -m pytest -q tests/test_sample.py tests/test_duo.py tests/test_picker.py` ; Expected : PASS

- [ ] **Step 5 : commit** `feat(duo): le module sample dans le cadre B`

---

### Tâche 5 : l'horloge du tempo lié

**Files :**
- Modify : `sample.html`
- Modify : `tests/test_sample.py`

**Interfaces :**
- Consumes : `makeClock` (Tâche 1), `SampleEngine` (Tâche 3), `__duo` (Tâche 4)
- Produces, sur `window.__engine()` : `name = "Module sample"`, `entry = { id: "sample", nom: "Module sample", natif_horloge: true, demarre: true }`, `midiIn(bytes: Uint8Array)`, `playLight() -> "green"|"off"`, `greenAt: number` (`performance.timeOrigin + performance.now()` au dernier vert) ; `window.__sample.loopBeats() -> number` ; `window.__sample.bpm` (tempo propre, 120 par défaut, gardé sous `fm1.sample.bpm`)

- [ ] **Step 1 : écrire les tests**

```python
def test_play_lance_les_deux(page): ...        # FM1-A FM-1+VA allumé, B module allumé avec un sample ; tempo lié à 150 ; PLAY du module → __duo.playing et module.playing ; PLAY encore → les deux arrêtés
def test_boucle_en_phase(page): ...            # lié à 240 BPM, 8 mesures : |loopBeats() - impulsions/24| < 0.05 temps
def test_tempo_change_et_delie(page): ...      # en lecture, BPM 120 → 180 : dans le temps qui suit, __engine().pos.bpm vaut 180 ± 2 ; délié : module.playing reste, il suit __sample.bpm
def test_seul_avec_son_tempo(page): ...        # sample.html seul : PLAY joue à __sample.bpm
```

- [ ] **Step 2 : vérifier qu'ils échouent**

- [ ] **Step 3 : brancher** : `midiIn` donne chaque octet d'horloge à `makeClock` ; à chaque impulsion, `send({ t: "sync", beats, bpm })` ; PLAY seul appelle `parent.__duoPlay()` quand `parent.__duo.linked`, sinon `play(!playing)`.

- [ ] **Step 4 : vérifier qu'ils passent** ; **Step 5 : commit** `feat(sample): le module suit le tempo lié`

---

### Tâche 6 : la capture et la mémoire des samples

**Files :**
- Modify : `sample.html` (sources, REC, base `fm1-samples`, prise sur FM1-A : un petit worklet `"sample-tap"` ajouté au contexte `window.__ac` de FM1-A, relié à `__engine().an`, ses blocs envoyés par `MessageChannel`)
- Modify : `tests/test_sample.py`

**Interfaces :**
- Consumes : `fitBars`, `sliceBounds`, `MAX_SECONDS` (Tâche 1), `SampleEngine.load` (Tâche 3), l'horloge (Tâche 5)
- Produces :
  - `Sample = { id: "S01"…, name: string, rate: number, ch: Float32Array[], bars: number|null, fit: number, slices: Int32Array(17), pads: (null|{ ch: Float32Array[], rate: number, name: string })[16], cols: { start: number, len: number, pitch: number, gain: number }[16] }` : start et len en millisecondes (start depuis la limite de la tranche), pitch en demi-tons (-24..24), gain 0..100 (défaut 0, longueur de la tranche, 0, 100) ; un cran de SELECT = 1 ms, 1 demi-ton ou 1
  - `window.__sample.capture(source: "mic"|"fm1"|"tab", opts?: { seconds?: number, pad?: number }) -> Promise<Sample>` ; `window.__sample.importFile(file: File) -> Promise<Sample>` ; `window.__sample.samples: Sample[]` ; `window.__sample.cur: number` ; `window.__sample.sources() -> { mic: boolean|string, fm1: boolean, file: true, tab: boolean }` (une chaîne : la raison du refus)
  - REC : arme ; part au premier bloc au-dessus du seuil (THRESH, -30 dB par défaut ; OFF part tout de suite) ; lié, part sur un temps et dure LENGTH mesures (2 par défaut) ; REC encore arrête ; puis découpe, `load`, page `edit`

- [ ] **Step 1 : écrire les tests**

```python
def test_capture_micro(page): ...              # Chromium et son faux micro : capture("mic", seconds=1) → un sample de 16 tranches, rms > 0.001 ; getUserMedia appelé avec les trois traitements à false
def test_mic_refuse(page): ...                 # getUserMedia rejeté (script d'init) → sources().mic est une chaîne, la puce MIC grisée, capture("fm1") reste possible
def test_capture_fm1(page): ...                # Duo, FM1-A FM-1+VA joue une note : capture("fm1", seconds=1) → rms > 0.01, getUserMedia jamais appelé
def test_capture_fm1_interrompue(page): ...    # FM1-A éteint pendant la capture → la promesse se résout avec ce qui a été capté, rien dans la console d'erreurs
def test_fichier(page, tmp_path): ...          # un .wav de 4 s à 120 BPM → bars 2, fit 1, 16 tranches
def test_fichier_court_et_long(page, tmp_path): ...  # 0,05 s → bars None ; 20 s → 16 s gardées, message « 16 s »
def test_rec_pad(page): ...                    # REC avec le pad 3 tenu → pads[3] rempli, ch du sample inchangé
def test_samples_gardes(page): ...             # deux captures, interrupteur éteint puis rechargement → samples.length == 2, cur gardé
def test_tab_selon_navigateur(page): ...       # getDisplayMedia absent (script d'init) → sources().tab False, pas de puce TAB
```

- [ ] **Step 2 : vérifier qu'ils échouent** ; **Step 3 : écrire la capture** (l'import accepte aussi `.mp4` et `.mov`, pour l'enregistrement d'écran d'iPadOS : à essayer à la main sur l'iPad) ; **Step 4 : vérifier qu'ils passent** ; **Step 5 : commit** `feat(sample): capture (micro, FM-1, fichier) et mémoire des samples`

---

### Tâche 7 : l'écran et ses gestes

**Files :**
- Modify : `sample.html`
- Modify : `tests/test_sample.py`

**Interfaces :**
- Consumes : `Sample`, `__sample` (Tâches 5, 6)
- Produces : `window.__sample.page`, `window.__sample.col: number|null`, `window.__sample.zoom: { from: number, to: number }` (fraction du sample) ; EDIT → `edit`, SEND → `send` (Tâche 10 fait le second appui), REC → `capture` (Tâche 6)

- [ ] **Step 1 : écrire les tests**

```python
def test_pages(page): ...                      # EDIT, SEND, REC changent __sample.page ; l'écran a des pixels allumés sur chaque page
def test_colonne_et_select(page): ...          # toucher la colonne START (x 55, y 30 en pixels de l'écran) → col 0 ; SELECT +3 crans lents → cols[tranche choisie].start == 3
def test_select_sans_colonne(page): ...        # col None : SELECT +1 → cur passe au sample suivant
def test_poignee(page): ...                    # glisser la poignée de début de la tranche 5 de 20 px → start augmente
def test_pincer(page): ...                     # deux pointeurs qui s'écartent sur la forme d'onde → zoom.to - zoom.from < 1
def test_tranche_touchee(page): ...            # toucher la tranche 9 → tranche choisie 9
def test_puces(page): ...                      # page capture, toucher la puce FILE → l'import de fichier s'ouvre (input[type=file] cliqué)
```

- [ ] **Step 2 : vérifier qu'ils échouent** ; **Step 3 : dessiner les trois pages** d'après `lcdCapture`, `lcdEdit`, `lcdSend` de la maquette, sur le canvas, à chaque image ; les touchers en pixels de l'écran ; **Step 4** ; **Step 5 : commit** `feat(sample): l'écran tactile du module`

---

### Tâche 8 : platine, zone XY et pads

**Files :**
- Modify : `sample.html`
- Modify : `tests/test_sample.py`

**Interfaces :**
- Consumes : messages du worklet (Tâche 3), `TURN_SECONDS`, `rollSeconds` (Tâche 1)
- Produces : `window.__sample.touch = { platter: number, xy: number, cut: boolean, reverse: boolean }` (nombre de pointeurs posés, états)

- [ ] **Step 1 : écrire les tests** (pointeurs simulés par `page.dispatch_event` sur `#platter`, `#xy`, `.key[data-pad]`, avec `pointerId`, `pressure`, `pointerType`)

```python
def test_scratch(page): ...                    # un doigt tourne d'un quart de tour en 200 ms → scratch pos avance de 0,45 s ± 0,05
def test_main_posee(page): ...                 # doigt immobile 300 ms → pos.beats ne bouge pas
def test_relache_en_phase(page): ...           # doigt levé → 500 ms après, |pos.beats - position de la boucle| < 0.05
def test_lancer_en_arriere(page): ...          # glissé vif à l'envers puis levé → reverse True tant que le disque tourne à l'envers
def test_cut_deuxieme_doigt(page): ...         # deux doigts sur la platine → cut True ; le second levé → False, le scratch continue
def test_xy_filtre_et_retour(page): ...        # un doigt en (0.1, 0.8) → filter x 0.1, y 0.8 ; levé → x revient à 0.5 en moins de 300 ms
def test_xy_echo(page): ...                    # deux doigts écartés de la moitié de la zone → echo amount ≈ 0.5
def test_stylet(page): ...                     # pointerType pen, pressure 0.3 puis 0.9 → l'effet touché suit la pression
def test_pad_et_roll(page): ...                # pad 4 tapé → pad on puis off ; tenu 400 ms → roll on, levé → off
def test_clavier_et_midi(page): ...            # Espace → PLAY ; R → REC ; midiIn([0x90, 36, 100]) → pad 0 on, [0x80, 36, 0] → off
```

- [ ] **Step 2** ; **Step 3 : écrire les gestes** : la position du disque = angle cumulé du doigt autour de `#platter` × `TURN_SECONDS / 2π` ; lancer en arrière : vitesse angulaire négative au relâchement ; zone XY : retour à zéro en 250 ms ; pression du stylet : quantité de l'effet ; un pad tenu plus de 250 ms passe en roll ; sur PC, Espace = PLAY, R = REC, les pads sur deux rangées de lettres ; notes MIDI 36 à 51 sur les pads ; **Step 4** ; **Step 5 : commit** `feat(sample): platine, zone XY et pads`

---

### Tâche 9 : les lumières

**Files :**
- Modify : `sample.html`
- Modify : `tests/test_sample.py`

**Interfaces :**
- Consumes : `pos` (Tâche 3), `touch` (Tâche 8)
- Produces : la variable `--i` (0..1) sur `.key[data-pad]`, `.cap`, et les 32 LED `#platter .led[data-i]` ; classes de teinte `hue-green` (PLAY), `hue-red` (REC)

- [ ] **Step 1 : écrire les tests**

```python
def test_led_des_pads(page): ...               # en lecture, le pad de pos.slice a --i == 1 ; le précédent 0 < --i < 1 (traînée) ; la tranche choisie au repos ≈ 0.25
def test_couronne(page): ...                   # la LED la plus allumée est celle de round(disc / 2π × 32) mod 32
def test_play_bat(page): ...                   # en lecture, --i de PLAY passe au-dessus de 0.9 une fois par temps
def test_rec(page): ...                        # armé : REC clignote ; en capture : --i == 1, rouge
def test_point_xy(page): ...                   # un doigt dans #xy → un point lumineux sous le doigt ; deux doigts → deux points ; levés → aucun
```

- [ ] **Step 2** ; **Step 3 : écrire `lights()`**, appelée à chaque image comme `panel.lights()` d'`index.html` ; **Step 4** ; **Step 5 : commit** `feat(sample): lumières des pads, de la couronne et des touches`

---

### Tâche 10 : l'envoi

**Files :**
- Modify : `index.html` (une ligne après la définition de `takeSamples`, l. 7142 : `window.__takeSamples = takeSamples;`, et `takeSamples` rend le texte d'état)
- Modify : `sample.html`
- Modify : `.github/workflows/pages.yml` (les tests d'envoi dans la liste de la l. 201, avec les natifs construits)
- Modify : `tests/test_sample.py`

**Interfaces :**
- Consumes : `encodeWav` (Tâche 1), `Sample` (Tâche 6), `parent.__duo.frames.a.contentWindow.__takeSamples(files: File[]) -> Promise<string>`
- Produces : `window.__sample.targets() -> ("pigeon"|"zp12"|"file"|"erase")[]` ; `window.__sample.send(target) -> Promise<string>` (le texte affiché)

- [ ] **Step 1 : écrire les tests**

```python
def test_cibles_selon_fm1a(page): ...          # FM1-A éteint, puis FM-1+VA → targets() == ["file", "erase"]
def test_envoi_pigeon(page, tmp_path): ...     # natif pigeon construit (sinon ignoré) : FM1-A Pigeon, sample de 4 s ; SEND puis SEND → demande de confirmation ; confirmée → status de FM1-A contient « chargé »
def test_envoi_zp12(page, tmp_path): ...       # natif zp12 : status de FM1-A commence par « zp12 : 16 sons »
def test_envoi_fichier(page): ...              # cible file → un téléchargement « S01.wav », en-tête RIFF
def test_erase(page): ...                      # cible erase, confirmée → le sample disparaît, de la base aussi
```

- [ ] **Step 2** ; **Step 3 : écrire l'envoi** : Pigeon reçoit d'abord le sample entier (la chanson) puis les 16 tranches (ou les sons de pads), en .wav ; zp12 les 16 tranches ; FILE par un lien `download` ; la confirmation sur l'écran : « Replaces Pigeon's whole bank. SEND to confirm. » ; **Step 4** ; **Step 5 : commit** `feat(sample): envoi vers Pigeon, zp12 et en fichier`

---

### Tâche 11 : la sauvegarde

**Files :**
- Modify : `backup.js` (comme `COPIES` : `SAMPLES = { name: "fm1-samples", version: 1, stores: ["samples"] }` ; `createBackup` ajoute `samples` ; `restoreBackup` ne les écrit que si le champ existe)
- Modify : `tests/test_backup.py`

- [ ] **Step 1 : écrire les tests**

```python
def test_samples_dans_la_sauvegarde(page): ...  # deux samples ; createBackup().samples a 2 entrées ; un troisième ; restoreBackup → les deux d'origine, Float32Array intacts
def test_sauvegarde_sans_samples_les_garde(page): ...  # champ samples absent → samples présents inchangés
```

- [ ] **Step 2** ; **Step 3** ; **Step 4 : Run** `python -m pytest -q tests/test_backup.py` ; Expected : PASS ; **Step 5 : commit** `feat(backup): les samples du module dans la sauvegarde`

---

### Tâche 12 : publication et documentation

**Files :**
- Modify : `.github/workflows/pages.yml` (l. 130 : `cp index.html engine.js backup.js sample.html _site/`)
- Modify : `README.md`, `README.en.md` (une puce dans « Utilisation » : le module sample dans FM1-B du Duo, ses sources, l'envoi vers Pigeon et zp12 ; hors du tableau généré)
- Modify : `index.html` (le manuel, rubrique « Solo et Duo » : une phrase sur le module)

- [ ] **Step 1 : vérifier** : Run : `node --test tests/*.test.mjs && python -m pytest -q tests/` ; Expected : PASS (les tests natifs ignorés sans paquets construits)
- [ ] **Step 2 : commit** `docs: le module sample dans le README et le manuel ; publication de sample.html`
