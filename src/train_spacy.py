import spacy
from spacy.tokens import DocBin
from sklearn.model_selection import train_test_split
from tqdm import tqdm

# On charge le modèle base pour le tokenizer (important d'avoir le même que pour l'entrainement)
# Si tu n'as pas téléchargé le TRF, utilise "fr_core_news_sm" ou "spacy.blank('fr')" temporairement
try:
    nlp = spacy.load("fr_dep_news_trf")
except:
    print("⚠️ Modèle TRF non trouvé, utilisation d'un modèle blank pour le tokenizer.")
    nlp = spacy.blank("fr")

def convert_to_spacy_binary(df, output_path):
    db = DocBin()
    
    # --- COMPTEURS ---
    stats = {
        "total_ents": 0,       # Nombre total d'entités qu'on essaie d'injecter
        "skipped_ents": 0,     # Nombre d'entités rejetées (alignement impossible)
        "total_docs": len(df), # Nombre total de documents
        "docs_with_skips": 0   # Nombre de documents ayant au moins 1 rejet
    }

    print(f"📦 Conversion de {len(df)} documents vers {output_path}...")

    for _, row in tqdm(df.iterrows(), total=len(df)):
        text = row['text']
        spans = row['ner_spans'] # Liste de tuples [(start, end, label), ...]
        
        doc = nlp.make_doc(text)
        ents = []
        
        doc_has_skip = False # Indicateur pour ce document précis
        
        for start, end, label in spans:
            stats["total_ents"] += 1
            
            # alignment_mode="contract" : Le span doit correspondre exactement aux frontières des tokens
            span = doc.char_span(start, end, label=label, alignment_mode="expand")
            
            if span is None:
                # ÉCHEC D'ALIGNEMENT
                stats["skipped_ents"] += 1
                doc_has_skip = True
                # Optionnel : décommenter pour voir les erreurs
                # print(f"Skip: '{text[start:end]}' dans doc débutant par '{text[:20]}...'")
            else:
                ents.append(span)
        
        if doc_has_skip:
            stats["docs_with_skips"] += 1
            
        try:
            # On utilise filter_spans pour gérer les chevauchements éventuels qui resteraient
            doc.ents = spacy.util.filter_spans(ents)
            db.add(doc)
        except Exception as e:
            print(f"❌ Erreur critique sur un doc : {e}")

    # Sauvegarde
    db.to_disk(output_path)
    
    # --- RAPPORT D'ALIGNEMENT ---
    pct_ents_skipped = (stats['skipped_ents'] / stats['total_ents']) if stats['total_ents'] > 0 else 0
    pct_docs_impacted = (stats['docs_with_skips'] / stats['total_docs']) if stats['total_docs'] > 0 else 0
    
    print(f"\n📊 RAPPORT D'ALIGNEMENT SPACY ({output_path}) :")
    print(f"=================================================")
    print(f"🟢 Entités valides      : {stats['total_ents'] - stats['skipped_ents']}")
    print(f"🔴 Entités skippées     : {stats['skipped_ents']} / {stats['total_ents']} ({pct_ents_skipped:.2%})")
    print(f"-------------------------------------------------")
    print(f"📄 Documents traités    : {stats['total_docs']}")
    print(f"⚠️ Docs avec skips      : {stats['docs_with_skips']} ({pct_docs_impacted:.2%})")
    print(f"✅ Fichier sauvegardé   : {output_path}")
    print(f"=================================================\n")

# --- UTILISATION ---

# 1. Split Train / Dev
train_df, dev_df = train_test_split(df_labeled_all_to_skill, test_size=0.2, random_state=42)

# 2. Génération des fichiers avec le rapport
convert_to_spacy_binary(train_df, "train_all_to_skill.spacy")
convert_to_spacy_binary(dev_df, "dev_all_to_skill.spacy")