"""eCXA — version Streamlit de l'application Tkinter d'origine.

Saisie des amplitudes articulaires (X_A) du membre supérieur (MS) et du membre
inférieur (MI), scores en % de la norme (X_N, plafonnés à 100 %), radars, et
enregistrement dans eCXA.xlsx.
"""

import base64
import json
import math
import sys
from datetime import date
from pathlib import Path

import openpyxl
import pandas as pd
import streamlit as st
from openpyxl import Workbook

DOSSIER = Path(__file__).parent
# Version navigateur (stlite / Pyodide) : /mnt est sauvegardé dans le navigateur (IndexedDB)
NAVIGATEUR = sys.platform == "emscripten"
# Sinon : fichier Excel à côté du script (comme l'original)
FICHIER = Path("/mnt/eCXA.xlsx") if NAVIGATEUR else DOSSIER / "eCXA.xlsx"
IMAGES = DOSSIER / "images" / "web"
COLONNES = ["Date", "Name", "Epaule_XA", "Coude_XA", "Poignet_XA", "Main_XA",
            "Hanche_XA", "Genou_XA", "Cheville_XA"]

# Articulation -> amplitude normale X_N (degrés)
MS = {"Epaule": 180, "Coude": 150, "Poignet": 180, "Main": 180}
MI = {"Hanche": 150, "Genou": 180, "Cheville": 120}
NORMES = MS | MI
# Scores ajoutés en fin de ligne dans l'Excel (en %, cellule vide si une mesure manque)
SCORES = {"eCXA_MS": MS, "eCXA_MI": MI, "eCXA": NORMES}
ENTETES = COLONNES + list(SCORES)
FORMAT_PCT = '0" %"'

# Ordre et orientation des axes repris de radar_plot_eCXA_MS / _MI (theta_offset)
RADAR_MS = (["Epaule", "Main", "Poignet", "Coude"], 135)
RADAR_MI = (["Genou", "Hanche", "Cheville"], 30)

# Gravité : plus le score est bas, plus c'est grave. (seuil min, libellé, couleur texte, couleur remplissage)
SEUILS = [
    (90, "Normal", "#248a3d", "#34c759"),
    (75, "Léger", "#936b00", "#ffcc00"),
    (50, "Modéré", "#c93400", "#ff9500"),
    (0, "Sévère", "#d70015", "#ff3b30"),
]
NEUTRE = ("—", "#8e8e93", "#d1d1d6")


# ------------------------------------------------------------------- Calculs
def gravite(score: int | None) -> tuple[str, str, str]:
    if score is None:
        return NEUTRE
    for seuil, libelle, texte, fond in SEUILS:
        if score >= seuil:
            return libelle, texte, fond
    return SEUILS[-1][1:]


def score_articulation(valeur: int | None, norme: int) -> int | None:
    """% de la norme, plafonné à 100 %."""
    return None if valeur is None else round(min(valeur, norme) / norme * 100)


def score_groupe(valeurs: dict, normes: dict) -> int | None:
    """Score d'un groupe d'articulations : None tant qu'une mesure manque."""
    if any(valeurs[a] is None for a in normes):
        return None
    return round(sum(min(valeurs[a], n) for a, n in normes.items()) / sum(normes.values()) * 100)


# ----------------------------------------------------------- Fichier Excel
def init_fichier() -> None:
    FICHIER.parent.mkdir(parents=True, exist_ok=True)
    if not FICHIER.exists():
        wb = Workbook()
        wb.active.append(ENTETES)
        wb.save(FICHIER)


def scores_ligne(valeurs: dict) -> list[int | None]:
    return [score_groupe(valeurs, groupe) for groupe in SCORES.values()]


def mettre_a_niveau(ws) -> None:
    """Fichier d'une version précédente (9 colonnes) : ajoute les colonnes de score
    et les calcule pour les lignes existantes."""
    if [c.value for c in ws[1]][:len(ENTETES)] == ENTETES:
        return
    debut = len(COLONNES) + 1
    for i, nom in enumerate(SCORES):
        ws.cell(row=1, column=debut + i, value=nom)
    for ligne in ws.iter_rows(min_row=2):
        valeurs = {}
        for i, art in enumerate(NORMES):
            v = ligne[2 + i].value
            valeurs[art] = v if isinstance(v, (int, float)) else None
        for i, score in enumerate(scores_ligne(valeurs)):
            ws.cell(row=ligne[0].row, column=debut + i, value=score).number_format = FORMAT_PCT


