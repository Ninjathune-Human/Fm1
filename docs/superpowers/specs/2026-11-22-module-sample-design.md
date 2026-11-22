# FM-1 : module sample et scratch

Date : 22 novembre 2026. Statut : en relecture.

## 1. Objet

Ajouter à l'environnement FM-1 un module, fait comme un FM-1, qui sert à capter un son, l'éditer, le déformer avec des commandes tactiles expressives, l'enregistrer, puis l'envoyer dans un firmware échantillonneur (Pigeon, zp12). Il se joue dans le Duo, à la place de FM1-B, à côté d'un FM-1 dont on choisit le firmware, sur la même horloge.

Point de départ : l'application de « beat board » de Zach Lansdale pour Board (pads, séquenceur, platine Loop / Motor / Cut, filtre XY, Roll, Throw Echo et Wash), vue en vidéo. Le module en garde l'esprit, mais il est tourné vers l'échantillon et le scratch, et le rythme vient du FM-1 voisin.

Décisions validées :

- **atelier de sample et platine** (choix « B ») : capture, éditeur avec découpe en tranches, 16 pads qui jouent les tranches, platine de scratch, zone XY, envoi vers Pigeon ou zp12 ; pas de séquenceur ni de patterns propres ;
- **le style du FM-1** : même boîtier, même taille, mêmes molettes, touches menthe à fente lumineuse, impression en points, animations lumineuses par LED ; un écran plus grand, au même style LCD que FM-1+VA ;
- **le strict nécessaire** : MASTER, SELECT, quatre touches (EDIT, SEND, PLAY/STOP, REC), l'écran tactile, la platine, 16 pads et une grande zone XY ; les fonctions retirées passent dans des gestes (§ 5.3) ;
- **le web seulement, pour l'instant** : le module se joue dans le navigateur (PC, Safari sur iPad et iPhone) ; l'app iPad (`ios/`) ne change pas tant que l'adhésion payante au programme Apple Developer n'est pas prise ;
- la maquette validée : canevas « Module sample et scratch pour FM-1, maquette » (https://claude.ai/artifact/URA71gJqNDLvNbRwKs5Dxy), planches « Le module », « Duo sur iPad » et « L'écran ».

Proposé, sans objection à ce jour : l'approche 1 du § 4 (une page à part, `sample.html`).

## 2. Objectifs, non-objectifs, anti-objectifs

**Objectifs**

- capter : le micro (PC, Safari sur iPad et iPhone), le son du FM-1 voisin, un fichier ; sur PC avec Chrome ou Edge, aussi le son d'un onglet ou du système ;
- éditer : découpe automatique en 16 tranches, début et fin au doigt, zoom, gain, hauteur ;
- déformer en jouant : scratch, filtre, écho, répétitions calées sur le tempo, lecture à l'envers, coupures ;
- garder : chaque sample dans le navigateur, compris dans la sauvegarde du bouton Mémoire ; export en .wav ;
- envoyer : dans Pigeon (une banque : la chanson et 16 pads) ou dans zp12 (16 sons sur C1 à D8), lancés dans FM1-A.

**Non-objectifs**

- un séquenceur, des patterns, des modes Bass ou Keys : le FM-1 voisin les fait ;
- capter sur iPad le son des autres apps (YouTube, Musique…) : Safari sur iPad n'offre pas cette capture, et l'app ne le pourrait qu'avec une extension de diffusion ReplayKit et un App Group, hors de portée d'un identifiant Apple gratuit et de Sideloadly. Le contournement documenté : un enregistrement d'écran d'iPadOS, importé comme fichier ;
- le module dans FM1-A, ou deux modules à la fois ;
- toute modification de l'app iPad (`ios/`), pour l'instant.

**Anti-objectifs** (ce qui ferait échouer le module même s'il marche)

- une régression sur les firmwares, le Solo ou le Duo ;
- une commande qui change de place d'une présentation à l'autre ;
- un module qui dérive du tempo du FM-1 voisin ;
- un envoi qui efface la banque de Pigeon sans prévenir ;
- une interface encombrée : toute commande ajoutée doit remplacer un geste qui ne suffit pas.

## 3. Critères de réussite

1. Dans le Duo, FM1-B peut devenir « Module sample » ; FM1-A garde tout firmware permis aujourd'hui. Revenir à un FM-1 dans FM1-B se fait d'un geste, au même endroit.
2. Tempo lié : un PLAY seul, sur l'un ou l'autre, lance et arrête les deux ; la boucle du module reste en phase avec l'horloge de la page (écart inférieur à un bloc audio de 128 échantillons sur 64 mesures, mesuré par test).
3. Capture : du micro sur PC (Chrome, Edge, Safari) et dans Safari sur iPad ; de FM1-A, le son de son firmware sans le micro ; d'un fichier (.wav, .aif, .mp3, .m4a, et la vidéo d'un enregistrement d'écran d'iPadOS si Safari en lit le son, à vérifier).
4. Les gestes du § 5.3 fonctionnent au doigt, à la souris et au stylet, sur PC, iPad et iPhone.
5. Envoi : Pigeon joue la banque reçue (chanson et pads) ; zp12 joue les 16 tranches sur C1 à D8 ; la ligne d'état de FM1-A dit ce qui a été chargé, comme le bouton Échantillons….
6. Les samples survivent au rechargement et passent dans une sauvegarde puis une restauration du bouton Mémoire ; l'export .wav s'ouvre dans un autre logiciel.
7. Les LED : la LED qui court sur les pads suit la tranche jouée, en phase avec la tête de lecture de l'écran ; la couronne de la platine suit la rotation du disque ; PLAY bat la mesure.
8. La suite de tests existante passe ; le module a ses propres tests (§ 9).

## 4. Approches

1. **Une page à part, `sample.html`, dans le cadre B du Duo** (retenue). Elle présente au Duo la même petite interface qu'un moteur de firmware (§ 6.2) : le tempo lié, le PLAY commun et les pastilles de battement fonctionnent sans changement. `index.html` n'est touché qu'à trois endroits (§ 6.1, § 6.4, § 6.5). Contrepartie : le dessin du boîtier (molettes, touches, plaques, écran, impression en points) est recopié de `buildPanel()`.
2. **Un mode de `index.html`** : le dessin est partagé, mais un fichier de 590 Ko grossit encore et chaque évolution du module touche la page de tous les firmwares.
3. **Un « firmware » du sélecteur**, comme FM-1+VA : intégration maximale, mais le panneau et l'abstraction des moteurs (touches, LED, molettes du FM-1) ne connaissent ni platine ni zone XY ; c'est le plus lourd et le plus risqué.

## 5. Le module

### 5.1 Le panneau

Unités du FM-1 : 1640 × 990, coloris Menthe ; les matières, les ombres et l'éclairage sont ceux de `buildPanel()`. Disposition validée :

| Élément | Place (unités du FM-1) |
|---|---|
| MASTER, SELECT | molettes à (135, 147) et (308, 147), étiquettes à y 69 : la place du FM-1 |
| Touches | plaque (95, 262, 252 × 228) ; EDIT (156, 319), SEND (286, 319), PLAY/STOP (156, 425), REC (286, 425), 100 × 80 |
| Écran | cadre (422, 70, 616 × 390), verre noir, image LCD de 440 × 240 pixels à 1,25 unité par pixel |
| Platine | centre (1336, 272) : puits de rayon 206, couronne de 32 LED à 192, disque de 174, macaron menthe |
| Pads | plaque (62, 560, 810 × 365) ; deux rangées de huit touches-pilules du FM-1 à x = 123 + 93 i, y 659 et 825 ; fente de 43, numéro 1 à 16 |
| Zone XY | verre (902, 560, 676 × 365), fond du thème de l'écran, quadrillage, légendes FILTER, RES, LOW-PASS, HIGH-PASS, 2 FINGERS ECHO |

Les coloris du FM-1 s'appliquent au module comme au FM-1 (les six pastilles), sur les mêmes couleurs dérivées.

Sous le module, une ligne comme celle du FM-1, à la même place : la pastille **Firmware** (« Module sample »), qui rouvre la liste des firmwares de FM1-B (§ 6.1), et l'interrupteur marche / arrêt. Sur l'écran, avant l'allumage, le bouton **Allumer** du FM-1 : le son ne démarre qu'après un geste sur iPad.

### 5.2 L'écran

Style de FM-1+VA : thème Green (fond #0a1210, texte #eef7f3, atténué #84a299, accent #a3d6c7), Barlow Semi Condensed, en-tête à quatre colonnes (nom, barre, valeur ; la colonne choisie en blanc), ligne d'état, nom du sample en bas à gauche, pile en bas à droite. Textes de l'écran en anglais, comme FM-1+VA. Trois pages :

- **Capture** : colonnes SOURCE, INPUT, THRESH, LENGTH ; puces MIC, FM-1, FILE (et TAB ou SYSTEM sur PC quand le navigateur les offre) ; la forme d'onde qui s'écrit, la tête rouge, le vumètre en segments avec le seuil ; « REC 0:03.4 ».
- **Édition** : colonnes START, LENGTH, PITCH, GAIN de la tranche choisie ; la forme d'onde découpée en 16 tranches, la tranche choisie en clair, ses poignées de début et de fin, la tête de lecture ; la barre de vue d'ensemble du zoom ; le tempo en haut à droite.
- **Envoi** : colonnes TO, SONG, PADS, SIZE ; la chanson et les 16 pads en vignettes ; une ligne qui dit ce que l'envoi va faire (« Replaces Pigeon's whole bank »).

L'écran est **tactile** : toucher une colonne la choisit, SELECT règle sa valeur, un glissé vertical sur la valeur aussi ; glisser une poignée déplace le début ou la fin ; pincer zoome ; toucher une tranche la choisit ; toucher une puce choisit la source ou la cible.

### 5.3 Commandes et gestes

| Commande | Rôle |
|---|---|
| MASTER | volume du module |
| SELECT | sans colonne choisie : passe d'un sample à l'autre (S01, S02…) ; avec : règle la colonne |
| REC | page Capture et armement : l'enregistrement part au premier son au-dessus du seuil (ou tout de suite, seuil à OFF) ; REC encore l'arrête. Avec le tempo lié, il part sur un temps et dure LENGTH mesures. Fini, le sample est découpé et la page Édition s'ouvre |
| REC + pad tenu | capte sur ce pad seul, pour faire un kit de sons venus de sources différentes |
| EDIT | page Édition |
| SEND | page Envoi ; SEND encore envoie, après confirmation quand l'envoi remplace la banque de Pigeon |
| PLAY/STOP | lance et arrête la boucle du sample en cours ; tempo lié : lance et arrête aussi FM1-A |
| Pad | joue sa tranche ; tenu : répète la tranche en doubles croches au tempo (roll) |
| Platine, un doigt | scratch : la position du disque mène la lecture (un tour = 1,8 s de son, comme un 33 tours) |
| Platine, doigt posé immobile | arrêt, la main sur le disque |
| Platine, doigt levé | le moteur relance le disque ; la lecture revient en phase avec l'horloge (lecture « slip » : la boucle a continué dessous) |
| Platine, lancer en arrière | lecture à l'envers tant que le disque tourne à l'envers |
| Platine, deuxième doigt | coupe le son tant qu'il reste posé (le cut du crossfader) |
| Zone XY, un doigt | filtre : X du passe-bas au passe-haut, Y la résonance |
| Zone XY, deux doigts | écho au tempo : l'écart des doigts en règle la quantité, leur hauteur le retour |
| Zone XY, doigts levés | retour à zéro, en douceur |
| Stylet | sa pression règle l'intensité de l'effet touché |

### 5.4 Les lumières

Comme sur le FM-1 : une LED faible éclaire d'abord le centre du diffuseur, puis la fente, avec un halo à proportion (`--i`).

- pads : la LED de la tranche jouée par la boucle, avec une traînée qui s'éteint ; un pad touché s'allume plein ; la tranche choisie reste faiblement allumée ;
- couronne : la LED en face du repère du disque et sa traînée, qui suivent la rotation réelle, scratch compris ;
- PLAY : vert, battement au temps ; REC : rouge, clignote armé, fixe en enregistrement ;
- zone XY : le point touché brille, avec sa croix ; deux points pour l'écho.

### 5.5 Le son

Un AudioWorklet propre au module, dans sa page, comme celui de FM-1+VA. Il lit le sample en cours à vitesse variable (scratch, moteur, lecture à l'envers), avec une interpolation propre aux vitesses lentes ; les tranches en une fois (pads) et en répétition (roll) ; un filtre à variable d'état passe-bas / passe-haut avec résonance ; un écho synchronisé ; le volume MASTER ; une analyse de sortie (`AnalyserNode`) comme les autres moteurs.

## 6. Liaisons

### 6.1 Le cadre B du Duo

- Dans la liste des firmwares de FM1-B, en tête, une section « Modules » avec une entrée **Module sample** ; la choisir charge `sample.html?fm1=b` dans le cadre B. Le choix est gardé (`fm1.duo.b`), et le Duo rouvre le module au chargement.
- Dans le module, la pastille Firmware (même place que sur le FM-1) recharge `?fm1=b&choisir`, qui ouvre la liste.
- La mémoire de FM1-B (« fm1b. ») n'est pas touchée par ce va-et-vient.
- La page du module a, comme celle du FM-1, une ligne `.deck` avec ses pastilles de coloris (`.skins`) : la page du Duo y place les onglets FM1-A | FM1-B quand un seul cadre est affiché.
- L'iframe B reçoit `allow="midi; autoplay; microphone; display-capture"` (l'iframe A aussi, sans conséquence).

### 6.2 L'horloge

Le module définit `window.__engine = () => moteur`, avec ce que la page du Duo lit d'un moteur : `on`, `name`, `entry` (`{ id: "sample", nom: "Module sample", natif_horloge: true, demarre: true }`), `midiIn(bytes)`, `playLight()` (« green » quand la boucle joue, comme `playingColour`), `greenAt`. Il reçoit l'horloge du tempo lié (0xF8, 0xFA, 0xFC) par `midiIn`, en déduit tempo et phase, et cale dessus la boucle, les rolls, l'écho et le départ de REC. Un PLAY seul appelle `parent.__duoPlay()`, comme le fait un FM-1. Sans tempo lié, ou ouvert seul, le module suit son propre tempo, réglable en touchant le tempo de la page Édition.

La boucle dure un nombre entier de mesures. Un sample capté avec le tempo lié en a déjà la longueur (LENGTH). Un sample venu d'un fichier, ou capté sans tempo, prend le nombre de mesures le plus proche (1, 2, 4 ou 8) ; sa vitesse de lecture s'ajuste pour tenir dedans, comme le réglage de vitesse d'une platine (la hauteur suit), et PITCH s'ajoute à cet ajustement.

### 6.3 Le son de FM1-A

Chaque moteur a un `AnalyserNode` (`an`) relié à la sortie, dans le contexte audio de sa page (`window.__ac`). Pour la source FM-1, le module place dans ce contexte un petit AudioWorklet de prise, relié à `an`, qui envoie ses blocs au module par un `MessageChannel` ; le module les écrit dans son tampon de capture (rééchantillonnés si les deux contextes n'ont pas la même fréquence). La prise est retirée à la fin de la capture. FM1-A éteint : la puce FM-1 est grisée.

### 6.4 L'envoi

Le module fabrique des fichiers .wav (`File`) et appelle la fonction de page de FM1-A qui sert au bouton Échantillons… ; `index.html` l'expose pour cela (`window.__takeSamples = takeSamples`), pour que la ligne d'état de FM1-A dise ce qui a été chargé. La réponse s'affiche aussi sur l'écran du module.

- **Pigeon** : la chanson est le sample en cours (Pigeon fait ses propres découpes, jusqu'à 32), les pads ses 16 tranches (ou les sons captés pad par pad). Pigeon remplace toute sa banque : l'écran le dit, SEND demande confirmation. Au-delà de 500 Kio, la banque passe en mode illimité, comme aujourd'hui.
- **zp12** : les 16 tranches sur C1 à D8, dans les places libres de sa mémoire (12 bits, 26 kHz, comme son éditeur).
- **FILE** : un .wav du sample en cours, par le téléchargement du navigateur (dans Fichiers sur iPad).
- Les cibles proposées sont celles de FM1-A : PIGEON ou ZP12 seulement si son firmware est l'un des deux, FILE toujours, ERASE pour supprimer le sample en cours (avec confirmation).

### 6.5 Le micro

- `getUserMedia` sans traitement de la voix (`echoCancellation`, `noiseSuppression`, `autoGainControl` à `false`), pour un son brut.
- Sur PC, la source TAB ou SYSTEM passe par `getDisplayMedia({ audio: true })`, seulement là où le navigateur l'offre.
- Micro refusé ou absent : la puce MIC est grisée et l'écran dit pourquoi ; les autres sources restent. C'est aussi le cas dans l'app iPad, non modifiée pour l'instant, si elle est reconstruite avec le site.

## 7. Mémoire

- Les samples et leurs réglages (tranches, début, fin, hauteur, gain, sons captés par pad) dans une base IndexedDB `fm1-samples`.
- Sauvegarde : `backup.js` les ajoute dans un champ à part, comme les copies (`COPIES`), puisque le validateur du fork de Jake Pawlik refuse toute base inconnue ; une sauvegarde sans ce champ laisse les samples tels quels.
- L'interrupteur marche / arrêt du module n'efface rien des samples (seule ERASE le fait).

## 8. Contraintes

- JavaScript sans dépendance, une page `sample.html` autonome (son worklet inclus, comme `index.html`) ; polices et licences reprises de `index.html` (Barlow Semi Condensed, M PLUS Rounded 1c, OFL).
- Licence GPL-3.0 ; le dessin vient de `buildPanel()`, lui-même adapté de DUB-1 (sbegueria/fm1-dub) : le crédit est repris dans la page.
- Publication : `pages.yml` copie `sample.html` avec `index.html` (ligne `cp index.html engine.js backup.js _site/`) ; le tag `deploye` existant suit. L'app iPad n'est pas modifiée (§ 2).
- PC, iPad, iPhone : souris, tactile, stylet ; molettes avec la même accélération et le même retour haptique (`Encoder`, `Haptics`).
- Interface de la page en FR / EN comme le site ; écran du module en anglais.
- Les modifications de `index.html` se limitent au § 6.1 (liste de FM1-B, iframes, choix gardé), au § 6.4 (`__takeSamples`) et à rien d'autre.

## 9. Tests

- `tests/test_sample.py`, avec le serveur et Playwright de la suite : le Duo avec le module en FM1-B ; l'horloge (phase de la boucle sur 64 mesures) ; une capture depuis FM1-A sur FM-1+VA (un son connu) ; un fichier .wav importé ; l'envoi vers Pigeon et zp12 quand leurs paquets natifs sont construits (sinon ignorés, comme les autres tests natifs) ; la sauvegarde et la restauration avec des samples.
- Le reste de la suite passe tel quel.

## 10. Laissé au constructeur

- Les constantes du son : courbe du filtre, temps et retour de l'écho, inertie du moteur de la platine, seuil par défaut, longueur maximale d'une capture (proposé : 4 mesures ou 16 s).
- La forme interne du sample (mono ou stéréo, fréquence) et de la base `fm1-samples`.
- Les raccourcis clavier sur PC : PLAY et REC comme sur le FM-1, les pads sur deux rangées de lettres ; les notes MIDI d'un clavier branché sur les pads (36 à 51, par exemple).
- L'organisation du code dans `sample.html`.

## 11. Choix faits sans vous, à vérifier

- les pads jouent les 16 tranches du sample en cours ; REC + pad tenu capte un son sur ce pad seul ;
- après un scratch, la lecture revient en phase avec l'horloge (« slip ») plutôt que de repartir d'où le disque s'est arrêté ;
- le roll en doubles croches, fixe ;
- un sample venu d'un fichier se cale sur le tempo en changeant de vitesse, comme une platine (sa hauteur change), plutôt que d'être étiré sans changer de hauteur ;
- confirmation avant de remplacer la banque de Pigeon ;
- le module ouvert seul (sans Duo) fonctionne, avec son propre tempo ;
- ERASE dans la page Envoi pour supprimer un sample.
