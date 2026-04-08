import streamlit as st
import requests
import time

# CONFIG -----------------------------------------------------------------------

st.set_page_config(
    page_title="?? No idea :)",
    page_icon="🔍",
    layout="centered",
)

# Timeout en secondes au-delà duquel on propose le parachute
# A modifier, j'ai été vraiment pas patiente
TIMEOUT_SECONDES = 5

# STYLE ------------------------------------------------------------------------

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

h1, h2, h3 {
    font-family: 'DM Sans', sans-serif;
    font-weight: 700;
}

/* Titre principal */
.main-title {
    font-family: 'DM Sans', sans-serif;
    font-size: 3.2rem;   
    font-weight: 800;  
    color: #1a1a2e;
    margin-bottom: 0.1rem;
    letter-spacing: -0.02em; 
}
.subtitle {
    color: #6b7280;
    font-size: 1rem;
    margin-bottom: 2rem;
}

/* Bandeaux parachute */
.bandeau-parachute {
    background: #fffbeb;
    border-radius: 12px;
    padding: 1rem 1.2rem;
    margin-bottom: 1.2rem;
    color: #78350f;
    font-size: 0.9rem;
}

.bandeau-indispo {
    background: #fef2f2;
    border-radius: 12px;
    padding: 1rem 1.2rem;
    margin-bottom: 1.2rem;
    color: #7f1d1d;
    font-size: 0.9rem;
}

/* Carte de catégorie */
.categorie-card {
    background: #f8f9ff;
    border-left: 4px solid #4f46e5;
    border-radius: 0 12px 12px 0;
    padding: 1rem 1.2rem;
    margin-bottom: 1rem;
}

.categorie-title {
    font-weight: 600;
    font-size: 0.85rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #4f46e5;
    margin-bottom: 0.6rem;
}

/* Tags */
.tags-container {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
}

.tag {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 999px;
    font-size: 0.85rem;
    font-weight: 500;
}

