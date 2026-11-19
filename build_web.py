"""Génère eCXA.html : l'app Streamlit complète dans un seul fichier, exécutée
dans le navigateur grâce à stlite (Python/WebAssembly). Aucun serveur requis.

    uv run python build_web.py
"""

import base64
import json
import tomllib
from pathlib import Path

STLITE = "1.12.2"
ICI = Path(__file__).parent

fichiers = {
    nom: (ICI / nom).read_text(encoding="utf-8")
    for nom in ["main.py", "style.css"]
}
# Miniatures WebP (~4 Ko chacune) : voir images/web/
for img in sorted((ICI / "images" / "web").glob("*.webp")):
    b64 = base64.b64encode(img.read_bytes()).decode()
    fichiers[f"images/web/{img.name}"] = {"url": f"data:image/webp;base64,{b64}"}

# Thème (.streamlit/config.toml) -> option streamlitConfig de stlite ("theme.primaryColor": ...)
config = tomllib.loads((ICI / ".streamlit" / "config.toml").read_text(encoding="utf-8"))
streamlit_config = {f"{section}.{cle}": val for section, cles in config.items() for cle, val in cles.items()}

html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>eCXA</title>
  <!-- Chargement au plus tôt : connexion au CDN et téléchargement du moteur en parallèle -->
  <link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin />
  <link rel="modulepreload" href="https://cdn.jsdelivr.net/npm/@stlite/browser@{STLITE}/build/stlite.js" />
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@stlite/browser@{STLITE}/build/stlite.css" />
</head>
<body style="margin:0;background:#f5f5f7">
  <div id="root"></div>
  <script type="module">
    import {{ mount }} from "https://cdn.jsdelivr.net/npm/@stlite/browser@{STLITE}/build/stlite.js";

    // IndexedDB est refusé par certains navigateurs quand la page est ouverte
    // en file:// ("invalid security context") : on le teste avant de l'utiliser.
    async function indexedDbDisponible() {{
      try {{
        await new Promise((ok, ko) => {{
          const req = indexedDB.open("ecxa-test");
          req.onsuccess = () => {{ req.result.close(); ok(); }};
          req.onerror = () => ko(req.error);
        }});
        return true;
      }} catch (e) {{
        return false;
      }}
    }}

    const persistant = await indexedDbDisponible();
    const files = {json.dumps(fichiers, ensure_ascii=False)};
    files["config_web.json"] = JSON.stringify({{ persistant }});
    mount(
      {{
        requirements: ["openpyxl"],  // pas de matplotlib : graphiques en SVG
        entrypoint: "main.py",
        files,
        idbfsMountpoints: persistant ? ["/mnt"] : [],
        streamlitConfig: {json.dumps(streamlit_config)},
      }},
      document.getElementById("root"),
    );
  </script>
</body>
</html>
"""
(ICI / "eCXA.html").write_text(html, encoding="utf-8")
print(f"eCXA.html généré ({len(html) / 1e6:.1f} Mo)")
