# eCXA (Streamlit)

Version Streamlit de l'application Tkinter `eCXA.py` : saisie des amplitudes articulaires
du membre supérieur (épaule, coude, poignet, main) et du membre inférieur (hanche, genou,
cheville), scores en % de la norme, radars MS/MI, score global, et enregistrement dans
`eCXA.xlsx` (même format de colonnes que l'original).

- Chaque articulation est représentée par son illustration (miniatures WebP dans `images/web/`,
  générées à partir des PNG de `images/`).
- Scores plafonnés à 100 %. Couleur selon la gravité (plus le score est bas, plus c'est grave) :
  ≥ 90 normal (vert), ≥ 75 léger (jaune), ≥ 50 modéré (orange), < 50 sévère (rouge).
  Seuils modifiables dans `SEUILS` (main.py).
- L'Excel contient aussi les scores `eCXA_MS`, `eCXA_MI` et `eCXA` (en %) en fin de ligne. Un fichier
  d'une ancienne version (9 colonnes) est complété automatiquement au premier enregistrement ou à l'import.
- Une mesure vide n'est pas comptée comme 0 : le score du membre s'affiche quand toutes ses
  articulations sont saisies. Les cases vides restent vides dans l'Excel.
- Radars dessinés en SVG (même ordre et orientation des axes que `radar_plot_eCXA_MS/MI.py`,
  qui ne sont plus utilisés) : plus besoin de matplotlib, la page charge beaucoup plus vite.

## Lancer

```bash
cd ~/Documents/eCXA
uv run streamlit run main.py
```

uv crée l'environnement et installe les dépendances au premier lancement.
L'app s'ouvre sur http://localhost:8501.

Pour reprendre tes anciennes données, copie ton `eCXA.xlsx` existant dans ce dossier.

## Version navigateur (sans installation)

`eCXA.html` contient toute l'app : il suffit de l'ouvrir dans Chrome, Edge, Firefox ou Safari
(double-clic). Python tourne dans le navigateur grâce à [stlite](https://github.com/whitphx/stlite) :
aucun serveur, aucune donnée envoyée. Une connexion internet est nécessaire au chargement
(~20-30 s la première fois, ensuite c'est en cache).

- Les enregistrements sont gardés dans le navigateur (IndexedDB), propres à chaque ordinateur/navigateur.
- Utilise « Télécharger eCXA.xlsx » pour garder une copie, et « Importer » pour reprendre un fichier.

Si la page reste bloquée sur « Loading Pyodide… » en l'ouvrant par double-clic
(certains navigateurs restreignent les pages ouvertes en `file://`), lance :

```bash
python3 serve.py
```

L'app s'ouvre sur http://localhost:8765/eCXA.html, avec sauvegarde automatique.
Pour la partager sans installation, héberge `eCXA.html` en https (GitHub Pages, serveur intranet…).

Après une modification de `main.py` ou des radars, régénère le fichier :

```bash
uv run python build_web.py
```
