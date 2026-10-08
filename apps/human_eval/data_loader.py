import csv
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"

RECALLS_CSV = DATA_DIR / "recalls_sample.csv"
EXTRACTION_CSVS = [
    DATA_DIR / "recalls_extracted_gemma4_e2b.csv",
    DATA_DIR / "recalls_extracted_gpt-5.4-nano.csv",
]

# Only the first repeat of each model's extractions is evaluated
REPEAT_ID = "1"

_recalls: dict[int, str] | None = None
_items: dict[tuple[int, str], dict] | None = None
_model_names: list[str] | None = None


def _load():
    global _recalls, _items, _model_names
    if _items is not None:
        return

    recalls = {}
    with open(RECALLS_CSV, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            recalls[int(row["document_id"])] = row["defect_description"]

    items = {}
    model_names = []
    for path in EXTRACTION_CSVS:
        with open(path, newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                if row["repeat_id"] != REPEAT_ID:
                    continue
                doc_id = int(row["document_id"])
                model = row["model_name"]
                if model not in model_names:
                    model_names.append(model)
                items[(doc_id, model)] = {
                    "document_id": doc_id,
                    "model_name": model,
                    "manufacturer": row["manufacturer"],
                    "models": row["models"],
                    "model_years": row["model_years"],
                }

    _recalls = recalls
    _items = items
    _model_names = model_names


def get_recall_text(document_id: int) -> str | None:
    _load()
    return _recalls.get(document_id)


def get_item(document_id: int, model_name: str) -> dict | None:
    _load()
    return _items.get((document_id, model_name))


def get_document_ids() -> list[int]:
    _load()
    return sorted(_recalls.keys())


def get_model_names() -> list[str]:
    _load()
    return list(_model_names)


def get_total_items() -> int:
    _load()
    return len(_items)
