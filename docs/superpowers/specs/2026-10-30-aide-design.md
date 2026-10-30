# FM-1 : manuel d'utilisation, raccourcis clavier et fiches par firmware

Date : 30 octobre 2026. Statut : en relecture.

## 1. Objet

L'aide de la page tient aujourd'hui en trois volets sous le FM-1 (« Jouer », « Gestes du firmware », « Ce qui manque encore »), écrits pour FM-1+VA seul. Avec 115 firmwares open source dans le sélecteur, elle doit séparer ce qui vaut pour toute la page de ce qui dépend du firmware chargé.

Décisions validées :

- trois volets : **Manuel d'utilisation** (général), **Raccourcis clavier**, **Fonctions de « firmware »** (suit le firmware chargé) ;
- ils restent un accordéon sous le FM-1, avec l'encoche actuelle ; en Duo, l'aide reste masquée comme aujourd'hui ;
- les raccourcis sont un clavier d'ordinateur dessiné ; le volet ouvert prend toute la largeur ;
- une fiche complète, en français, pour chacun des 116 firmwares (115 du catalogue et FM-1+VA), rédigée d'après la doc de son dépôt au commit du catalogue ;
- rédaction par des agents en parallèle, relecture par d'autres agents qui n'ont pas écrit les fiches relues.

## 2. Critères de réussite

1. Les trois volets s'affichent sous le FM-1, en Solo, sur PC, iPad et iPhone.
2. Le volet 3 montre la fiche du firmware choisi, même avant l'allumage, et change avec lui sans recharger la page.
3. Les 116 fiches existent, et chacune a été relue contre sa source par un agent qui ne l'a pas écrite. Une fiche ne dit rien que sa source ne dise.
4. Le dessin des raccourcis est produit depuis la table des raccourcis (`KEYMAP`, `ENCMAP`) : les deux ne peuvent pas diverger.
5. La suite de tests existante passe toujours.

## 3. Les trois volets

Ils remplacent les trois volets actuels dans `<section class="notes">`, dans cet ordre.

### 3.1 Manuel d'utilisation

Le même pour tous les firmwares. Rubriques, en liste de définitions comme le volet « Jouer » actuel :

- **Allumer** : le bouton Allumer du FM-1, l'interrupteur sous le FM-1 ; éteindre efface les réglages du firmware actif.
- **Firmwares** : le sélecteur, les optimisés (natifs et FM-1+VA) avant les émulés, la recherche, « Ouvrir un .fwsc… » pour un paquet personnel ; « Redémarrer » quand un firmware s'arrête.
- **Boutons propres à un firmware** : certains firmwares ajoutent un bouton sous le FM-1 (Importer un son DX7, Échantillons) ; leur fiche l'explique.
- **Coloris**, **Solo et Duo** (le texte « Duo » actuel), **MIDI** (entrée, canal, voyant), **Plein écran**.
- **Ce que le navigateur garde** : les sauvegardes de chaque firmware, le dernier firmware choisi, le coloris.
- **Crédits et licences** : le paragraphe actuel sur Baud Girl, DUB-1 et la licence, élargi au cœur fm1-emu et aux licences des firmwares (`firmwares/licences/`).

Chaque affirmation est vérifiée contre le code de la page au moment de l'écrire.

### 3.2 Raccourcis clavier

**Le dessin.** Un SVG produit en JavaScript, mis à l'échelle de la largeur du volet :

