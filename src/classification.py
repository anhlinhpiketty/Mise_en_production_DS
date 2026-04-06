from bs4 import BeautifulSoup

import duckdb

import llm



def normalize(text : str) -> str:
    if not isinstance(text, str):
        return ""

    text = html.unescape(text)
    soup = BeautifulSoup(text, "html.parser")

    text = soup.get_text(separator=" ")

    series.fillna("")
            .map(self.strip_html)
            .str.replace(r"\\[a-zA-Z]+", " ", regex=True)
            .str.replace(r"[\x00-\x1F\x7F]", " ", regex=True)
            .str.lower()
            .str.replace(r"[^\w\s]", " ", regex=True)
            .str.replace(r"\s+", " ", regex=True)
            .str.strip()
    return normalized_text
           

def classify(skills : List[str]) -> List[dict]:

    if not isinstance(text, List[str]):
        return []

    output = classify_from_history(skills)
    if output == None:
        output = classify_from_llm(skills)

    return output

def classify_from_llm(skills : List[str]) -> List[dict]:
    
    return None

def classify_from_history(skill : List[str]) -> List[dict]:
    con = load_classif_history()
    output = []
    for skill in skills
        query = f"""
            SELECT 
                num.original
                num.cat
                num.entrée
                theme.cat
                niv.cat
                ia.cat
            FROM classif_history
            WHERE normalize(num.original) = {normalize(skill)}
        """
        result = con.sql(query).df()

        output.append({
            "label": result['num.entrée'],
            "categorie": result['num.cat'],
            "details": None if result['num.cat'] != 'Compétence numérique' else {'thematique' : result['theme.cat'], 'niveau' : result['niv.cat'], 'categorie_ia' : result['ia.cat']}
        })
    
    return output


def load_classif_history():
    con = duckdb.connect()

    # La table full join de toutes les classifications (num, theme, niv, ia)
    con.sql(f"""
        CREATE classif_history
            
        FROM read_parquet({})
        JOIN 
        """  
    )

    return con