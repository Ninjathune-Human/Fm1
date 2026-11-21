# Vignettes des firmwares

Une image de 240 x 240 par firmware, pour la grille du sélecteur ; elle sert quand l'auteur n'a pas publié de capture
dans le catalogue de RemoteFM1FW (la capture de l'auteur passe avant si elle est là).

- Les écrans d'accueil ont été pris par `tests/capture_vignettes.py` : le firmware démarre dans la page, HOME est pressé,
  l'écran est enregistré une fois stable (palette de 64 couleurs). Ce sont les écrans des firmwares eux-mêmes,
  sous leur licence (voir `firmwares/licences`).
- Quelques images viennent du dépôt du firmware lui-même, sous sa licence GPL-3.0 :
  `morpheus` (assets/screen_preview.png, benbadio/morpheus-fm1), `kawa` (source/docs/screens/en/boot.png, Guizmoh/Kawa-Tracker-Fm1),
  `bubba` (web/img/00-home.png, Erbubar23/bubba-machine).
- Pour en refaire une : `VIGNETTES=<id> python -m pytest -q -s tests/capture_vignettes.py` (`SANS_HOME=1` si HOME mène ailleurs).