- les rangées utiles d'un clavier d'ordinateur : Échap ; la rangée des chiffres ; les trois rangées de lettres ; Espace ; Entrée ; les flèches ;
- les touches sans raccourci restent dessinées, estompées, pour que le clavier se reconnaisse ;
- chaque touche avec raccourci porte sa lettre en haut à gauche et sa fonction en bas : la note (« Do 4 », « Do♯ 4 »), le bouton (« FX », « PLAY »), ou la molette et son sens (« SELECT − ») ;
- trois familles de couleur, avec une légende sous le dessin : notes (couleur d'accent de la page), boutons, molettes ;
- le dessin parcourt `KEYMAP` et `ENCMAP` ; le nom des notes vient de l'indice de touche (7 = Do 4).

**Les lettres.** Celles du clavier de la personne quand le navigateur les donne (`navigator.keyboard.getLayoutMap`, Chrome et Edge). Sinon, de l'AZERTY si la langue du navigateur est le français de France ou de Belgique (`fr`, `fr-FR`, `fr-BE`), du QWERTY sinon. La rangée des chiffres affiche toujours les chiffres, qui sont imprimés sur les touches dans les deux dispositions.

**La largeur.** Ouvert, ce volet occupe toute la largeur de la grille des volets. Sur un écran étroit, le dessin garde une taille lisible et défile horizontalement.

**Les gestes**, sous le dessin, repris du volet « Jouer » actuel : plusieurs touches à la fois ; les molettes (glisser, molette de la souris, accélération, Maj pour un pas d'une unité) ; maintenir un bouton (Maj+clic, clic droit, deux mains au doigt).

Le dessin a `role="img"` et un `aria-label` qui énumère les raccourcis.

### 3.3 Fonctions de « firmware »

**Le titre** suit le firmware choisi (`active` dans le code du sélecteur) : « Fonctions de Felucca ». Sous le titre, une ligne tirée du catalogue : auteur · version · licence.

**Le contenu** est la fiche du firmware (section 4), rendue dans l'ordre :

1. **En bref** ;
2. **Commandes** : une liste de définitions, commande → rôle ;
3. **Gestes** ;
4. **Modes et écrans** : une rubrique par mode ;
5. **Manuel complet** : le lien vers la source, et la mention « Rédigée d'après le code du firmware, faute de doc. » quand c'est le cas.

**Les cas particuliers :**

- un .fwsc ouvert depuis Fichiers (`id: "local"`) : « Pas de fiche pour ce firmware. » ;
- une fiche introuvable ou injoignable : « Fiche indisponible pour le moment. » ;
- la fiche est chargée à l'ouverture du volet ou au changement de firmware si le volet est ouvert, puis gardée en mémoire pour la session.

**FM-1+VA** : sa fiche reprend le volet « Gestes du firmware », la répartition des presets (001–064 FM…), le bouton Importer un son DX7 et le volet « Ce qui manque encore ».

## 4. Les fiches

### 4.1 Fichiers

Un fichier par firmware, `firmwares/fiches/<id>.json`, plutôt qu'un fichier unique : la page ne charge que la fiche du firmware choisi, et deux rédacteurs n'écrivent jamais dans le même fichier.

```json
{
  "id": "felucca",
  "resume": "Une ou deux phrases.",
  "commandes": [
    { "commande": "FX", "role": "…" },
    { "commande": "SELECT", "role": "…" }
  ],
  "gestes": ["SEL maintenu + ALGORITHM : …"],
  "modes": [{ "nom": "…", "texte": "…" }],
  "source": { "url": "https://github.com/hugelton/Felucca/blob/<commit>/README.md", "commit": "<commit>" },
  "d_apres_le_code": false
}
```

**Les règles :**

- `commande` est pris dans une liste fermée : les 14 boutons (`OCT-`, `OCT+`, `FX`, `SEL`, `ENV`, `LFO`, `EDIT`, `GLO`, `HOME`, `SAVE`, `ARP`, `SEQ`, `PLAY`, `REC`), les 4 molettes (`MASTER`, `SELECT`, `PRESETS`, `ALGORITHM`), et `Touches`, `Touches blanches`, `Touches noires`.
- Chaque commande figure une fois au plus, dans l'ordre de cette liste. Un rôle qui change selon le mode le dit dans son texte.
- `gestes` et `modes` peuvent être vides ; `resume` et `commandes` non.
- Pour un firmware du catalogue, `source.commit` vaut le `commit_source` du catalogue, et `source.url` commence par son `depot`. Pour FM-1+VA, `source.url` est le manuel de Baud Girl et `source.commit` vaut `null`.
- Le texte est du texte brut. La page l'insère par `textContent`, jamais comme du HTML.

### 4.2 Rédaction

**Les sources.** Un script, `tools/fiches_sources.sh`, rapatrie dans un dossier de travail non suivi la doc de chaque dépôt au `commit_source` du catalogue : README, dossier `docs`, manuels, images des commandes. Si la doc ne décrit pas les commandes, le rédacteur lit l'aide de la page web du firmware ou le code qui traite les boutons, et pose `d_apres_le_code: true`.

**Les rédacteurs.** Des agents en parallèle, une dizaine de firmwares chacun, avec une consigne commune :

- le format et les règles de 4.1 ;
- le français, avec les noms du panneau tels qu'imprimés ;
- seulement ce que dit la source : rien d'inventé, rien d'extrapolé d'un firmware parent ;
- des phrases courtes, et des notes à la française (Do, Ré, Mi).

**La relecture.** D'autres agents relisent chaque fiche contre sa source, par lots différents de ceux de la rédaction. Ils listent chaque écart : affirmation absente de la source, commande mal nommée, oubli important. Je corrige, puis le test de 6.1 valide le tout.

**FM-1+VA.** J'écris sa fiche moi-même, d'après le texte actuel de la page et le manuel FM-1+VA.

## 5. Code

**Dans `index.html` :**

- le balisage des trois volets ;
- le dessin du clavier, une fonction qui lit `KEYMAP` et `ENCMAP` ;
- le chargement et le rendu des fiches, appelés là où `active` change (`pick`) et à l'ouverture du volet 3 ;
- l'ancien remplacement des lettres dans les `<kbd data-code>` disparaît avec le volet « Jouer » ; la carte des lettres sert au dessin.

**Les styles** suivent ceux des volets actuels. Une règle `grid-column: 1 / -1` s'applique au volet des raccourcis quand il est ouvert.

## 6. Tests

### 6.1 Les fiches (`tests/fiches.test.mjs`, Node)

- Chaque `id` du catalogue, plus `fm1va`, a son fichier.
- Le schéma : champs requis, `resume` et `commandes` non vides, commandes dans la liste fermée, sans doublon et dans l'ordre.
- `source.commit` égal au `commit_source` du catalogue, et `source.url` sous `depot`.
- Aucun `<` dans les textes.

### 6.2 La page (`tests/test_aide.py`, Playwright)

- Les titres des trois volets.
- Changer de firmware change le titre et le contenu du volet 3 ; un .fwsc local affiche « Pas de fiche pour ce firmware. » ; une fiche injoignable affiche « Fiche indisponible pour le moment. ».
- Chaque code de `KEYMAP` et `ENCMAP` a une touche dessinée qui porte sa fonction.
- Sans `getLayoutMap` et en `fr-FR`, la touche `KeyA` porte « Q » ; en `en-US`, « A ».
- Ouvert, le volet des raccourcis occupe toute la largeur.

### 6.3 Non-régression

La suite complète (`pytest` et les tests Node) passe. Les tests qui lisaient l'ancien volet « Jouer » sont adaptés.

## 7. Hors champ

- L'aide en Duo.
- Une version anglaise.
- Les touches du clavier d'ordinateur à côté des commandes, dans les fiches.
- Une fiche pour un .fwsc hors catalogue.
