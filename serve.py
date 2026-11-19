"""Ouvre eCXA.html via http://localhost (au lieu de file://) pour que le
navigateur autorise Pyodide (WebAssembly) et la sauvegarde locale.

    python3 serve.py        (aucune dépendance, Python standard)

Laisser la fenêtre ouverte pendant l'utilisation ; Ctrl+C pour arrêter.
"""

import functools
import http.server
import threading
import webbrowser
from pathlib import Path

PORT = 8765
dossier = Path(__file__).parent
Handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(dossier))

with http.server.ThreadingHTTPServer(("127.0.0.1", PORT), Handler) as serveur:
    url = f"http://localhost:{PORT}/eCXA.html"
    print(f"eCXA disponible sur {url}  (Ctrl+C pour arrêter)")
    threading.Timer(0.5, webbrowser.open, args=[url]).start()
    try:
        serveur.serve_forever()
    except KeyboardInterrupt:
        print("\nArrêt.")
