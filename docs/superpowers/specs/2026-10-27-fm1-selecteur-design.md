# FM-1 : sélecteur de firmwares sur le panneau FM-1+VA

Date : 27 octobre 2026. Statut : en relecture.

## 1. Objet

Le panneau FM-1 existant (artefact Claude « FM-1+VA », réimplémentation du firmware de Baud Girl d'après son manuel) doit pouvoir faire tourner, en plus de cette réimplémentation, les firmwares open source du M-VAVE FM-1. Un sélecteur permet de passer de l'un à l'autre.

Décisions validées :

- la réimplémentation FM-1+VA reste disponible, comme premier firmware du sélecteur ;
- les vrais firmwares tournent sur le cœur d'émulation fm1-emu (Joakim Eriksson, MIT), qui émule la puce JieLi AC791N et exécute les paquets `.fwsc` sans modification ;
- le cœur est compilé en WebAssembly par une action GitHub dans ce dépôt, à partir d'un commit figé de fm1-emu ;
- le site est publié sur GitHub Pages ; l'artefact Claude est mis à jour à la même adresse.

## 2. Critères de réussite

1. Sur GitHub Pages, les 94 firmwares que fm1-emu déclare fonctionnels démarrent depuis le sélecteur : l'écran affiche l'image du firmware, le clavier produit du son. Les 20 firmwares « non évalués » sont essayés de la même façon, et leur marqueur est remplacé par le résultat mesuré.
2. Le panneau, les coloris, les molettes (accélération, retour haptique) et l'éclairage des fentes restent ceux de l'artefact actuel.
3. Changer de firmware prend un geste et ne perd aucune sauvegarde : chaque firmware retrouve ses presets et patterns.
4. La réimplémentation FM-1+VA fonctionne comme aujourd'hui.
5. PC, iPad et iPhone : souris, tactile et stylet.

## 3. Architecture

```
index.html (panneau, sélecteur, couche de liaison)
 ├─ moteur « FM-1+VA »      : AudioWorklet existant, inchangé
 └─ moteur « puce émulée »  : runtime/worklet.js  (fm1-emu, AudioWorklet)
                              runtime/fm1_web.wasm (compilé par l'action)
                              runtime/persistence.js (sauvegardes)
                              firmwares/<id>.fwsc + catalogue.json
```

Un seul moteur est actif à la fois. Changer de moteur arrête l'AudioWorkletNode courant et en crée un nouveau.

### 3.1 Protocole avec le cœur émulé

Repris de `web/main.js` de fm1-emu (MIT), adapté sans l'interface de fm1-emu.

Page vers worklet :

| Message | Rôle |
|---|---|
| `boot { seq, wasm, package, mhz }` | démarre un paquet `.fwsc` |
| `key { id, down }` | touche 0 à 40 |
| `enc { enc, clicks }` | encodeur 0 à 6, crans signés |
| `pot { value }`, `midi { bytes }` | potentiomètre, MIDI entrant |
| `snapshot`, `resume` | sauvegarde de la flash |

Worklet vers page : `booted`, `frame { lcd, leds }`, `flash-changed`, `snapshot`, `error`.

### 3.2 Couche de liaison

| Panneau | Firmware |
|---|---|
| Boutons OCT-, OCT+, FX, SCL, ENV, LFO, EDIT, GLO, HOME, SAVE, ARP, SEQ, PLAY, REC | identifiants 0 à 13 |
| 27 touches de clavier, de F3 à G5 | identifiants 14 à 40 |
| Molette SELECT, ALGO, K1 à K4, PRESET | encodeurs 0, 1, 2 à 5, 6 |
| Écran | `lcd` 240 × 240 en RGB565, converti en RGBA, affiché à l'échelle 3 dans le canvas 720 × 720, sans lissage |
| Fentes éclairées | `leds` : 41 valeurs de 0 à 1, une par touche |

L'accélération des molettes reste calculée par le panneau ; seul le nombre de crans obtenu est transmis.

### 3.3 Sauvegardes

`persistence.js` de fm1-emu enregistre, dans IndexedDB, les secteurs de flash modifiés par chaque firmware, indexés par l'empreinte du paquet. Au démarrage d'un firmware, ses secteurs sont restaurés. « Réglages d'usine » efface l'enregistrement du seul firmware actif. Le firmware utilisé en dernier est mémorisé (localStorage) et redémarre à l'ouverture.

## 4. Sélecteur

- Un contrôle sous le panneau, à côté des coloris : nom du firmware actif et une encoche qui pivote quand la liste est dépliée.
- La liste : feuille montant du bas sur iPhone, panneau sous le contrôle sur PC et iPad.
- En tête, un champ de recherche sur le nom, l'auteur et la description, construit selon la convention « champ de recherche intelligent » de l'utilisateur.
- Sections repliables, chacune avec son encoche : FM-1+VA, Officiel V15, Groovebox, Synthé, Accords, Boîte à rythmes, Tracker, Autre.
- Chaque ligne : nom, auteur, une ligne de description, et les marqueurs « bêta », « en ligne », « non évalué » quand ils s'appliquent.
- Bubba Machine est masqué (il ne démarre pas dans fm1-emu).
- En pied de liste : « Ouvrir un .fwsc… » pour un paquet personnel, qui n'est ni enregistré dans le dépôt ni envoyé ailleurs.
- Toucher une ligne démarre le firmware, sans confirmation. La ligne d'état affiche « Démarrage de… », puis le nom du firmware.
- Commandes sous le panneau selon le moteur : avec FM-1+VA, « Charger un patch DX7 » et « Réglages d'usine » comme aujourd'hui ; avec un firmware émulé, « Réglages d'usine » seul.

## 5. Dépôt et publication

```
index.html                     page complète
firmwares/<id>.fwsc            106 paquets vérifiés (SHA-256 du catalogue du Hub)
firmwares/catalogue.json       données du sélecteur
firmwares/licences/<id>/       licences de chaque firmware
assets/banniere.png            bannière du README
README.md                      présentation, crédits, sources GPL
.github/workflows/pages.yml    compilation et publication
docs/superpowers/specs/        cette spécification
```

L'action `pages.yml`, à chaque mise à jour de `main` :

1. récupère fm1-emu au commit figé `1c8661daa1bbfddbb7d32d927bbaf831343b7d3b` ;
2. installe la cible `wasm32-unknown-unknown` et compile `fm1-web` avec les réglages de `web/build.sh` de fm1-emu ;
3. copie `fm1_web.wasm`, `worklet.js` et `persistence.js` dans `runtime/` du site ;
4. publie le site sur GitHub Pages ;
5. joint `runtime/` à une version GitHub du dépôt, pour l'artefact Claude.

Changer de version de fm1-emu revient à modifier le commit figé.

### 5.1 Artefact Claude

L'artefact FM-1+VA est republié à la même adresse avec `runtime/` et les paquets en fichiers joints (environ 63 Mo, publiés en deux fois). Les 9 firmwares « en ligne » y sont indisponibles : l'artefact ne peut pas joindre le Hub. Si l'environnement des artefacts refuse le WebAssembly, les firmwares émulés y sont désactivés avec un message, et seule la version GitHub Pages les fait tourner.

## 6. Erreurs

| Cas | Comportement |
|---|---|
| `fm1_web.wasm` absent ou refusé | les firmwares émulés sont grisés, avec la raison ; FM-1+VA fonctionne |
| Paquet en ligne injoignable | message dans la ligne d'état, le firmware précédent reste actif |
| Erreur au démarrage (`error` du worklet) | « Ce firmware n'a pas démarré », retour au firmware précédent |
| Firmware arrêté (`halted`) | message dans la ligne d'état, bouton de redémarrage |
| Audio suspendu (iOS) | le démarrage reste lié au bouton « Allumer » existant |
| Paquet personnel invalide | message, aucun changement |

## 7. Vérification

- Tests Node de la couche de liaison : table des touches et encodeurs, conversion RGB565 vers RGBA, lecture du catalogue.
- Après la première exécution de l'action : navigateur sans interface, démarrage de chaque paquet local ; un paquet passe s'il produit une image non vide et un signal audio non nul dans un délai fixé. Le rapport liste les échecs.
- Contrôle visuel du sélecteur sur trois largeurs : iPhone, iPad, PC.
- Non-régression de FM-1+VA : même vérification que lors de sa réalisation (accord, charge processeur, aller-retour DX7).

## 8. Licences

- fm1-emu : MIT, fichiers repris avec leur en-tête et la mention de l'auteur.
- Firmwares : GPL-3.0 pour la plupart, MPL-2.0 pour 9, Apache-2.0 pour le V15 officiel. Le dépôt et le commit exact de la source sont indiqués pour chacun dans `catalogue.json` et le README.
- FM-1+VA de Baud Girl n'est ni inclus ni redistribué ; la réimplémentation ne reprend aucun code de son firmware.

## 9. Hors périmètre

- La mise à jour automatique du catalogue depuis le Hub.
- L'archivage des sources des firmwares (1,7 Go), possible plus tard.
- Le SMK-37 et l'installation sur un FM-1 réel.
