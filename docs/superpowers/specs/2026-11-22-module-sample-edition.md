# Module sample : éditer le sample entier et ses tranches, découpage intelligent

Complète `2026-11-22-module-sample-ecran-non-tactile.md` (MACRO, menus, écran non tactile). Approuvé par l'utilisateur le 22/11/2026 (« Ok »).

## Intention
Pouvoir éditer le sample entier (le rogner) et chacune de ses 16 tranches, avec les deux potards : SELECT règle le début, MACRO la fin, et un bouton SEL valide. Le découpage en tranches ne coupe pas le son au milieu d'une onde, mais dans un creux proche.

## Approches pour la hauteur et le volume d'une tranche
1. **Un menu de plus, SON** (SELECT : hauteur, MACRO : volume). **Choisie** par l'utilisateur : « le plus simple, on verra des optimisations à l'usage ».
2. SEL valide et passe à la paire suivante (début/fin, puis hauteur/volume) : écartée pour l'instant.

## Panneau
ASSIGN devient **SEL**. Rien d'autre ne change.

## Menus
EDIT fait défiler : **SAMPLE**, **TRANCHE**, **SON**, **CAPTURE**, puis hors menu. SEND ouvre l'Envoi depuis partout ; EDIT depuis l'Envoi revient hors menu.

- **SAMPLE** (le sample entier) : SELECT déplace le début de la partie gardée, MACRO sa fin ; tout le sample s'affiche, la partie gardée en clair. **SEL** rogne le sample à cette partie, le redécoupe en 16 tranches (découpage intelligent) dont les réglages repartent de zéro, et recalcule s'il boucle en mesures. Quitter le menu sans SEL ne change rien.
- **TRANCHE** (la tranche choisie au pad) : SELECT déplace son début sans bouger sa fin, MACRO déplace sa fin ; l'écran zoome sur la tranche. On entend le réglage tout de suite. **SEL** l'enregistre ; quitter le menu, ou choisir une autre tranche au pad, sans SEL le défait.
- **SON** (la même tranche) : SELECT règle la hauteur (±24 demi-tons), MACRO le volume (0 à 100) ; même règle de validation que TRANCHE.
- **CAPTURE** et **ENVOI** : inchangés (MACRO choisit la colonne, SELECT règle sa valeur, aucune validation).
- **Tempo** : plus de colonne tempo dans les menus ; MACRO assigné à TEMPO le règle hors menu. Le tempo reste affiché.

## Hors menu
Inchangé : SELECT change de sample, MACRO règle sa cible. SEL tenu en tournant MACRO choisit la cible ; un appui court sur SEL garde la liste ouverte, un second la ferme.

## Découpage intelligent
- Chaque coupe part de sa place régulière (i/16 du sample) et glisse vers le creux de volume le plus proche (enveloppe du son), sans s'écarter de plus d'un quart de tranche ; elle se cale ensuite sur le passage à zéro de l'onde le plus proche.
- Il sert à la capture, à l'import, et après un rognage.
- Les débuts et fins réglés aux potards (SAMPLE, TRANCHE) se calent aussi sur un passage à zéro.

## Hors du champ
Pas d'annulation après un rognage validé (SEL est la sécurité) ; pas de nouvelle touche clavier ni de nouveau bouton.

## Laissé au constructeur
La taille de la fenêtre d'enveloppe ; les bornes des repères (une tranche garde au moins 10 ms, un sample rogné au moins 0,1 s) ; la façon d'afficher la partie gardée et les repères ; le pas des potards.
