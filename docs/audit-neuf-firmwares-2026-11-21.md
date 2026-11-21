# Audit de neuf firmwares demandés (21 novembre 2026)

Module `.rfm1` de RemoteFM1FW (ABI 6), vérifié par son sha256 à la construction, joué par `tools/worklets/rfm1.js`.
Essai en banc (Node) : démarrage, écran dessiné, son par MIDI et par les touches, LED.

| Firmware | Version | Licence (manifeste) | Contenu tiers à noter | Décision |
|---|---|---|---|---|
| AURORA (twochannels) | 0.8.0 | GPL-3.0-only | police Terminus (OFL-1.1) | ajouté, natif |
| FM-1 Chimera Vocal (Shan-Sherif) | 0.8.0 | MPL-2.0 AND MIT | CHIMERA de J. Hodge (MIT, nom repris avec sa permission), dictionnaire CMU, police Barlow (OFL-1.1) | ajouté, natif |
| Dungeon Tracker (BourbonWX) | 1.5 | GPL-3.0-only | WAVES d'après Ambika (GPL-3.0-or-later), msfa (Apache-2.0), DaisySP et Rings (MIT), échantillons VSCO-2 CE, VCSL et Hügelton (CC0) | ajouté, natif ; une touche joue un échantillon de 0,2 s |
| Golf (BARNIR) | 1.0 | MPL-2.0 | tables d'ondes dont des tables Surge XT (GPL-3.0), Mutable Instruments (MIT), TABELLEN.md | ajouté, natif ; le tout se redistribue sous GPL-3.0 |
| PATCHWERK (Matt Kuebrich) | 1.0.3 | GPL-3.0-only | ymfm (BSD-3), MAME uPD933 (BSD-3), codec SEA (MIT) | ajouté, natif |
| Smileyface (pbarilla) | 1.1.5 | GPL-3.0-only | police Terminus (OFL-1.1) | ajouté, natif |
| Ruido (M. Hernández Domenech) | 0.7.1 | GPL-3.0-only | tables de police de l'affichage tirées de Helvetica Neue, non licenciée (†) | **retenu en attente d'accord** |
| EVILGENIUS (Quixotic7) | 0.1.3 | MPL-2.0 | voix SAM (Software Automatic Mouth), sans licence (†) | **retenu en attente d'accord** |
| LOAF BREAKER (FLEXOR) | 0.9.69 | MPL-2.0 | sons sous droits : boucles Cyberworm (libres de redevance), extraits de disques dont les droits restent à leurs ayants droit ; 83 Mo de breaks ; pas de `.rfm1` publié | **non ajouté** |

Chaque `.rfm1` embarque aussi le code de liaison de FM1VST (GPL-3.0) et le runtime Emscripten (MIT, musl), jusqu'aux
textes de licence qu'il joint.
