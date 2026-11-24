# Audit : touches allumées en MIDI, firmwares natifs

2026-11-24, 95 firmwares natifs (FMDj exclu, sans ROM). Pour chacun : une touche du panneau, puis les 27 notes MIDI de F3 à G5 (53 à 79), canal 1.
On relève les touches du panneau qui s'allument (`tests/audit_midi_leds.py`, résultats bruts dans `docs/audit-midi-leds-2026-11-24.json`).

| Cas | Firmwares |
|---|---|
| Touches allumées en MIDI (au moins 20 notes sur 27) | 47 |
| Allumées au clavier du panneau, jamais en MIDI | 33 |
| Allumées en MIDI pour une partie des notes seulement | 5 |
| N'allument aucune touche, ni au panneau ni en MIDI | 10 |

Aucun firmware n'est muet en MIDI parmi ceux qui jouent des notes au panneau, sauf les cinq marqués « non » ci-dessous (leur MIDI demande peut-être un réglage ou un autre canal : à vérifier un par un).

## Allumées au panneau, jamais en MIDI (33)

Ces firmwares allument la LED dans leur gestion des touches, pas dans celle des notes MIDI : sur le vrai FM-1 aussi, la touche reste éteinte.

| Firmware | Son en MIDI | Notes allumées |
|---|---|---|
| Carnac OS | oui | 0/27 |
| Chipbox | non | 0/27 |
| ChoralRoot | oui | 0/27 |
| Cut-A-Dor | non | 0/27 |
| DRIFT | oui | 0/27 |
| Dungeon Tracker | oui | 0/27 |
| ECHOFIELD | oui | 0/27 |
| Frodhes | non | 0/27 |
| FuMi-1 | oui | 0/27 |
| GATOR | oui | 0/27 |
| Golana | oui | 0/27 |
| Golana DZ Edition | oui | 0/27 |
| Golf | oui | 0/27 |
| GRAINE | oui | 0/27 |
| HERA | oui | 0/27 |
| J6 | oui | 0/27 |
| JIANT FM | oui | 0/27 |
| LOOM-8 | non | 0/27 |
| MONO2K | oui | 0/27 |
| MOPE-1 | oui | 0/27 |
| Mutable Dreams | oui | 0/27 |
| PATCHWERK | oui | 0/27 |
| Polly | oui | 0/27 |
| PurpleMonkey | oui | 0/27 |
| Rainbow Mode | oui | 0/27 |
| Ravel | non | 0/27 |
| Ruido | oui | 0/27 |
| SLOOP 3 | oui | 0/27 |
| SPAMPY | oui | 0/27 |
| Speak37 | oui | 0/27 |
| Unholy Union | oui | 0/27 |
| Vector37 | oui | 0/27 |
| ZEN-1 | oui | 0/27 |

## Allumées en MIDI pour une partie des notes (5)

| Firmware | Son en MIDI | Notes allumées |
|---|---|---|
| 386DX | oui | 14/27 |
| Bunker Evolved | oui | 14/27 |
| FiMba-1 | oui | 7/27 |
| FMini-1 | oui | 15/27 |
| NACHTFAHRT | oui | 18/27 |

## N'allument aucune touche (10)

Ce sont des firmwares sans LED de touches (pads, boîtes à rythmes, instruments à écran) ou dont la touche testée (n° 12) n'a pas de LED.

| Firmware | Son en MIDI | Notes allumées |
|---|---|---|
| Berlinan | non | 0/27 |
| DUELL | oui | 0/27 |
| MIN-1 | oui | 0/27 |
| MONK-1 | oui | 0/27 |
| MYCELIUM | oui | 0/27 |
| Niagara Drift | non | 0/27 |
| PIGEON | non | 0/27 |
| Smileyface | oui | 0/27 |
| TRIBE | non | 0/27 |
| zp12 | oui | 0/27 |