@st.cache_data(show_spinner=False)
def lire_historique(_chemin: str, mtime: float) -> pd.DataFrame:
    """Relu seulement quand le fichier change (mtime dans la clé du cache).
    Les scores sont recalculés depuis les mesures (fiable même si l'Excel a été retouché)."""
    df = pd.read_excel(_chemin).reindex(columns=COLONNES)
    for nom, groupe in SCORES.items():
        plafonne = sum(df[f"{a}_XA"].clip(upper=n) for a, n in groupe.items())
        df[nom] = (plafonne / sum(groupe.values()) * 100).round()  # NaN si une mesure manque
    return df


def stockage_persistant() -> bool:
    """Version navigateur : True si les données survivent à la fermeture de la page."""
    config = DOSSIER / "config_web.json"
    return config.exists() and json.loads(config.read_text()).get("persistant", False)


# ------------------------------------------------------------------ Visuels
@st.cache_resource
def images() -> dict[str, str]:
    """Miniatures WebP (~4 Ko) intégrées en data URI : aucune requête réseau."""
    return {p.stem: "data:image/webp;base64," + base64.b64encode(p.read_bytes()).decode()
            for p in IMAGES.glob("*.webp")}


@st.cache_resource
def css() -> str:
    return (DOSSIER / "style.css").read_text(encoding="utf-8")


POLICE = "-apple-system, BlinkMacSystemFont, 'SF Pro Text', system-ui, 'Segoe UI', Roboto, sans-serif"


def svg_img(svg: str, classe: str, alt: str) -> str:
    """st.html filtre les <svg> : on les passe en image (data URI), styles intégrés."""
    data = base64.b64encode(svg.encode()).decode()
    return f'<img class="{classe}" src="data:image/svg+xml;base64,{data}" alt="{alt}"/>'


def radar_svg(axes: list[str], offset: float, valeurs: dict, normes: dict) -> str:
    """Radar SVG : grille 25-100 %, contour de la norme, polygone des scores,
    points colorés selon la gravité de chaque articulation."""
    W, H, cx, cy, R = 300, 266, 150, 128, 84
    n = len(axes)
    angles = [math.radians(offset + 360 * i / n) for i in range(n)]

    def pt(a: float, r: float) -> tuple[float, float]:
        return cx + r * math.cos(a), cy - r * math.sin(a)

    def poly(rayons: list[float]) -> str:
        return " ".join(f"{x:.1f},{y:.1f}" for x, y in (pt(a, r) for a, r in zip(angles, rayons)))

    scores = [score_articulation(valeurs[a], normes[a]) for a in axes]
    groupe = score_groupe(valeurs, normes)
    _, _, couleur = gravite(groupe)
    if groupe is None:
        couleur = "#0071e3" if any(s is not None for s in scores) else "#c7c7cc"

    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
           f'font-family="{POLICE}">']
    for k in (0.25, 0.5, 0.75):
        svg.append(f'<polygon points="{poly([R * k] * n)}" fill="none" stroke="#e5e5ea"/>')
    for a in angles:
        x, y = pt(a, R)
        svg.append(f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" stroke="#e5e5ea"/>')
    svg.append(f'<polygon points="{poly([R] * n)}" fill="none" stroke="#aeaeb2" stroke-width="1.2" '
               'stroke-dasharray="3 3"/>')
    if any(s is not None for s in scores):
        svg.append(f'<polygon points="{poly([R * (s or 0) / 100 for s in scores])}" '
                   f'fill="{couleur}" fill-opacity=".16" stroke="{couleur}" stroke-width="2" '
                   'stroke-linejoin="round"/>')
    for a, art, s in zip(angles, axes, scores):
        _, texte, fond = gravite(s)
        if s is not None:
            x, y = pt(a, R * s / 100)
            svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="{fond}" stroke="#fff" '
                       f'stroke-width="1.5"><title>{art} : {s} %</title></circle>')
        lx, ly = pt(a, R + 18)
        ancre = "middle" if abs(math.cos(a)) < 0.3 else ("start" if math.cos(a) > 0 else "end")
        ly += 4 if math.sin(a) < -0.3 else (-6 if math.sin(a) > 0.3 else 0)
        svg.append(f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{ancre}" font-size="15" '
                   f'font-weight="500" fill="#1d1d1f">{art}'
                   f'<tspan x="{lx:.1f}" dy="17" font-size="14" font-weight="650" fill="{texte}">'
                   f'{"—" if s is None else f"{s} %"}</tspan></text>')
    svg.append("</svg>")
    texte_alt = ", ".join(f"{a} {'—' if s is None else f'{s} %'}" for a, s in zip(axes, scores))
    return svg_img("".join(svg), "radar", f"Radar : {texte_alt}")


