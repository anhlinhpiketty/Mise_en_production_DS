"""
Module contenant les tests unitaires pour le système de classification.

Ce fichier permet de valider les fonctionnalités suivantes :
- Normalisation des compétences
- Chargement de l'historique de classification
- Classification basée sur l'historique (history)
- Classification via LLM (structure de données)
- Pipeline complet de bout en bout
"""

import sys
import traceback
import os
from src.llm import *
from src.classification import *
from src.classification import (_get_classif_history_connection)
from src.extraction import * 


def test_normalize_cases():
    """
    Teste la fonction `normalize` sur une série de données variées.

    Vérifie que la normalisation gère correctement :
    - Les différentes casse
    - Les entités HTML
    - Les balises HTML
    - Les espaces multiples
    - La ponctuation
    - Les formats LaTeX
    - Les valeurs non-sérieuses (None, int, vide)

    """
    cases = {
        "nominal":           ("Maîtrise d'Excel", "maîtrise d excel"),
        "html entities":     ("Comp&amp;eacute;tence", "compétence"),
        "balises html":      ("<b>Python</b> avancé", "python avancé"),
        "espaces multiples": ("  Python   avancé  ", "python avancé"),
        "ponctuation":       ("C++, SQL & NoSQL", "c sql nosql"),
        "latex":             (r"Algèbre \\textbf{linéaire}", "algèbre linéaire "),
        "None":              (None, ""),
        "int":               (42, ""),
        "chaîne vide":       ("", ""),
    }
    for name, (inp, expected) in cases.items():
        result = normalize(inp)
        assert result.strip() == expected.strip(), f"Erreur normalize: {name}, résultat : {result.strip()}, attendu : {expected.strip()}"


def test_load_history():
    """
    Vérifie la connexion à la base de données et l'intégrité de la table `classif_history`.

    Assure que :
    - La connexion est possible.
    - Les données existent.
    - Les colonnes attendues sont présentes.
    """
    con = _get_classif_history_connection()
    df = con.sql("SELECT * FROM classif_history LIMIT 5").df()
    assert len(df) > 0, "Aucune donnée trouvée dans la table d'historique."
    assert "num_cat" in df.columns, "La colonne 'num_cat' manque dans le résultat."


def test_classify_from_history():
    """
    Valide la capacité du système à classer des éléments en se référant à l'historique.

    Teste spécifiquement :
    - Tous les étiquettes présentes dans l'historique doivent revenir un résultat valide.
    - Une catégorie totalement inconnue (non présente dans l'historique) doit retourner None pour "categorie".
    """
    con = _get_classif_history_connection()
    sample = con.sql("""
        SELECT DISTINCT norm_label
        FROM classif_history
        LIMIT 2
    """).df()
    known = sample["norm_label"].tolist()
    unknown = ["Compétence totalement inconnue XYZ 999"]
    results = classify_from_history(known + unknown)
    assert results[-1]["categorie"] is None, "Le dernier élément (inconnu) doit avoir une catégorie None."
    assert all(r["categorie"] is not None for r in results[:-1]), "Tous les éléments connus doivent avoir une catégorie définie."


def test_llm_structure():
    """
    Valide la structure et le contenu du retour généré par la classification LLM.

    Vérifie :
    - Le nombre de résultats correspond au nombre d'inputs.
    - Chaque dictionnaire contient les clés : 'label', 'categorie', 'details'.
    - Si la catégorie est 'compétence numérique', 'details' doit contenir des sous-éléments.
    """
    skills = [
        "Utilisation de ChatGPT en entreprise",
        "Gestion du stress",
        "Développement API FastAPI"
    ]
    results = classify_from_llm(skills)
    
    assert len(results) == len(skills), "Le nombre de résultats ne correspond pas à la liste d'inputs."
    
    for r in results:
        assert "label" in r, "Claire 'label' manquante dans le résultat."
        assert "categorie" in r, "Claire 'categorie' manquante dans le résultat."
        assert "details" in r, "Claire 'details' manquante dans le résultat."
        
        if r["categorie"] == "compétence numérique":
            assert r["details"] is not None, "Details devraient être présentes pour 'compétence numérique'."
            assert "thematique" in r["details"], "Clair 'thematique' manquante dans details."
            assert "niveau" in r["details"], "Clair 'niveau' manquante dans details."
            assert "categorie_ia" in r["details"], "Clair 'categorie_ia' manquante dans details."
        else:
            assert r["details"] is None, "Details devraient être None pour d'autres catégories."


def test_full_pipeline():
    """
    Exécute un test d'intégration complet du pipeline de classification.

    Simule un scénario réel en :
    1. Récupérant une compétence de l'historique dans `classif_history`.
    2. Ajoutant de nouvelles compétences.
    3. Lançant la classification complète.
    4. Vérifiant que chaque compétence est assignée à une catégorie.
    """
    con = _get_classif_history_connection()
    known = con.sql("SELECT num_entree FROM classif_history LIMIT 1").df().iloc[0, 0]
    skills = [
        known,
        "Maîtrise de Notion pour la gestion de projets",
        "Communication interpersonnelle",
    ]
    results = classify(skills)
    assert len(results) == len(skills), "Nombre de résultats inattendu pour le pipeline complet."
    for r in results:
        assert r["categorie"] is not None, "Chaque compétence doit obtenir une catégorie dans le pipeline complet."


def run_test(name, func):
    """
    Éxécute une fonction de test et affiche le statut visuel.

    Args:
        name (str): Nom du test à afficher.
        func (Callable): Fonction de test à exécuter.

    Raises:
        SystemExit: Si une exception est levée, le script s'arrête.
    """
    try:
        func()
        print(f"✓ {name}")
    except Exception as e:
        print(f"✗ {name}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    """Boucle principale d'exécution de la batterie de tests. Exécute toutes les vérifications instantanément."""
    run_test("normalize", test_normalize_cases)
    run_test("load_history", test_load_history)
    run_test("classify_from_history", test_classify_from_history)
    run_test("llm_structure", test_llm_structure)
    run_test("full_pipeline", test_full_pipeline)
    print("\nTous les tests passent ✓")
