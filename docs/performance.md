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

61 firmwares publient une version navigateur compilée depuis leur code C (`web/emu`, Emscripten). Mesure sur la même machine d'intégration continue :

| Felucca 1.6.1 | Coût |
|---|---|
| natif, morceau lourd (FM6, PHYS, GRAIN, batterie) | 1,1 % du temps réel |
| émulé, accord simple | 31 % du temps réel (3,21×) |

Le natif coûte environ 30 fois moins pour un travail plus lourd.

L'action GitHub compile chacun des 61 depuis ses sources, au commit noté dans `tools/natif.json` (une tâche par firmware, `tools/natif_build.sh` ; les champs facultatifs `zig`, `avant` et `wasm` y règlent la chaîne Zig, une commande préalable et le `.wasm` retenu). Sont retenus ceux dont le worklet parle un des six protocoles connus : familles Felucca, X0X (dont MONK-1, qui lit une touche à la fois), ChoralRoot, sim, MEL et mono2k (écran d'un bit par pixel). hera et ravel, dont la page fait tourner le firmware sans worklet, passent par nos worklets (`tools/worklets/`), qui pilotent leur `.wasm` comme leur page et parlent au panneau en protocole Felucca. Soit 54 firmwares natifs. La raison de chaque écart s'affiche en annotation de l'action. La page lit `natif/manifest.json` et prend le natif quand il existe ; l'action vérifie que chacun démarre, dessine son écran et répond au panneau.

Les 7 autres restent émulés :

- frodhes, chipbox : leur version navigateur tourne sur la page avec Emscripten et sa boucle (Asyncify), sans worklet ;
- amb, dub, hyp1, perf1 : la version navigateur est une appli compagnon (le moteur seul, sans écran ni touches FM-1) ;
- vector37 : la version navigateur simule un SMK-37 Pro, pas le FM-1.

Retouches faites aux worklets, et seulement celles-là : nom de processeur propre à chaque firmware, écran à 60 images par seconde, et un `TextDecoder` de secours (absent du fil audio de Chrome, il bloquait FUMI et ZEN-1).
