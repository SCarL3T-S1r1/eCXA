import numpy as np
import matplotlib.pyplot as plt

def radar_plot_eCXA_MI(values) :
    # Données d'exemple pour le radar plot
    labels = ['Genou', 'Hanche', 'Cheville']  # 4 axes pour un carré/losange

    # Nombre de variables
    num_vars = len(labels)

    # Calculer les angles pour chaque axe (90° d'écart pour chaque angle)
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()

    # Fermer le graphique pour former un polygone fermé
    values += values[:1]
    angles += angles[:1]

    # Création de la figure et de l'axe polaire
    fig, ax = plt.subplots(figsize=(1, 1), subplot_kw=dict(polar=True))
    fig.subplots_adjust(top=1)
    
    # Tourner le graphique de 45° (π/4 radians)
    ax.set_theta_offset(0.523599)

    # Tracer les lignes de grille droites (au lieu de cercles)
    # Les lignes droites pour chaque niveau radial
    radial_levels = [0.2, 0.4, 0.6, 0.8, 1.0]  # Ajuster en fonction de l'échelle des valeurs
    for level in radial_levels:
        ax.plot(angles, [level] * len(angles), color="gray", linewidth=0.2, linestyle="--")

    # Tracer le contour du radar plot
    ax.fill(angles, values, color='blue', alpha=0.25)
    ax.plot(angles, values, color='blue', linewidth=0.5)

    # Ajouter les labels pour chaque axe
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels,fontsize=4)
    ax.set_yticks([])  # Supprimer les graduations de l'axe y

    # Supprimer le contour du plot
    ax.spines['polar'].set_visible(False)
    
    # Ajuster l'offset radial des labels
    for label, angle in zip(ax.get_xticklabels(), angles):
        label.set_horizontalalignment('center')
        label.set_y(0.45)  # 1.1 éloigne les labels, réduire pour les rapprocher
    
    return fig