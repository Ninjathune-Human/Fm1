# Module sample : écran non tactile, potard MACRO et bouton ASSIGN

Approuvé par l'utilisateur le 22/11/2026 (« C'est ok »). Remplace, pour ce qu'il touche, la spec du module (2026-11-22-module-sample).

## Intention
L'écran du module est un affichage, comme celui du FM-1 : on ne le touche pas. Tout ce qui s'y faisait au doigt passe par les commandes du panneau. L'utilisateur a dessiné le nouveau panneau : un troisième potard en haut, et un bloc de boutons de 3 × 2.

## Approches
1. Aucun bouton de plus, appui sur SELECT : écartée, SELECT ne se pousse pas.
2. Deux boutons ◀ ▶ sous l'écran : écartée par le croquis de l'utilisateur.
3. **Un potard MACRO et un bouton ASSIGN, selon le croquis : choisie.** MACRO est d'abord assignable (choix 1 de l'utilisateur) ; dans un menu, il choisit la colonne.

## Panneau
```
 MASTER  SELECT  MACRO      [ écran ]
 [ FILE ]  [ EDIT ]  [ SEND ]
 [ASSIGN]  [ PLAY ]  [ REC  ]
```
- MACRO : troisième potard de la rangée du haut, entre SELECT et l'écran (le rond rouge du croquis).
- FILE à la place d'EDIT ; EDIT à la place de SEND ; SEND et REC dans la nouvelle troisième colonne ; PLAY (lecture et arrêt, comme aujourd'hui) à la place de REC ; ASSIGN à la place de PLAY.

## Conduite
- **Écran** : ne réagit plus au toucher. Le code des gestes à l'écran (choix de colonne, glisser une valeur, poignées, pincement, toucher d'une tranche, puces de source et de cible, tempo touché) et leurs tests sont retirés.
- **Hors menu** (on joue) : MACRO règle sa cible assignée, le filtre par défaut ; SELECT change de sample.
- **Dans un menu** (Édition, Capture, Envoi) : MACRO choisit la colonne de l'en-tête (et le tempo en dernière position sur Édition) ; SELECT règle sa valeur.
- **EDIT** fait défiler : Édition, Capture, puis hors menu. L'écran indique où l'on est.
- **SEND** ouvre l'Envoi, qui est un menu ; SEND y envoie comme aujourd'hui (premier appui pour préparer, second pour envoyer).
- **ASSIGN** : tenu, tourner MACRO choisit sa cible dans la liste affichée : FILTER, RES, ECHO, FEEDBACK, TEMPO. Le choix est gardé.
- **Filtre** : la zone tactile prend la main tant qu'un doigt la touche ; au lever, le filtre revient à la valeur de MACRO (et non au neutre) quand MACRO règle le filtre ou la résonance.
- **FILE** : ouvre le choix d'un fichier son au lever du doigt (Safari n'ouvre la fenêtre qu'alors). La source FILE disparaît de la colonne SOURCE de Capture.
- **Zoom** : quand la colonne active est START ou LEN, l'écran montre la tranche choisie en grand ; sinon tout le sample.
- Les pads choisissent toujours la tranche.

## Laissé au constructeur
Les positions exactes dans le dessin du panneau ; la manière d'afficher le menu courant et la liste d'ASSIGN ; les touches clavier des nouvelles commandes, à l'image des touches existantes.
