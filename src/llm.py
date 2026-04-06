import re
from openai import 
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = ""


def call_llm(self, competences: List[str], model_name, temperature, system_prompt) -> List[dict]:
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(competences, ensure_ascii=False)}
    ]

    client = create_client(
            api_key=os.environ["API_KEY"],
            base_url=BASE_URL
        )
    
    response = client.chat.completions.create(
        model=model_name,
        messages=messages,
        temperature=temperature,
    )

    text = response.choices[0].message.content

    # Extraction robuste des objets JSON
    json_blocks = re.findall(r'\{.*?\}', text, re.DOTALL)

    parsed = []
    for block in json_blocks:
        try:
            parsed.append(json.loads(block))
        except json.JSONDecodeError:
            print(f"JSON invalide ignoré : {block}")

    return parsed


def create_client(self, api_key: str, base_url: str):
    if base_url == "openai":
        return OpenAI(api_key=api_key)
    return OpenAI(api_key=api_key, base_url=base_url)