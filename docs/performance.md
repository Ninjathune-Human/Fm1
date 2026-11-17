# Performances : émulation et firmwares natifs

Mesures du 28 octobre 2026. Les rapports entre chiffres comptent plus que les chiffres eux-mêmes : la machine de test a deux cœurs lents.

## Le cœur émulé (fm1-emu, 100 MHz, WebAssembly)

| Firmware | Vitesse (temps émulé / temps de calcul) | Pire quantum (budget 2,9 ms) |
|---|---|---|
| OberVave | 1,86× | 6 ms |
| Felucca | 1,5 à 2× | 11 ms |
| X0X | 0,7 à 1,1× | 60 ms |
| sloopDX | 0,8 à 1× | 50 ms |
| FM-106 | 0,7× | 38 ms |
| Clipper | 0,45× | 51 ms |
| Melodee | 0,25× | 78 ms |

- En dessous de 1×, le son coupe. Les pics viennent de la compilation à la volée du code émulé, faite dans le fil audio.
- Avance du son : 256 échantillons au lieu de 1 024 double les quanta trop longs (Felucca 33 → 64, X0X 463 → 508). Elle reste à 1 024.
- La dernière version de fm1-emu (eb0d897) ne change rien de mesurable dans le navigateur : sa passe de vitesse vise le JIT natif des Mac.
- FM-1+VA en veille prend 0,5 % du fil audio : il n'y est pour rien.
- À 100 MHz, chaque firmware mesuré produit tout son son.

Pistes restantes dans le cœur émulé (code Rust de fm1-emu), par appels d'aide comptés :

- calcul flottant (`FOp`) : 5 M d'appels par seconde sur Melodee, 2 M sur X0X, à traduire en instructions WebAssembly ;
- lecture du compteur TIMER4, interrogé en boucle : 19 % du temps de Felucca selon l'auteur ;
- sonde d'inactivité du second cœur : 8 à 11 % ;
- `IfBlk`, `Div`, `Raw22`, `LdPre`, `LdPair` traduits directement ;
- compilation des blocs hors du fil audio.

Gain estimé : 20 à 40 %, pas un ordre de grandeur.

## Les firmwares natifs

86 firmwares publient une version navigateur compilée depuis leur code C (`web/emu`, Emscripten). Mesure sur la même machine d'intégration continue :

| Felucca 1.6.1 | Coût |
|---|---|
| natif, morceau lourd (FM6, PHYS, GRAIN, batterie) | 1,1 % du temps réel |
| émulé, accord simple | 31 % du temps réel (3,21×) |

Le natif coûte environ 30 fois moins pour un travail plus lourd.

