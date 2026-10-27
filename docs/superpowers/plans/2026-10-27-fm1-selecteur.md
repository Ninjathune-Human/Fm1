# Sélecteur de firmwares FM-1 : plan de réalisation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** faire tourner, derrière le panneau FM-1 existant, soit la réimplémentation FM-1+VA, soit l'un des firmwares open source du FM-1 exécuté par le cœur fm1-emu, avec un sélecteur.

**Architecture:** la page `index.html` (reprise de l'artefact FM-1+VA) garde son panneau ; le panneau parle à un objet hôte (Proxy) qui délègue au moteur actif : `Firmware` (FM-1+VA, inchangé) ou `EmuFirmware` (nouveau, qui pilote l'AudioWorklet de fm1-emu). Une action GitHub compile le cœur WebAssembly au commit figé et publie le site.

**Tech Stack:** HTML/JS sans framework, AudioWorklet, WebAssembly (fm1-emu, Rust), IndexedDB ; tests `node --test` et Playwright Python (Chromium sans interface) ; GitHub Actions et GitHub Pages.

**Spec:** `docs/superpowers/specs/2026-10-27-fm1-selecteur-design.md`

## Global Constraints

- fm1-emu figé au commit `1c8661daa1bbfddbb7d32d927bbaf831343b7d3b` ; horloge émulée 100 MHz.
- `index.html` reste un seul fichier ; `runtime/` est produit par l'action, jamais commité.
- Le moteur FM-1+VA (classe `Firmware`, worklet `#engine-src`, `engine.js`) n'est pas modifié. Toute modification du code existant se limite aux points d'accroche nommés dans les tâches.
- Interface en français, sans emoji ni tiret cadratin ; design sobre ; tout menu qui se déplie porte une encoche qui pivote ; souris, tactile et stylet ; iPhone, iPad, PC. Charger les skills `apple-hig-design` et `création-dun-champ-de-recherche-intelligent` avant la tâche 6.
- Fichiers repris de fm1-emu : en-tête et licence MIT conservés (`runtime/LICENSE-fm1-emu.txt`).
- Chaque commit se termine par :
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` puis `Claude-Session: https://claude.ai/code/session_01AAmNf3tasD2kzoHkSYXP9g`.
- Dépôt : `Ninjathune-Human/Fm1`, branche `main`.

## Review Focus

1. iPhone : un changement de firmware après l'allumage ne doit pas exiger un nouveau toucher ; le même `AudioContext` est réutilisé (test tâche 5).
2. Deux firmwares choisis à moins de 50 ms d'intervalle : le dernier gagne, un seul nœud audio reste branché (test tâche 6).
3. Une touche tenue pendant un changement de moteur ne reste pas bloquée (test tâche 5).
4. IndexedDB indisponible (navigation privée) : le firmware tourne, la ligne d'état dit que les sauvegardes sont indisponibles (test tâche 7).
5. Canvas redimensionné (zoom, rotation) : l'écran émulé reste net, sans lissage (test tâche 5).

---

### Task 1: Base du dépôt, page reprise à l'identique