def jauge_svg(score: int | None, manquantes: list[str]) -> str:
    libelle, texte, fond = gravite(score)
    r, c = 62, 2 * math.pi * 62
    rempli = 0 if score is None else c * score / 100
    valeur = "—" if score is None else (
        f'{score}<tspan font-size="18" font-weight="600" fill="#6e6e73" dy="-17">%</tspan>')
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 160 160" font-family="{POLICE}">
      <circle cx="80" cy="80" r="{r}" fill="none" stroke="#e8e8ed" stroke-width="12"/>
      {"" if not rempli else f'''<circle cx="80" cy="80" r="{r}" fill="none" stroke="{fond}" stroke-width="12"
              stroke-linecap="round" stroke-dasharray="{rempli:.1f} {c:.1f}" transform="rotate(-90 80 80)"/>'''}
      <text x="80" y="94" text-anchor="middle" font-size="40" font-weight="700" letter-spacing="-1.5"
            fill="#1d1d1f">{valeur}</text></svg>"""
    return f"""{svg_img(svg, "jauge", f"Score global : {'—' if score is None else f'{score} %'}")}
    <div class="jauge-libelle" style="color:{texte}" title="{", ".join(manquantes)}">{libelle if score is not None
        else ("À compléter : " + ", ".join(manquantes)) if len(manquantes) < len(NORMES)
        else "En attente des mesures"}</div>"""


def puce_score(titre: str, score: int | None) -> str:
    _, texte, fond = gravite(score)
    return (f'<div class="puce"><span class="point" style="background:{fond}"></span>'
            f'{titre}<b style="color:{texte}">{"—" if score is None else f"{score} %"}</b></div>')


LEGENDE = '<div class="legende">' + "".join(
    f'<span><i style="background:{fond}"></i>{lib} {"≥ " + str(s) if s else "< 50"}</span>'
    for s, lib, _, fond in SEUILS) + "</div>"


# --------------------------------------------------------------------- Saisie
def reset() -> None:
    st.session_state["nom"] = ""
    for art in NORMES:
        st.session_state[art] = None


def carte_membre(titre: str, normes: dict, radar: tuple[list[str], float], cle: str) -> dict:
    """Carte d'un membre : une colonne par articulation (image, norme, saisie, score) + radar."""
    imgs = images()
    with st.container(key=f"carte_{cle}"):
        entete = st.empty()
        cols = st.columns([1, 1, 1, 1, 1.9], gap="small")
        valeurs = {}
        for col, (art, norme) in zip(cols, normes.items()):
            with col:
                st.html(f'<div class="articulation"><img src="{imgs.get(art, "")}" alt="{art}" '
                        f'title="{art}" width="54" height="120" decoding="async"/>'
                        f'<div class="norme">X<sub>N</sub> {norme}°</div></div>')
                valeurs[art] = st.number_input(art, min_value=0, max_value=360, step=1, value=None,
                                               key=art, placeholder="°",
                                               label_visibility="collapsed")
                s = score_articulation(valeurs[art], norme)
                _, texte, fond = gravite(s)
                st.html(f'<div class="score-art"><b style="color:{texte}">'
                        f'{"—" if s is None else f"{s} %"}</b>'
                        f'<div class="barre"><i style="width:{s or 0}%;background:{fond}"></i></div></div>')
        with cols[-1]:
            st.html(radar_svg(*radar, valeurs, normes))
        total = score_groupe(valeurs, normes)
        _, texte, _ = gravite(total)
        entete.html(f'<div class="carte-titre"><h3>{titre}</h3>'
                    f'<span style="color:{texte}">{"—" if total is None else f"{total} %"}</span></div>')
    return valeurs


