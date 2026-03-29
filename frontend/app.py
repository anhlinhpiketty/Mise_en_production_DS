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
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Sans:wght@400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

h1, h2, h3 {
    font-family: 'DM Serif Display', serif;
}

/* Titre principal */
.main-title {
    font-family: 'DM Serif Display', serif;
    font-size: 2.4rem;
    color: #1a1a2e;
    margin-bottom: 0.2rem;
}

.subtitle {
    color: #6b7280;
    font-size: 1rem;
    margin-bottom: 2rem;
}

/* Bandeaux parachute */
.bandeau-parachute {
    background: #fffbeb;
    border: 1px solid #fbbf24;
    border-radius: 12px;
    padding: 1rem 1.2rem;
    margin-bottom: 1.2rem;
    color: #78350f;
    font-size: 0.9rem;
}

.bandeau-indispo {
    background: #fef2f2;
    border: 1px solid #ef4444;
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
    {"label": "AWS Certified Solutions Architect", "categorie": "Certification / Formation", "details": None},
]

# Changer cette valeur pour tester les différents scénarios :
# "ok" : API répond normalement
# "lent" : API dépasse le timeout
# "indisponible" : LLMLab down
SCENARIO_MOCK = "ok"

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

# INTERFACE ----------------------------------------------------------------------

st.markdown('<p class="main-title">I have no name idea</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Diagnostic des compétences d\'une offre d\'emploi</p>', unsafe_allow_html=True)

offre = st.text_area(
    "Collez votre offre d'emploi ici",
    height=220,
    placeholder="Ex : Nous recherchons un Data Scientist maîtrisant la checklist des bonnes pratiques de développement, avec des bonnes capacités de communications..."
)

col1, col2, col3 = st.columns([2, 1, 2])
with col2:
    analyser = st.button("Analyser →", use_container_width=True, type="primary")

if analyser:
    if not offre.strip():
        st.warning("Merci de coller une offre d'emploi avant d'analyser.")
    else:
        resultat = None
        mode = "ok" 
        
        # --- Tentative API principale ---
        try:
            with st.spinner("Analyse avec le modèle principal..."):
                debut = time.time()
                resultat = mock_api_principale(offre)
                duree = time.time() - debut

                # --- Vérification si trop lent ---
                if duree > TIMEOUT_SECONDES:
                    st.toast("Trop long : passage au modèle de secours")
                    mode = "parachute_timeout"
                    resultat = mock_api_parachute(offre)

        except ConnectionError:
            # --- Gestion si LLM indispo ---
            st.toast("Indisponible : passage au modèle de secours")
            mode = "parachute_indispo"
            resultat = mock_api_parachute(offre)

        # --- Affichage des résultats ---
        if resultat:
            competences = resultat.get("competences", [])
            total = len(competences)

            st.markdown("<hr class='section-sep'>", unsafe_allow_html=True)
            
            # Affiche le bandeau si on n'est pas en mode "ok"
            if mode != "ok":
                render_bandeau(mode)
                
            st.markdown(f"### {total} compétence{'s' if total > 1 else ''} détectée{'s' if total > 1 else ''}")
            render_resultats(competences)