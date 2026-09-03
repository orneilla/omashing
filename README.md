# Omashing

Carnet de *mashing* colorimétrique — les **348 accords** et **159 couleurs** de
*A Dictionary of Color Combinations* (配色事典) de **Sanzo Wada**, sortis du manuel
et transformés en petite application à consulter pour composer une tenue, une
slide, ou n'importe quoi d'autre.

Projet **personnel**, non commercial.

## Ouvrir l'application

`index.html` s'ouvre directement dans un navigateur, sans serveur ni installation :
tout est dans le fichier, données comprises. C'est suffisant sur un ordinateur.

## Installer sur l'écran d'accueil

L'app est une **PWA** : servie depuis une vraie adresse web, elle s'installe comme
une application (icône, plein écran, fonctionne hors-ligne). Il lui faut donc un
hébergement. Ce dépôt est privé et contient le scan du manuel, qui n'a pas à être
publié — deux voies, au choix :

- **Un hébergeur gratuit branché sur le dépôt privé.** Cloudflare Pages, Netlify ou
  Vercel servent un dépôt privé sans le rendre public. Créer le compte, autoriser
  GitHub, choisir ce dépôt, laisser les réglages de build vides (site statique,
  racine du dépôt). Rien ne devient public.
- **GitHub Pages**, qui exige un dépôt **public** sur le plan gratuit. À ne faire
  qu'avec un dépôt sans le PDF — par exemple un second dépôt ne contenant que
  `index.html`, `data/`, `icons/`, `manifest.webmanifest` et `sw.js`.

Une fois le site en ligne : **iPhone** — l'ouvrir dans **Safari**, bouton Partager →
*Sur l'écran d'accueil*. **Android** — Chrome propose *Installer l'application*.

L'icône est le motif en croix des planches à quatre couleurs du manuel. Après la
première ouverture, tout est mis en cache : l'app marche sans réseau.

## Ce qu'il y a dedans

- **Accords** — les 348 planches du manuel, filtrables par nombre de couleurs
  (duo / trio / quatuor), par famille chromatique, ou par recherche libre
  (nom anglais, nom japonais, kana, hex, numéro).
- **Mash !** — tire un accord au hasard dans le filtre courant.
- **Trois vues** par accord : *Planche* (la disposition du livre, croix comprise
  pour les quatuors), *Tenue* (les couleurs posées sur une silhouette, avec
  permutation des rôles), *Slide* (fond / titre / accents pour une présentation).
- **Copier** les hex, un bloc de variables CSS, ou une fiche complète.
- **Favoris**, gardés dans le navigateur.
- **Couleurs** — les 159 teintes classées par famille, avec nom japonais, kana,
  hex et CMJN ; cliquer une couleur montre tous les accords qui l'utilisent.

## Fichiers

| | |
|---|---|
| `index.html` | l'application, autonome (généré) |
| `manifest.webmanifest`, `sw.js`, `icons/` | le nécessaire PWA (installation, hors-ligne) |
| `app/template.html` | la source de l'application |
| `data/omashing.json` | les données seules, réutilisables (généré) |
| `scripts/extract.py` | extraction du PDF vers `data/omashing.json` |
| `scripts/colors.tsv` | l'index des 159 couleurs relevé sur le manuel |
| `scripts/build_app.py` | injecte les données dans le gabarit |
| `scripts/make_icons.py` | génère les icônes depuis la palette |

Régénérer :

```bash
pip install pymupdf numpy
python3 scripts/extract.py      # PDF  -> data/omashing.json  (quelques minutes)
python3 scripts/build_app.py    # JSON -> index.html
python3 scripts/make_icons.py   # JSON -> icons/
```

Après une modification, penser à incrémenter `CACHE` dans `sw.js` pour que les
appareils déjà installés récupèrent la nouvelle version.

## Format des données

```jsonc
{
  "colors": [
    { "id": 62, "name": "Yellow Orange", "jp": "柑子色", "kana": "こうじいろ",
      "hex": "#FF950E", "rgb": [255,149,14], "cmyk": [0,45,100,0],
      "group": "yellows", "count": 22 }
  ],
  "combinations": [
    { "id": 288, "size": 4, "colors": [62, 148, 84, 159] }
  ]
}
```

`colors` est ordonné comme le catalogue du livre (1-159) ; `combinations` comme
les planches (1-348). Dans une combinaison, l'ordre des couleurs suit la
disposition imprimée : gauche → droite pour les duos et trios, et
haut → gauche → droite → bas pour la croix des quatuors. `count` indique sur
combien de pastilles la teinte a été mesurée.

Deux noms anglais apparaissent deux fois dans le catalogue (*Eugenia Red* n° 12
et 13, *Grayish Lavender* n° 134 et 135) : ce sont bien deux teintes distinctes,
d'où les `id`.

## D'où viennent les valeurs

- **CMJN** : relevés dans l'index du manuel. 154 des 159 ont été re-confirmés
  automatiquement par la couche texte du PDF ; les 5 restants (mal océrisés) ont
  été relus à l'image.
- **Hex** : *mesurés* sur le scan — médiane au centre de chaque pastille, sur les
  planches et sur l'index, normalisée par le blanc du papier de la page. Les deux
  mesures indépendantes concordent à ~7/255 en moyenne. La conversion naïve
  CMJN → RVB donne des teintes nettement fausses sur les saturés (elle rend
  *Hermosa Pink* magenta), d'où la mesure.
- **Accords** : disposition des pastilles détectée géométriquement, noms lus dans
  la couche texte du PDF, les deux recoupés. L'index inverse du livre
  (couleur → liste d'accords, p. 261-282) sert de contrôle indépendant : 93 % des
  entrées relisibles concordaient d'emblée, le reste a été corrigé.

C'est une extraction automatique d'un scan : quelques attributions peuvent rester
imparfaites. Le CMJN du livre est conservé tel quel dans les données, donc tout
est revérifiable.

## Source

*A Dictionary of Color Combinations* — 配色事典 大正・昭和の色彩ノート,
Sanzo Wada (和田三造, 1883-1967), d'après *Haishoku Soukan* (配色総鑑, 1933-34),
Seigensha Art Publishing, 2010. ISBN 978-4-86152-247-5.

Ce dépôt ne redistribue ni les planches ni le texte du livre — seulement les
valeurs colorimétriques et les regroupements, relevés pour un usage personnel.
