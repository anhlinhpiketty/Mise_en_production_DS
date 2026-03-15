import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv
import llm_utils
import re


def load_config(config_path: Path) -> dict:
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as f:
        config = json.load(f)

    required_keys = [
        "MODEL_NAME",
        "INPUT_CSV",
        "INPUT_COLUMN",
        "BATCH_SIZE",
        "RETRY_LIMIT",
        "BASE_URL",
        "SYSTEM_PROMPT",
    ]

    missing = [k for k in required_keys if k not in config]
    if missing:
        raise ValueError(f"Missing required config keys: {missing}")

    return config


def build_output_filename(config: dict) -> str:
    input_path = Path(config["INPUT_CSV"])
    input_filename = input_path.name  # ex: competences.csv

    model_name = config["MODEL_NAME"]

    # Nettoyage pour nom de fichier (remplace caractères invalides)
    safe_model_name = re.sub(r"[^\w\-\.]", "_", model_name)

    if config.get("TASK"):
        output_filename = f"{config.get("TASK")}_{safe_model_name}_{input_filename}"
    else:
        output_filename = f"{safe_model_name}_{input_filename}"

    # Même dossier que INPUT_CSV
    output_path = input_path.parent / output_filename

    return str(output_path)


def inject_api_key(config: dict) -> dict:
    api_key = os.getenv("LLM_API_KEY")
    if not api_key:
        raise ValueError(
            "LLM_API_KEY not found. Define it in a .env file or environment variable."
        )

    config["API_KEY"] = api_key
    return config


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run LLM inference using a JSON configuration file."
    )

    parser.add_argument(
        "config_path",
        type=Path,
        help="Path to config_llm_infer.json",
    )

    parser.add_argument(
        "--override-output",
        type=str,
        default=None,
        help="Override OUTPUT_CSV from config file",
    )

    return parser.parse_args()


def main():
    load_dotenv()  # charge automatiquement .env

    args = parse_args()
    config = load_config(args.config_path)

    if args.override_output:
        config["OUTPUT_CSV"] = args.override_output
    else:
        config["OUTPUT_CSV"] = build_output_filename(config)

    config = inject_api_key(config)

    llm_process = llm_utils.LLMProcessor(config)
    llm_process.run()


if __name__ == "__main__":
    main()