/* Couleurs par catégorie */
.tag-soft       { background: #fce7f3; color: #be185d; }
.tag-numerique  { background: #ede9fe; color: #6d28d9; }
.tag-non-num    { background: #d1fae5; color: #065f46; }
.tag-domaine    { background: #fef3c7; color: #92400e; }
.tag-certif     { background: #dbeafe; color: #1e40af; }

/* Détails compétence numérique */
.detail-badge {
    display: inline-block;
    background: #f3f0ff;
    border: 1px solid #c4b5fd;
    color: #5b21b6;
    border-radius: 6px;
    font-size: 0.75rem;
    padding: 2px 8px;
    margin-left: 6px;
    vertical-align: middle;
}

.niveau-avance    { background: #fef9c3; border-color: #fbbf24; color: #78350f; }
.niveau-inter     { background: #e0f2fe; border-color: #38bdf8; color: #0c4a6e; }
.niveau-basique   { background: #f0fdf4; border-color: #86efac; color: #14532d; }

/* Bloc compétence numérique détaillée */
.num-item {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    padding: 0.7rem 1rem;
    margin-bottom: 0.5rem;
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 6px;
}

.num-label {
    font-weight: 600;
    font-size: 0.9rem;
    color: #1a1a2e;
}

/* Séparateur section */
.section-sep {
    border: none;
    border-top: 1px solid #e5e7eb;
    margin: 1.5rem 0;
}

/* Zone de texte */
.stTextArea > div:focus-within {
    border-color: #1d4ed8;
}

/* Bouton Analyse*/
.stButton > button {
    background-color: #3b82f6;  
    color: white;
    border: none;
}

.stButton > button:hover {
    background-color: #1d4ed8;  
    color: white;
}

</style>
""", unsafe_allow_html=True)

# MOCK API (à remplacer par le vrai appel quand l'API sera prête) -----------------
# Ici on peut simuler plusieurs scénarios (dont la lenteur d'execution)
# Si c'est trop lent on utilise le modèle parachute (pas sûre de comment faire le pop up)


# Réponses fictives
COMPETENCES_MOCK = [
    {
        "label": "Python",
        "categorie": "Compétence numérique",
        "details": {"thematique": "Données, Analytics & IA", "niveau": "Avancé", "categorie_ia": "Machine Learning"}
    },
    {
        "label": "SQL",
        "categorie": "Compétence numérique",
        "details": {"thematique": "Données, Analytics & IA", "niveau": "Intermédiaire", "categorie_ia": None}
    },
    {
        "label": "Docker",
        "categorie": "Compétence numérique",
        "details": {"thematique": "Infrastructure, Systèmes & Réseaux", "niveau": "Basique", "categorie_ia": None}
    },
    {"label": "Communication",        "categorie": "Soft Skill",               "details": None},
    {"label": "Gestion de projet",    "categorie": "Soft Skill",               "details": None},
    {"label": "Rédaction de rapports","categorie": "Compétence non numérique", "details": None},
    {"label": "Finance de marché",    "categorie": "Domaine / Secteur",        "details": None},
    {"label": "Whatever diploma", "categorie": "Certification / Formation", "details": None},
]

# Changer cette valeur pour tester les différents scénarios :
# "ok" : API répond normalement
# "lent" : API dépasse le timeout
# "indisponible" : LLMLab down
SCENARIO_MOCK = "lent"

# API principale où on utilise le "bon" LLM 
def mock_api_principale(texte_offre: str) -> dict:
    """
    Simule l'API principale du LLM.

    Pour l'instant : retourne une classification fictive.

    Pas sûre du format JSON sur lequel on se calquera mais en gros je fais :
    label = la compétence brute extraite du texte
    categorie = le résultat de la 1ère classification LLM
    details = les résultats des classifications suivantes (seulement si numérique)

    Je simule le fait que le modèle puisse prendre trop de temps aussi
 
    À remplacer plus tard avec les réponses des API principales/de secours
    """
    if SCENARIO_MOCK == "ok":
        time.sleep(1) # On s'arrête pendant 1 secondes
        return {"competences": COMPETENCES_MOCK}
 
    elif SCENARIO_MOCK == "lent":
        time.sleep(TIMEOUT_SECONDES + 5) # On s'arrête au delà du temps accepté
        return {"competences": COMPETENCES_MOCK}
 
    elif SCENARIO_MOCK == "indisponible":
        raise ConnectionError("API principale indisponible")
 
# API parachute
def mock_api_parachute(texte_offre: str) -> dict:
    """
    Simule le LLM de secours (plus rapide).
 
    À remplacer plus tard par :
        response = requests.post(
            "http://<url-api-parachute>/analyze",
            json={"texte": texte_offre},
            timeout=TIMEOUT_SECONDES
        )
        return response.json()
    """
    time.sleep(1)
    return {"competences": COMPETENCES_MOCK}


# AFFICHAGE ---------------------------------------------------------------------

CATEGORIE_CONFIG = {
    "Soft Skill":               {"css": "tag-soft",      "emoji": "💬"},
    "Compétence numérique":     {"css": "tag-numerique", "emoji": "💻"},
    "Compétence non numérique": {"css": "tag-non-num",   "emoji": "🛠️"},
    "Domaine / Secteur":        {"css": "tag-domaine",   "emoji": "🌐"},
    "Certification / Formation":{"css": "tag-certif",    "emoji": "🎓"},
}

NIVEAU_CSS = {
    "Avancé":        "niveau-avance",
    "Intermédiaire": "niveau-inter",
    "Basique":       "niveau-basique",
}

def render_resultats(competences: list):
    # Grouper par catégorie
    groupes = {}
    for comp in competences:
        cat = comp["categorie"]
        groupes.setdefault(cat, []).append(comp)

    for cat, comps in groupes.items():
        cfg = CATEGORIE_CONFIG.get(cat, {"css": "tag-soft", "emoji": "📌"})
        emoji = cfg["emoji"]

        st.markdown(f"""
        <div class="categorie-card">
            <div class="categorie-title">{emoji} {cat} ({len(comps)})</div>
        """, unsafe_allow_html=True)

        if cat == "Compétence numérique":
            # Affichage détaillé pour les compétences numériques
            for comp in comps:
                d = comp.get("details") or {}
                niveau_css = NIVEAU_CSS.get(d.get("niveau", ""), "")
                niveau_html = f'<span class="detail-badge {niveau_css}">{d["niveau"]}</span>' if d.get("niveau") else ""
                thema_html  = f'<span class="detail-badge">{d["thematique"]}</span>' if d.get("thematique") else ""
                ia_html     = f'<span class="detail-badge">🤖 {d["categorie_ia"]}</span>' if d.get("categorie_ia") else ""

                st.markdown(f"""
                <div class="num-item">
                    <span class="num-label">{comp["label"]}</span>
                    {thema_html}{niveau_html}{ia_html}
                </div>
                """, unsafe_allow_html=True)
        else:
            # Tags simples pour les autres catégories
            tags_html = "".join(
                f'<span class="tag {cfg["css"]}">{c["label"]}</span>'
                for c in comps
            )
            st.markdown(f'<div class="tags-container">{tags_html}</div>', unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

def render_bandeau(mode: str):
    """Affiche un bandeau d'avertissement selon le modèle utilisé."""
    if mode == "parachute_timeout":
        st.markdown("""
        <div class="bandeau-parachute">
             <strong>Modèle de secours utilisé</strong> — L'API principale a mis trop de temps.
        </div>
        """, unsafe_allow_html=True)
    elif mode == "parachute_indispo":
        st.markdown("""
        <div class="bandeau-indispo">
             <strong>Modèle de secours utilisé</strong> — L'API principale est indisponible.
        </div>
        """, unsafe_allow_html=True)

def afficher_resultats(resultat: dict, mode: str):
    """Affiche le bandeau + les compétences détectées."""
    competences = resultat.get("competences", [])
    total       = len(competences)
    st.markdown("<hr class='section-sep'>", unsafe_allow_html=True)
    if mode != "ok":
        render_bandeau(mode)
    st.markdown(f"### {total} compétence{'s' if total > 1 else ''} détectée{'s' if total > 1 else ''}")
    render_resultats(competences)


# INTERFACE ----------------------------------------------------------------------

st.markdown('<p class="main-title">I have no name idea</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Diagnostic des compétences d\'une offre d\'emploi</p>', unsafe_allow_html=True)

offre = st.text_area(
    "Collez votre offre d'emploi ici",
    height=220,
    placeholder="Ex : Nous recherchons un Data Scientist maîtrisant Python et SQL, avec des bonnes capacités de communications..."
)

col1, col2, col3 = st.columns([2, 1, 2])
with col2:
    analyser = st.button("Analyser →", use_container_width=True, type="primary")


# On utilise st.session_state pour mémoriser l'état entre deux exécutions du script.
# Streamlit réexécute tout le fichier à chaque interaction (clic, saisie...),
# donc sans session_state, on perdrait l'information d'un tour à l'autre.
#
# États possibles dans session_state :
#   "attente_choix" (bool) : True quand on attend que l'utilisateur choisisse
#   "offre_en_cours" (str) : l'offre mémorisée pendant qu'on attend le choix
#   "resultat" (dict)      :  résultat final à afficher
#   "mode" (str)           : "ok" | "parachute_timeout" | "parachute_indispo"

# Initialisation des variables de session si elles n'existent pas encore
if "attente_choix" not in st.session_state:
    st.session_state["attente_choix"] = False
if "resultat" not in st.session_state:
    st.session_state["resultat"] = None
if "mode" not in st.session_state:
    st.session_state["mode"] = "ok"
 
# Quand on clique sur "Analyser"
if analyser:
    if not offre.strip():
        st.warning("Merci de coller une offre d'emploi avant d'analyser.")
    else:
        # On remet l'état à zéro pour une nouvelle analyse
        st.session_state["resultat"]     = None
        st.session_state["attente_choix"] = False
        st.session_state["mode"]         = "ok"
 
        try:
            with st.spinner("Analyse avec le modèle principal..."):
                debut    = time.time()
                resultat = mock_api_principale(offre)
                duree    = time.time() - debut
 
            if duree > TIMEOUT_SECONDES:
                # Trop lent : on mémorise l'offre et on passe en mode "attente choix"
                st.session_state["attente_choix"]  = True
                st.session_state["offre_en_cours"] = offre
            else:
                # OK : on mémorise le résultat directement
                st.session_state["resultat"] = resultat
                st.session_state["mode"]     = "ok"
 
        except ConnectionError:
            # Indisponible donc parachute automatique
            st.toast("Indisponible : passage au modèle de secours")
            with st.spinner("Basculement sur le modèle de secours..."):
                st.session_state["resultat"] = mock_api_parachute(offre)
                st.session_state["mode"]     = "parachute_indispo"
 
# Pop-up de choix si on est en attente 
if st.session_state["attente_choix"]:
    st.warning(f"L'analyse prend plus de {TIMEOUT_SECONDES} secondes.")
    col_a, col_b = st.columns([1, 1])
    _, col_a, col_b, _ = st.columns([1, 1, 1, 1])
    spinner_placeholder = st.empty() 

    with col_a:
        if st.button("Continuer à attendre"):
            with spinner_placeholder, st.spinner("En attente de l'API principale..."):
                st.session_state["resultat"]      = mock_api_principale(st.session_state["offre_en_cours"])
                st.session_state["mode"]          = "ok"
                st.session_state["attente_choix"] = False
 
    with col_b:
        if st.button("Utiliser un modèle de secours"):
            with spinner_placeholder, st.spinner("Basculement sur le modèle de secours..."):
                st.session_state["resultat"]      = mock_api_parachute(st.session_state["offre_en_cours"])
                st.session_state["mode"]          = "parachute_timeout"
                st.session_state["attente_choix"] = False
 
# Affichage du résultat final 
if st.session_state["resultat"]:
    afficher_resultats(st.session_state["resultat"], st.session_state["mode"])