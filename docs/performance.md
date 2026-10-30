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

66 firmwares publient une version navigateur compilée depuis leur code C (`web/emu`, Emscripten). Mesure sur la même machine d'intégration continue :

| Felucca 1.6.1 | Coût |
|---|---|
| natif, morceau lourd (FM6, PHYS, GRAIN, batterie) | 1,1 % du temps réel |
| émulé, accord simple | 31 % du temps réel (3,21×) |

Le natif coûte environ 30 fois moins pour un travail plus lourd.

L'action GitHub compile chacun des 66 depuis ses sources, au commit noté dans `tools/natif.json` (une tâche par firmware, `tools/natif_build.sh` ; les champs facultatifs `zig`, `avant` et `wasm` y règlent la chaîne Zig, une commande préalable et le `.wasm` retenu). Sont retenus ceux dont le worklet parle un des six protocoles connus : familles Felucca, X0X (dont MONK-1, qui lit une touche à la fois), ChoralRoot, sim, MEL et mono2k (écran d'un bit par pixel). hera et ravel, dont la page fait tourner le firmware sans worklet, passent par nos worklets (`tools/worklets/`), qui pilotent leur `.wasm` comme leur page et parlent au panneau en protocole Felucca. frodhes et chipbox, écrits pour une page Emscripten (leur boucle rend la main par `emscripten_sleep`), sont recompilés depuis leurs sources sans Emscripten (`tools/worklets/asyncify.sh` : Zig, un `emscripten.h` de remplacement, la passe Asyncify de Binaryen) ; leur boucle tourne en coroutine dans notre worklet (`coroutine.js`). DUB-1, hyp1 et perf1 passent par leur émulateur complet (`web/emu`, et non l'appli compagnon `web/app`) : DUB-1 compilé avec Zig, hyp1 et perf1 par leur propre `build_clang.sh`. Hortator passe par son simulateur, compilé par l'emcc de l'action avec une entrée MIDI à nous (`tools/worklets/hortator_sim.c`, `hortator.js`) ; zp12 par son `sim/build.sh`, sa prise TRS simulée (`zp12_avant.sh`). Berlinan, CTL-1, Del Rio et LOOM-8, bâtis sur fm1-base, par `./build.sh --web` ; 386DX par son `tools/build_web.py`, eSpeak NG cloné avant. Soit 66 firmwares natifs. La raison de chaque écart s'affiche en annotation de l'action. La page lit `natif/manifest.json` et prend le natif quand il existe ; l'action vérifie que chacun démarre, dessine son écran et répond au panneau.

Les autres restent émulés. Ceux qui pourraient passer en natif, à faire plus tard, du plus simple au plus lourd :

- Evander's Music Box, FM1-GM, FM1 Quest, FM-1 SID, FOMAJAM, Ketch, MNM-1, winampFM, No Man Sky FM et FIZZ : une version navigateur dans un protocole que le panneau ne connaît pas ; un worklet à nous pour chacun, comme Hortator (winampFM et No Man Sky FM, d'où vient le protocole sim, d'abord) ;
- Cut-A-Dor : son `.wasm` (`host/wasm.c`) n'est que le moteur ; son test `host/display.c` montre l'interface complète hors de l'appareil par quelques fonctions `plat_*`, à écrire pour le navigateur, avec un worklet en protocole Felucca ;
- Bytemania : un simulateur hôte en ligne de commande (`tests/host.c`, sur Dinghy) ; à remplacer par une adaptation navigateur dérivée de celle de frodhes, en coroutine Asyncify ;
- Mycelium : ses sources dans un zip, un dérivé de SLOOP et de Felucca (`tests/hostsim.c`) ; y greffer le `felucca_web.c` de Felucca, selon l'écart des versions ;
- amb : dans sa version 1.3, celle du catalogue, la version navigateur est l'appli compagnon (le moteur seul) ; son émulateur complet n'existe que dans une version plus récente du dépôt, avec son paquet à mettre à jour ;
- SIDOU : un cœur C (un 6502 et un SID émulés) testé depuis Rust, sans version navigateur ; toute une couche plateforme à écrire.

vector37 reste émulé : sa version navigateur simule un SMK-37 Pro, pas le FM-1.

Retouches faites aux worklets, et seulement celles-là : nom de processeur propre à chaque firmware, écran à 60 images par seconde, et un `TextDecoder` de secours (absent du fil audio de Chrome, il bloquait FUMI et ZEN-1).
