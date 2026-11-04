# Consigne : fiches de firmware

Tu rédiges, ou tu relis, des fiches d'aide pour un émulateur de M-VAVE FM-1. Une fiche dit à quelqu'un qui vient de charger un firmware comment s'en servir sur le panneau du FM-1.

## Ce que tu as

- `.fiches-sources/<id>/repo` : la doc du dépôt du firmware, au commit du catalogue (README, `docs/`, manuels). Le reste du dépôt s'obtient avec `git -C .fiches-sources/<id>/repo show <commit>:<chemin>`.
- `firmwares/catalogue.json` : nom, auteur, `depot`, `commit_source`, description.
- `firmwares/fiches/fm1va.json` : une fiche terminée, comme exemple de ton et de forme.
- Ne jamais exécuter le code des dépôts.

## Le format, `firmwares/fiches/<id>.json`

```json
{
  "id": "…",
  "resume": "Une ou deux phrases.",
  "commandes": [{ "commande": "FX", "role": "…" }],
  "gestes": ["SEL maintenu + ALGORITHM : …"],
  "modes": [{ "nom": "…", "texte": "…" }],
  "a_savoir": ["…"],
  "source": { "url": "https://github.com/<o>/<r>/blob/<commit>/README.md", "commit": "<commit>" },
  "d_apres_le_code": false
}
```

- `commande` vient de cette liste fermée, dans cet ordre, au plus une fois chacune : `OCT-`, `OCT+`, `FX`, `SEL`, `ENV`, `LFO`, `EDIT`, `GLO`, `HOME`, `SAVE`, `ARP`, `SEQ`, `PLAY`, `REC`, `MASTER`, `SELECT`, `PRESETS`, `ALGORITHM`, `Touches`, `Touches blanches`, `Touches noires`. Si le rôle change selon le mode, le dire dans le texte du rôle.
- `resume` et `commandes` ne sont jamais vides ; `gestes`, `modes` peuvent l'être (`[]`) ; `a_savoir` est facultatif (limites, différences avec l'appareil).
- `source.commit` est le `commit_source` du catalogue ; `source.url` est le fichier principal lu, au commit (`.../blob/<commit>/...`).
- Texte brut, sans HTML, sans le caractère `<`.

## Les règles

- Français, phrases courtes, notes en Do, Ré, Mi. Pas d'emoji, pas de tiret cadratin.
- Les noms de commandes tels qu'imprimés sur le FM-1.
- Seulement ce que dit la source au commit. Rien d'inventé, rien emprunté à un firmware parent ou voisin, même s'il est proche.
- Si la doc ne décrit pas les commandes : lire le code qui traite les boutons (`git show`), le dire dans `resume` n'est pas nécessaire, mais pose `"d_apres_le_code": true`. Si même le code ne permet pas de savoir, une commande reste absente plutôt que devinée.
- Garde le nécessaire pour jouer : à quoi sert chaque commande, les gestes, les modes. Pas d'historique du projet, pas d'instructions de compilation.

## Vérifier

`node --test tests/fiches.test.mjs` doit passer.

## Pour un relecteur

Tu ne modifies rien. Pour chaque fiche de ton lot, compare chaque affirmation à la source. Rends, par fiche, une liste `id | affirmation | ce que dit la source | correction proposée`, ou `id | aucun écart`. Signale aussi une commande importante de la source oubliée par la fiche.