L'action GitHub compile chacun des 86 depuis ses sources, au commit noté dans `tools/natif.json` (une tâche par firmware, `tools/natif_build.sh` ; les champs facultatifs `zig`, `avant` et `wasm` y règlent la chaîne Zig, une commande préalable et le `.wasm` retenu). Sont retenus ceux dont le worklet parle un des six protocoles connus : familles Felucca, X0X (dont MONK-1, qui lit une touche à la fois), ChoralRoot, sim, MEL et mono2k (écran d'un bit par pixel). hera et ravel, dont la page fait tourner le firmware sans worklet, passent par nos worklets (`tools/worklets/`), qui pilotent leur `.wasm` comme leur page et parlent au panneau en protocole Felucca. frodhes et chipbox, écrits pour une page Emscripten (leur boucle rend la main par `emscripten_sleep`), sont recompilés depuis leurs sources sans Emscripten (`tools/worklets/asyncify.sh` : Zig, un `emscripten.h` de remplacement, la passe Asyncify de Binaryen) ; leur boucle tourne en coroutine dans notre worklet (`coroutine.js`). DUB-1, hyp1, perf1 et DARK-1 passent par leur émulateur complet (`web/emu`, et non l'appli compagnon `web/app`) : DUB-1 compilé avec Zig, hyp1, perf1 et DARK-1 (une modification de PERF-1) par leur propre `build_clang.sh`. Hortator passe par son simulateur, compilé par l'emcc de l'action avec une entrée MIDI à nous (`tools/worklets/hortator_sim.c`, `hortator.js`) ; zp12 par son `sim/build.sh`, sa prise TRS simulée (`zp12_avant.sh`). Melodee, qui n'a pas de version navigateur, par son test d'interface (`tests/ui_test.c` : le son de `hostsim.c` et l'interface de l'appareil sur des bouchons), compilé par l'emcc de l'action et mené comme sa boucle principale (`tools/worklets/melodee_sim.c`, `melodee.js`). Berlinan, CTL-1, Del Rio et LOOM-8, bâtis sur fm1-base, par `./build.sh --web` ; FRASIL de même ; J6, dont la copie de fm1-base n'a pas la version navigateur, avec le `web/` de fm1-base au commit le plus proche de cette copie (934e40d) ; Mutable Dreams, dont les sources sont dans un zip du dépôt, par son `tools/build_local.py` et le SDK WASI 34 qu'il demande ; 386DX par son `tools/build_web.py`, eSpeak NG cloné avant. AMB-1, bâti sur fm1-base, par `./build.sh --web` (son `web/app` n'est que l'appli compagnon, le moteur seul). VECTOR37, dont la version navigateur simule un SMK-37 Pro, par le FM-1 simulé de ses tests d'hôte (`tests/panel.h` sans `BOARD_SMK37`, la version FM-1 de son panneau), compilé par l'emcc de l'action avec notre conduite (`tools/worklets/vector37_sim.c`, `vector37.js`). Soit 86 firmwares natifs. La raison de chaque écart s'affiche en annotation de l'action. La page lit `natif/manifest.json` et prend le natif quand il existe ; l'action vérifie que chacun démarre, dessine son écran et répond au panneau.

Les autres restent émulés. Ceux qui pourraient passer en natif, à faire plus tard, du plus simple au plus lourd :

- Evander's Music Box, FM1-GM, FM1 Quest, FM-1 SID, FOMAJAM, Ketch, MNM-1, winampFM, No Man Sky FM et FIZZ : une version navigateur dans un protocole que le panneau ne connaît pas ; un worklet à nous pour chacun, comme Hortator (winampFM et No Man Sky FM, d'où vient le protocole sim, d'abord) ;
- MIDIMON : il compile (son tampon `sx_in`, qui recouvrait celui de la version navigateur de fm1-base, renommé), mais le worklet de sa version de fm1-base ne lui passe pas le MIDI de la page : un moniteur MIDI qui ne reçoit rien ; un worklet à nous, qui appelle son `web_midi_in` ;
- Cut-A-Dor : son `.wasm` (`host/wasm.c`) n'est que le moteur ; son test `host/display.c` montre l'interface complète hors de l'appareil par quelques fonctions `plat_*`, à écrire pour le navigateur, avec un worklet en protocole Felucca ;
- Bytemania : un simulateur hôte en ligne de commande (`tests/host.c`, sur Dinghy) ; à remplacer par une adaptation navigateur dérivée de celle de frodhes, en coroutine Asyncify ;
- Mycelium : ses sources dans un zip, un dérivé de SLOOP et de Felucca (`tests/hostsim.c`) ; y greffer le `felucca_web.c` de Felucca, selon l'écart des versions ;
- SIDOU : un cœur C (un 6502 et un SID émulés) testé depuis Rust, sans version navigateur ; toute une couche plateforme à écrire.

Retouches faites aux worklets, et seulement celles-là : nom de processeur propre à chaque firmware, écran à 60 images par seconde, et un `TextDecoder` de secours (absent du fil audio de Chrome, il bloquait FUMI et ZEN-1).

## Piste testée le 16 novembre 2026 : multiplications-accumulations en WebAssembly

Les ops flottantes 7 et 8 (d = d ± a × b) passent par l'exécuteur dans le cœur au commit 60645a5 ; la branche `essai-perf` (`tools/fm1emu_perf.py`, banc `perf.yml`) les calcule en instructions f32 du bloc compilé.

- Exactitude : le son de dix firmwares (Melodee, Clipper, SLOOPDX, DARK-1, FM1SID, zp12, NACHTFAHRT, Mutable, Scintilla, FMDj), 8 s à 100 MHz, est identique octet pour octet à celui du cœur publié ; l'auto-test `fop_selftest` ne signale que les écarts de charge utile NaN déjà présents dans le cœur publié (ops 0 et 2, interpréteur contre exécuteur), les ops 7 et 8 se comportent comme eux.
- Vitesse : aucun gain mesurable (Melodee 1,59× avant, 1,57× après ; DARK-1 1,27× et 1,28×). Aucune op flottante n'apparaît parmi les appels d'aide comptés : la piste ne vaut rien sur ce cœur, elle n'est pas publiée.
- Où va le temps (profil, 6 s émulées à 100 MHz, 500 millions d'instructions) : les appels d'aide comptés sont rares (au plus 0,7 million) ; les lectures du bus sont de 4 à 20 millions, dont 6,8 à 9,6 millions du seul compteur TIMER4 (`0x10804`) sur Melodee, DARK-1 et Clipper, et 2,5 à 3 millions de `0x50000` (GPIO) sur tous. Chaque lecture traverse l'appel d'aide, le bus de la machine, le décodage des régions, la lecture du périphérique (une division 64 bits, le dépistage des boucles d'attente et leur saut) : c'est la piste qui reste.
