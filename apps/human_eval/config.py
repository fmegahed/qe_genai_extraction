import os

# --- Environment variables ---
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/human_eval")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "changeme")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

# --- Extraction fields rated by reviewers ---
# display: "verbatim" shows the raw extracted string on one line;
# "list" splits on ";" into a bulleted list (multi-valued fields)
FIELDS = [
    {
        "key": "manufacturer",
        "label": "Manufacturer",
        "question": "Is the extracted manufacturer correct?",
        "display": "verbatim",
    },
    {
        "key": "models",
        "label": "Models",
        "question": "Are the extracted vehicle models correct?",
        "display": "list",
    },
    {
        "key": "model_years",
        "label": "Model Years",
        "question": "Are the extracted model years correct?",
        "display": "list",
    },
]

# --- 1-5 correctness anchors (adapted from the paper's evaluation scale) ---
CORRECTNESS_ANCHORS = {
    1: {
        "label": "Incorrect",
        "definition": "The extracted value is wrong, unsupported by the recall description, or clearly misrepresents it.",
    },
    2: {
        "label": "Mostly Incorrect",
        "definition": "A small amount of the extracted value is correct, but substantial errors or important omissions remain.",
    },
    3: {
        "label": "Partially Correct",
        "definition": "The extracted value mixes correct and incorrect information, or captures only part of what the recall description states.",
    },
    4: {
        "label": "Mostly Correct",
        "definition": "The extracted value is largely correct, with only minor errors, omissions, or imprecision.",
    },
    5: {
        "label": "Correct",
        "definition": "The extracted value is fully supported by the recall description, with no meaningful errors or omissions.",
    },
}
