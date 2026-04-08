"""API pour l'extraction et classication de compétence à partir d'offres d'emploi"""

from fastapi import FastAPI
from src.classification import classify
from src.extraction import extract_skills_from


app = FastAPI(
    title="Extraction et classification de compétences à partir d'offres d'emploi",
    description="<br>Une version par API pour faciliter la réutilisation du modèle 🚀"
    + '<br>',
)


@app.get("/", tags=["Welcome"])
def show_welcome_page():
    """
    Show welcome page with model name and version.
    """

    return {
        "Message": "API d'extraction et de classification de compétences issues d'offres d'emploi",
        "Model_name": "NER_LLM_JOCAS",
        "Model_version": "0.1",
    }


@app.get("/analyze", tags=["Analyze"])
async def analyze(
   desc_offre: str = ""
) -> list[dict]:
    """ """
    skills = extract_skills_from(desc_offre)
    classification = classify(skills)
    return classification