**Files:**
- Create: `index.html`, `engine.js` (copies exactes de l'artefact, version `1793124748-9ff1`)
- Create: `tests/serve.py`, `tests/test_va_smoke.py`, `.gitignore` (`runtime/`, `__pycache__/`, `test-results/`)

**Interfaces:**
- Produces: `tests/serve.py` : `serve(root: str) -> contextmanager[str]` (serveur HTTP local, renvoie l'URL de base) ; utilisé par tous les tests Playwright.

- [ ] **Step 1:** Récupérer `index.html` et `engine.js` de l'artefact `https://claude.ai/artifact/6tvcwtxm9xiXhXXXY4akFg` (action `read`, `path`) et vérifier les tailles : 328 598 et 53 289 octets.
- [ ] **Step 2: Tests de non-régression** `test_va_smoke.py` :
  - `test_power_on` : ouvrir la page, cliquer `#go`, attendre `#status` = « Allumé. », appuyer la touche 12 du clavier 300 ms ; assertions : `#screen` contient au moins 1 000 pixels non noirs ; `window.__fw.on === true` ;
  - `test_tuning` : sur le premier preset, touche donnant A4 (`window.__fw` convertit l'index en note : chercher l'index dont la note MIDI vaut 69), FFT de l'analyseur : pic à 440 Hz ± 3 Hz.
- [ ] **Step 3:** `python3 -m pytest tests/test_va_smoke.py -v` → PASS.
- [ ] **Step 4:** Commit « Reprise de la page FM-1+VA ».

### Task 2: Compilation du cœur et publication

**Files:**
- Create: `.github/workflows/pages.yml`

**Interfaces:**
- Produces: sur Pages et dans la version GitHub `runtime-1c8661d` : `runtime/fm1_web.wasm`, `runtime/worklet.js` (processeur `"fm1"`), `runtime/persistence.js` (`SaveStore`, `packageHash`, `changedSectors`, `packSectors`), `runtime/LICENSE-fm1-emu.txt`.

- [ ] **Step 1:** Écrire le workflow, déclenché sur `push` vers `main` et `workflow_dispatch`, permissions `contents: write, pages: write, id-token: write` :
  1. checkout du dépôt ; checkout de `joakimeriksson/fm1-emu` au commit figé dans `fm1-emu/` ;
  2. `rustup target add wasm32-unknown-unknown` ;
  3. dans `fm1-emu/`, avec `CARGO_PROFILE_RELEASE_CODEGEN_UNITS=1` et `RUSTFLAGS="-Cllvm-args=-inline-threshold=2000 -Clink-arg=--export-table -Clink-arg=--growable-table"` : `cargo build --release -p fm1-web --target wasm32-unknown-unknown --target-dir target/wasm` ;
  4. assembler `_site/` : `index.html`, `engine.js`, `firmwares/`, `assets/`, et `_site/runtime/` avec le `.wasm`, `web/worklet.js`, `web/persistence.js`, `LICENSE` renommé `LICENSE-fm1-emu.txt` ;
  5. `actions/upload-pages-artifact@v3` puis `actions/deploy-pages@v4` ;
  6. créer ou mettre à jour la version `runtime-1c8661d` avec les fichiers de `_site/runtime/` (`gh release create` si absente, sinon `gh release upload --clobber`).
- [ ] **Step 2:** Activer Pages en mode « GitHub Actions » par l'API (`POST /repos/Ninjathune-Human/Fm1/pages`, `build_type: workflow`). En cas de refus, demander à l'utilisateur de le régler dans Settings > Pages.
- [ ] **Step 3:** Commit, push, suivre l'exécution par l'API jusqu'à sa fin. Attendu : conclusion `success`.
- [ ] **Step 4: Vérification :** télécharger les 4 fichiers de la version dans `runtime/` local ; `fm1_web.wasm` commence par `\0asm` ; `WebAssembly.validate` en Node renvoie `true`.

### Task 3: Paquets et catalogue

**Files:**
- Create: `firmwares/<id>.fwsc` (106), `firmwares/catalogue.json`, `firmwares/licences/<id>/…`
- Create: `tests/catalogue.test.mjs`

**Interfaces:**
- Produces: `catalogue.json` = `{ genere_le, defaut, firmwares: Entry[] }` ; `Entry` = `{ id, nom, version, auteur, categories: string[], licence, beta: bool, fichier: string|null, sha256, depot, commit_source, description, emulateur_fm1emu, paquet_en_ligne: string|null }` (format du kit livré le 27 octobre).

- [ ] **Step 1:** Copier `firmwares/`, `catalogue.json` et `licences/` depuis le kit `FM1_firmwares_open_source.zip`.
- [ ] **Step 2: Test** `catalogue.test.mjs` : pour chaque entrée dont `fichier` n'est pas nul, le fichier existe et son SHA-256 égale `sha256` ; 115 entrées ; ids uniques ; `bubba` présent ; toute entrée sans `fichier` a un `paquet_en_ligne` commençant par `https://thefirmwarehub.com/fw/`.
- [ ] **Step 3:** `node --test tests/` → PASS. Commit « Paquets et catalogue des firmwares ».

### Task 4: Fonctions de liaison pures

**Files:**
- Modify: `index.html` : nouveau bloc `<script id="fm1-lib">` placé avant le script principal
- Create: `tests/lib.test.mjs` (extrait le bloc par expression régulière et l'exécute avec `node:vm`)

**Interfaces:**
- Produces (globales du bloc) :
  - `KEY_IDS: Record<string, number>` = `OCT-`:0, `OCT+`:1, `FX`:2, `SEL`:3, `ENV`:4, `LFO`:5, `EDIT`:6, `GLO`:7, `HOME`:8, `SAVE`:9, `ARP`:10, `SEQ`:11, `PLAY`:12, `REC`:13 ;
  - `noteId(i: number): number` = `14 + i` pour `i` de 0 à 26, sinon `-1` ;
  - `ENC_IDS: Record<string, number>` = `SELECT`:0, `ALGORITHM`:1, `KNOB1`:2, `KNOB2`:3, `KNOB3`:4, `KNOB4`:5, `PRESETS`:6 ;
  - `potAfter(pot: number, clicks: number): number` : `pot + 8 × clicks`, borné à [0, 1023] ;
  - `rgb565ToRgba(src: Uint16Array, dst: Uint8ClampedArray): void` (alpha 255, canaux étendus sur 8 bits par réplication des bits hauts) ;
  - `LIT = 0.25` ; `isLit(leds: Float32Array, id: number): boolean` (`leds[id] > LIT`) ;
  - `CATEGORY_ORDER` = `["FM-1+VA", "Officiel", "Groovebox", "Synthé", "Accords", "Boîte à rythmes", "Tracker", "Autre"]` ;
  - `HIDDEN = new Set(["bubba"])` ;
  - `groupCatalogue(entries: Entry[], query: string): { categorie: string, items: Entry[] }[]` : filtre sans tenir compte des accents ni de la casse sur `nom`, `auteur`, `description` ; exclut `HIDDEN` ; une entrée va dans sa première catégorie (« Base de développement » va dans « Autre ») ; sections dans `CATEGORY_ORDER`, vides omises ; tri par `nom` dans chaque section.

- [ ] **Step 1: Tests** : `KEY_IDS.SEL === 3`, `noteId(26) === 40`, `noteId(27) === -1` ; `potAfter(1020, 2) === 1023`, `potAfter(4, -1) === 0` ; `rgb565ToRgba` : `0xF800` → `[255,0,0,255]`, `0x07E0` → `[0,255,0,255]`, `0x001F` → `[0,0,255,255]`, `0x0000` → `[0,0,0,255]` ; `isLit` vrai pour 0,3 et faux pour 0,2 ; `groupCatalogue(catalogue, "")` n'a pas `bubba` et commence par « Officiel » ; `groupCatalogue(catalogue, "synthe")` ne contient que des entrées dont nom, auteur ou description contiennent « synthe » sans accent ; `groupCatalogue(catalogue, "zzz")` → `[]`.
- [ ] **Step 2:** `node --test tests/lib.test.mjs` → FAIL (bloc absent).
- [ ] **Step 3:** Écrire le bloc `#fm1-lib`.
- [ ] **Step 4:** `node --test tests/` → PASS ; `test_va_smoke.py` → PASS. Commit « Fonctions de liaison ».

### Task 5: Moteur émulé et changement de moteur

**Files:**
- Modify: `index.html` : nouveau bloc `<script id="fm1-emu">` (classe `EmuFirmware`) ; dans le script principal, seuls changent la création de `fw` (hôte Proxy), `switchOn()` et l'ajout de `useEngine()`
- Create: `tests/test_emu.py`

**Interfaces:**
- Consumes: tâche 2 (`runtime/*`), tâche 3 (`Entry`), tâche 4 (globales `fm1-lib`).
- Produces:
  - `class EmuFirmware` : `constructor(canvas: HTMLCanvasElement, va: Firmware)` ; membres utilisés par le panneau, mêmes noms que `Firmware` : `on`, `T` et `G` (lus sur `va`), `gdirty`, `idx`, `onTheme`, `power()`, `draw()`, `press(label)`, `release(label)`, `turn(label, n, v)`, `keyDown(i, src)`, `keyUp(src)`, `keyLit(i)`, `buttonLit(label)` ; `takePatch` et `askBank` lèvent `Error("Réservé à FM-1+VA")` ; propres : `attach(ac: AudioContext, wasm: ArrayBuffer): Promise<void>` (charge `runtime/worklet.js`, crée le nœud `"fm1"`, branche un `AnalyserNode` exposé en `an`), `boot(entry: Entry | {id:"local", nom, bytes}, opts?: {reset?: boolean}): Promise<boolean>`, `stop(): Promise<void>` (sauvegarde, puis débranche et ferme le port) ;
  - `useEngine(entry): Promise<boolean>` dans le script principal : arrête le moteur courant (relâche touches et notes), réutilise l'`AudioContext` unique, démarre le nouveau, met à jour l'hôte ; renvoie `false` et garde l'ancien moteur en cas d'échec ;
  - `onWorklet(e: MessageEvent): void` sur `EmuFirmware` (messages du worklet ; appelable par les tests) ;
  - le script principal étant une IIFE, il expose pour les tests : `window.__host` (Proxy), `window.__engine()` (moteur actif), `window.__ac`, `window.__useEngine(entry)`, `window.__nodes()` (nœuds audio des moteurs actuellement branchés), `window.__catalogue` (entrées chargées).
- La logique de session et de sauvegarde reprend `web/main.js` de fm1-emu, lignes 751 à 962 (MIT, mention en commentaire) : `boot` envoie `{type:"boot", seq, wasm, package, sectors, syx:null, mhz:100, jit:true}` ; `booted` → instantané de base ; `flash-changed` puis `snapshot` → `SaveStore.save` ; « Réglages d'usine » = `boot(entry, {reset:true})`.
- `draw()` : copie le dernier `lcd` dans un canvas 240 × 240 hors écran via `rgb565ToRgba`, puis `drawImage` à la taille du canvas avec `imageSmoothingEnabled = false` ; écran noir tant qu'aucune image.
- `turn("MASTER", n)` → `pot` via `potAfter` (départ 900) ; autres molettes → `enc` avec `n` crans.

- [ ] **Step 1: Tests** (`test_emu.py`, sur le serveur local avec `runtime/` téléchargé) :
  - `test_boot_felucca` : allumer, `useEngine(felucca)` → `true` en moins de 30 s ; après 3 s, `#screen` a au moins 2 000 pixels non noirs ; touche 12 tenue 500 ms → RMS de `an` > 0,001 ;
  - `test_same_audiocontext` : `__ac` identique avant et après deux changements ;
  - `test_no_stuck_key` : `keyDown(5)` sur FM-1+VA, `useEngine(felucca)`, puis retour à FM-1+VA : aucune note active (`window.__engine().keyNotes.size === 0`) ;
  - `test_crisp_lcd` : canvas forcé à 731 px, après `draw()` le contexte a `imageSmoothingEnabled === false` ;
  - `test_saves_kept` : sur Felucca, bouton SAVE tenu 1 s, attendre un message `snapshot` ; passer à zp12 puis revenir : `SaveStore.load(hash)` renvoie au moins un secteur ;
  - `test_factory_reset_emu` : `boot(felucca, {reset:true})` → `true`, puis `SaveStore.load(hash).sectors.length === 0` ;
  - `test_va_still_works` : retour à FM-1+VA, mêmes assertions que `test_power_on`.
- [ ] **Step 2:** Lancer → FAIL. **Step 3:** Implémenter. **Step 4:** `pytest tests -v` et `node --test tests/` → PASS. Commit « Moteur émulé fm1-emu ».

### Task 6: Sélecteur

**Files:**
- Modify: `index.html` : contrôle `#fw-picker` dans la barre sous le panneau (à côté de `#swatches`), panneau `#fw-sheet`, styles ; commandes contextuelles (`#syx` masqué hors FM-1+VA ; `#reset` appelle `boot(entry, {reset:true})` pour un firmware émulé)
- Create: `tests/test_picker.py`

**Interfaces:**
- Consumes: `groupCatalogue`, `useEngine`, `catalogue.json` (chargé par `fetch("firmwares/catalogue.json")`).
- Produces: `localStorage["fm1.firmware"]` = id du dernier firmware démarré (`"fm1va"` par défaut) ; libellés exacts : « Firmware », « Rechercher un firmware », « Ouvrir un .fwsc… », « Démarrage de {nom}… », marqueurs « bêta », « en ligne », « non évalué ».

- [ ] **Step 1: Tests** :
  - `test_open_close` : clic sur `#fw-picker` → `#fw-sheet` visible, `aria-expanded="true"`, encoche tournée ; Échap → fermé ;
  - `test_search` : saisir « sloop » → seules des lignes dont le texte contient « sloop » ; aucune ligne « Bubba Machine » quelle que soit la recherche ;
  - `test_pick` : toucher « SLOOP » → `#status` contient « Démarrage de SLOOP… » puis le nom ; le contrôle affiche « SLOOP » ;
  - `test_last_wins` : deux clics à 30 ms (X0X puis zp12) → moteur actif = zp12, un seul `AudioWorkletNode` branché (`window.__nodes().length === 1`) ;
  - `test_restore_last` : rechargement → zp12 redémarre après « Allumer » ;
  - `test_sections_fold` : un titre de section replie sa liste et fait pivoter son encoche ;
  - `test_layouts` : captures à 390 × 844, 820 × 1180 et 1440 × 900 ; à 390 px la feuille est ancrée en bas (`bottom` = 0) ; à 1440 px elle s'ouvre sous le contrôle ;
  - `test_contextual_controls` : `#syx` visible avec FM-1+VA, masqué avec SLOOP ;
  - `test_open_local` : « Ouvrir un .fwsc… » avec `firmwares/felucca.fwsc` → le contrôle affiche le nom du fichier sans extension et l'écran s'allume ; rien n'est ajouté au catalogue.
- [ ] **Step 2:** FAIL. **Step 3:** Implémenter. **Step 4:** PASS, puis contrôle visuel des trois captures. Commit « Sélecteur de firmwares ».

### Task 7: Cas d'erreur

**Files:**
- Modify: `index.html` : messages et repli dans `useEngine`, `EmuFirmware.attach`, le chargement des paquets et « Ouvrir un .fwsc… »
- Create: `tests/test_errors.py`

**Interfaces:**
- Consumes: tâches 5 et 6. Messages exacts :
  - cœur absent : lignes émulées grisées, sous-titre « Cœur d'émulation indisponible » ;
  - paquet en ligne injoignable : « {nom} : paquet injoignable. » ;
  - échec au démarrage : « {nom} n'a pas démarré. » ;
  - arrêt du processeur émulé : « {nom} s'est arrêté. » et bouton « Redémarrer » ;
  - stockage indisponible : « Sauvegardes indisponibles dans ce navigateur. » ;
  - paquet personnel invalide : « Ce fichier n'est pas un paquet FM-1. ».

- [ ] **Step 1: Tests** (interceptions Playwright) : `runtime/fm1_web.wasm` en 404 → lignes émulées `aria-disabled="true"`, FM-1+VA démarre ; paquet en ligne en 503 → message, moteur précédent conservé ; paquet tronqué à 1 000 octets → « … n'a pas démarré. », moteur précédent conservé ; `indexedDB` supprimé avant chargement → Felucca démarre et le message de stockage s'affiche ; fichier texte ouvert via « Ouvrir un .fwsc… » → message, aucun changement ; message `frame` simulé avec `halted: 1` passé à `onWorklet` → message d'arrêt et bouton « Redémarrer », qui relance le même firmware.
- [ ] **Step 2:** FAIL. **Step 3:** Implémenter. **Step 4:** PASS. Commit « Cas d'erreur ».

### Task 8: Vérification de tous les firmwares

**Files:**
- Create: `tests/boot_all.py`, `docs/verification.md`
- Modify: `firmwares/catalogue.json` (champ `emulateur_fm1emu` des 20 « pas encore évalué »)

**Interfaces:**
- Consumes: `useEngine`, catalogue.
- Produces: `emulateur_fm1emu` ∈ {`fonctionne selon fm1-emu`, `vérifié`, `ne démarre pas`} ; le sélecteur affiche « non évalué » pour aucun, « ne démarre pas » en marqueur pour les échecs.

- [ ] **Step 1:** `boot_all.py` démarre chaque entrée locale non masquée ; réussite = démarrage en moins de 30 s, au moins 2 000 pixels non noirs après 4 s, et RMS > 0,0005 après PLAY puis touche 12 pendant 1 s. Écrit `docs/verification.md` (tableau id, résultat, durée).
- [ ] **Step 2:** Lancer ; mettre à jour le catalogue pour les 20 non évalués ; les 94 déclarés fonctionnels qui échouent sont listés dans le rapport pour l'utilisateur, sans changer leur marqueur.
- [ ] **Step 3:** `node --test tests/` → PASS. Commit « Vérification des firmwares ».

### Task 9: README, bannière, publication

**Files:**
- Create: `README.md` (français : présentation, utilisation, liste des firmwares par catégorie avec auteur, licence et lien vers dépôt et commit source, crédits fm1-emu et Hub, mention FM-1+VA non redistribué), `assets/banniere.png` (1280 × 640, panneau FM-1 sur fond sobre, titre « FM-1 »)
- Modify: artefact `https://claude.ai/artifact/6tvcwtxm9xiXhXXXY4akFg`

- [ ] **Step 1:** README et bannière ; push ; l'action réussit ; la page Pages répond et `test_boot_felucca` passe contre l'URL Pages.
- [ ] **Step 2:** Charger le skill `artifact-design`. Sonde : publier un artefact de test minimal qui appelle `WebAssembly.validate` sur un module vide et charge un AudioWorklet depuis un fichier joint ; noter le résultat, puis le supprimer.
- [ ] **Step 3:** Republier l'artefact FM-1+VA à la même adresse : `index.html`, `engine.js`, `runtime/*`, `firmwares/catalogue.json` et les `.fwsc` (plusieurs publications, 64 Mo maximum chacune). Si la sonde a échoué, la page affiche le message « Cœur d'émulation indisponible » prévu à la tâche 7.
- [ ] **Step 4:** Lecture de l'artefact publié (`action: read`) : la liste des fichiers contient 106 `.fwsc`. Commit « README et bannière ».
