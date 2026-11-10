# Vérification des firmwares

Chaque paquet local démarre dans le sélecteur (Chromium sans interface, cœur fm1-emu à 100 MHz). Critères : démarrage en moins de 30 s, au moins 500 pixels allumés après 4 s, niveau RMS supérieur à 0.0005 pendant PLAY puis la touche 12 tenue 1 s.

| Firmware | État déclaré | Résultat | Pixels | RMS | Démarrage (s) |
|---|---|---|---:|---:|---:|
| AISLING | vérifié | vérifié | 8406 | 0.10594 | 0.4 |
| Arcturus S6 | vérifié | vérifié | 13426 | 0.02789 | 0.2 |
| ARTIHIVE | vérifié | vérifié | 55101 | 0.00921 | 0.4 |
| Bigorna | vérifié | vérifié | 15129 | 0.08269 | 0.1 |
| Blop | vérifié | vérifié | 50988 | 0.06871 | 0.4 |
| CTL-1 | À VÉRIFIER | silencieux | 57600 | 0 | 0.1 |
| DARK-1 | vérifié | vérifié | 57600 | 0.18849 | 0.2 |
| Demake | vérifié | vérifié | 57600 | 0.02494 | 0.3 |
| Dinghy | À VÉRIFIER | vérifié | 9755 | 0.04756 | 0.1 |
| FIZZ | À VÉRIFIER | vérifié | 4526 | 0.02765 | 0.1 |
| fm1-dock | À VÉRIFIER | vérifié | 1190 | 0.05375 | 0.2 |
| FOMAJAM | À VÉRIFIER | vérifié | 18946 | 0.12249 | 0.1 |
| Hortator | À VÉRIFIER | vérifié | 57600 | 0.02589 | 0.1 |
| K-WASUB | vérifié | vérifié | 19365 | 0.10828 | 0.3 |
| KARMA | vérifié | vérifié | 7691 | 0.09463 | 0.2 |
| LOOM-8 | À VÉRIFIER | silencieux | 35348 | 0 | 0.0 |
| ORBIT | À VÉRIFIER | vérifié | 7751 | 0.09293 | 0.1 |
| Penumbra | vérifié | vérifié | 11208 | 0.00522 | 0.3 |
| PT/FM | vérifié | vérifié | 4809 | 0.0186 | 0.3 |
| SLOOP | À VÉRIFIER | vérifié | 13471 | 0.0756 | 0.1 |

Total : 20 firmwares, 18 vérifiés, 2 démarrés sans son mesuré, 0 qui ne démarrent pas.

« Silencieux » : le firmware démarre et affiche son écran, mais ne produit pas de son avec PLAY et une touche ; c'est attendu pour un contrôleur MIDI ou un moniteur, et ne vaut pas un échec.