@st.fragment
def zone_mesure() -> None:
    """Fragment : modifier une valeur ne redessine que cette zone (pas l'historique)."""
    gauche, droite = st.columns([1.05, 3], gap="large")

    # Panneau gauche : titre, patient, date, puis score global (rempli plus bas)
    with gauche, st.container(key="panneau"):
        st.html('<h1>eCXA</h1>'
                '<p class="sous-titre">Amplitudes actives, en % de la norme</p>')
        nom = st.text_input("Patient", key="nom", placeholder="Nom du patient")
        jour = st.date_input("Date", value=date.today(), format="DD/MM/YYYY")
        zone_score = st.container(key="carte_score")

    with droite:
        v_ms = carte_membre("Membre supérieur", MS, RADAR_MS, "ms")
        v_mi = carte_membre("Membre inférieur", MI, RADAR_MI, "mi")
    valeurs = v_ms | v_mi

    with zone_score:
        st.html(f'<div class="score-titre">eCX<sub>A</sub> global</div>'
                f'{jauge_svg(score_groupe(valeurs, NORMES), [a for a, v in valeurs.items() if v is None])}'
                f'<div class="puces">{puce_score("Membre supérieur", score_groupe(v_ms, MS))}'
                f'{puce_score("Membre inférieur", score_groupe(v_mi, MI))}</div>{LEGENDE}')
        b1, b2 = st.columns(2, gap="small")
        enregistrer = b1.button("Enregistrer", type="primary", use_container_width=True)
        b2.button("Réinitialiser", on_click=reset, use_container_width=True)
        if enregistrer:
            if not nom.strip():
                st.error("Indique le nom du patient avant d'enregistrer.")
            elif all(v is None for v in valeurs.values()):
                st.error("Aucune mesure saisie.")
            else:
                wb = openpyxl.load_workbook(FICHIER)
                ws = wb.active
                mettre_a_niveau(ws)
                ws.append([jour.strftime("%d/%m/%Y"), nom.strip(),
                           *(valeurs[a] for a in NORMES), *scores_ligne(valeurs)])
                for cellule in ws[ws.max_row][len(COLONNES):len(ENTETES)]:
                    cellule.number_format = FORMAT_PCT
                wb.save(FICHIER)
                st.session_state["message"] = f"Mesures de {nom.strip()} enregistrées"
                st.rerun()  # rafraîchit aussi l'historique


# ------------------------------------------------------------------------- Page
st.set_page_config(page_title="eCXA", page_icon="🦴", layout="wide")
st.html(f"<style>{css()}</style>")
init_fichier()
for k in NORMES:
    st.session_state.setdefault(k, None)
if msg := st.session_state.pop("message", None):
    st.toast(msg, icon=":material/check_circle:")

if NAVIGATEUR and not stockage_persistant():
    st.warning(
        "**Les enregistrements ne seront pas conservés après fermeture de la page** : "
        "ce navigateur bloque le stockage local pour un fichier ouvert depuis le disque. "
        "Télécharge `eCXA.xlsx` (en bas) avant de fermer, ou ouvre l'app via une adresse "
        "`http://localhost` / `https://` pour activer la sauvegarde automatique.",
        icon="⚠️",
    )

zone_mesure()

# --------------------------------------------------------------- Historique
st.divider()
df = lire_historique(str(FICHIER), FICHIER.stat().st_mtime)
st.subheader(f"Historique ({len(df)} enregistrement{'s' if len(df) > 1 else ''})")
if df.empty:
    st.caption("Aucune donnée enregistrée pour l'instant.")
else:
    pourcent = {c: st.column_config.ProgressColumn(c, min_value=0, max_value=100, format="%d %%")
                for c in SCORES}
    affiche = df.copy()
    mesures = [f"{a}_XA" for a in NORMES]
    affiche[mesures] = df[mesures].map(lambda v: "—" if pd.isna(v) else f"{v:.0f}")  # pas de « None »
    colonnes = pourcent | {m: st.column_config.TextColumn(m, alignment="right") for m in mesures}
    st.dataframe(affiche, hide_index=True, use_container_width=True, column_config=colonnes)
    st.download_button("Télécharger eCXA.xlsx", FICHIER.read_bytes(), "eCXA.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

with st.expander("Importer un eCXA.xlsx existant (remplace l'historique)"):
    if NAVIGATEUR:
        st.caption("Les données sont gardées dans ce navigateur, sur cet ordinateur. "
                   "Pense à télécharger le fichier Excel régulièrement pour en garder une copie.")
    fichier = st.file_uploader("Fichier eCXA.xlsx", type="xlsx")
    if fichier and st.button("Remplacer l'historique par ce fichier"):
        entetes = [c.value for c in openpyxl.load_workbook(fichier).active[1]]
        if entetes[:len(COLONNES)] != COLONNES:
            st.error(f"Colonnes inattendues. Attendu : {', '.join(COLONNES)}")
        else:
            wb = openpyxl.load_workbook(fichier)
            mettre_a_niveau(wb.active)  # ajoute les scores si le fichier est d'une ancienne version
            wb.save(FICHIER)
            st.rerun()
