import streamlit as st
import requests
import time
import os

# CONFIG -----------------------------------------------------------------------

st.set_page_config(
    page_title="JobLess",
    page_icon="🔍",
    layout="centered",
)


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


# API -----------------------------------------------------------------------------

API_URL = os.environ['BACKEND_API_URL']+"/analyze/"
TIMEOUT_SECONDES = 120 

def appeler_api(texte_offre: str):
    """
    Appelle l'API
    """
    params = {"desc_offre": texte_offre}
    
    try:

        response = requests.get(
            API_URL, 
            params=params,
            timeout=TIMEOUT_SECONDES)
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Erreur {response.status_code} : {response.text}")
            return None
            
    except Exception as e:
        st.error(f"Le serveur ne répond pas : {e}")
        return None
        

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

def afficher_resultats(resultat: dict):
    """Affiche le bandeau + les compétences détectées."""
    competences = resultat
    total       = len(competences)
    st.markdown("<hr class='section-sep'>", unsafe_allow_html=True)
    st.markdown(f"### {total} compétence{'s' if total > 1 else ''} détectée{'s' if total > 1 else ''}")
    render_resultats(competences)

def normaliser_categorie(cat):
    if not cat:
        return None

    cat = cat.lower()

    mapping = {
        "soft skill": "Soft Skill",
        "compétence numérique": "Compétence numérique",
        "competence numérique": "Compétence numérique",
        "compétence non numérique": "Compétence non numérique",
        "domaine - secteur": "Domaine / Secteur",
        "domaine / secteur": "Domaine / Secteur",
        "certification": "Certification / Formation",
    }

    return mapping.get(cat, None)  

def nettoyer_competences(data):
    clean = []

    for comp in data:
        label = comp.get("label")
        cat = normaliser_categorie(comp.get("categorie"))

        # On skip si catégorie invalide
        if not label or not cat:
            continue

        clean.append({
            "label": label,
            "categorie": cat,
            "details": comp.get("details")
        })

    return clean


# INTERFACE ----------------------------------------------------------------------

st.markdown('<p class="main-title">🔍 JobLess (version 1.1)</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitle"><span style="font-weight:600;">J</span>ob <span style="font-weight:600;">O</span>ffer <span style="font-weight:600;">B</span>reakdown with <span style="font-weight:600;">L</span>LM <span style="font-weight:600;">E</span>xtraction & <span style="font-weight:600;">S</span>kills <span style="font-weight:600;">S</span>orting</p>', unsafe_allow_html=True)

offre = st.text_area(
    "Collez votre offre d'emploi ici",
    height=220,
    placeholder="Ex : Nous recherchons un Data Scientist maîtrisant Python et SQL, avec des bonnes capacités de communications..."
)

col1, col2, col3 = st.columns([2, 1, 2])
with col2:
    analyser = st.button("Analyser →", use_container_width=True, type="primary")

# LOGIQUE ----------------------------------------------------------------------------------

if "resultat" not in st.session_state:
    st.session_state["resultat"] = None

if analyser:
    if not offre.strip():
        st.warning("Merci de coller une offre d'emploi avant d'analyser.")
    else:
        st.session_state["resultat"] = None

        with st.spinner("Analyse de l'offre..."):
            resultat = appeler_api(offre)

        if resultat is None:
            st.error("Impossible d'obtenir un résultat.")
        else:
            resultat_clean = nettoyer_competences(resultat)
            st.session_state["resultat"] = resultat_clean 

# AFFICHAGE DES RESULTATS  ------------------------------------------------------

if "resultat" in st.session_state and st.session_state["resultat"] is not None:
    afficher_resultats(st.session_state["resultat"])
