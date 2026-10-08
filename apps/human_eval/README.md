# Recall Extraction Human Evaluation

A FastAPI web app that captures expert human ratings of the correctness of LLM-extracted
structured data (manufacturer, vehicle models, model years) from 30 NHTSA vehicle-recall
defect descriptions. Two models are evaluated (gemma4:e2b and gpt-5.4-nano, first repeat
only), giving each reviewer 60 blinded extractions to rate on a 1-5 correctness scale.
Ratings feed the accuracy analysis in our paper "What Quality Engineers Need to Know
About Generative AI: Structured Data Extraction", to be submitted to *Quality Engineering*.

## Study design

- **Blinded**: reviewers never see which model produced an extraction; the admin CSV
  export unblinds.
- **Two balanced blocks per reviewer**: the 30 documents are randomly split 15/15;
  block 1 shows one half with model A and the other half with model B (shuffled),
  block 2 mirrors the assignment (shuffled independently). Every document appears once
  per block, a document's two extractions are never adjacent (including across the block
  seam), and each model is evenly represented in the fresh first half and the tired
  second half. Which model plays "A" is randomized per reviewer.
- **Fatigue reduction**: keyboard shortcuts (1-5 rate, Enter advances), autosave on
  every submit, resume across sessions, back navigation and a jump strip for revising,
  and a break interstitial at the halfway point.

## Running locally

```bash
# Docker Compose (recommended) - starts PostgreSQL 16 + FastAPI app
docker compose up --build
# App at http://localhost:8000, admin password: changeme

# Without Docker
pip install -r requirements.txt
export DATABASE_URL="postgresql://user:pass@localhost:5432/human_eval"
uvicorn main:app --reload --port 8000
```

## Usage

1. Log in at `/admin/login`.
2. Create a review link per reviewer (name + optional email). Each link gets its own
   randomized presentation order, fixed at creation.
3. Send each reviewer their link. Progress is tracked on the admin dashboard.
4. Download all ratings at `/admin/export` (long-format CSV: one row per reviewer x
   position x field, with document id, unblinded model name, block, and timestamps).

## Tests

```bash
pip install -r requirements-dev.txt
pytest tests
```

Covers the randomization balance guarantees, the submit/revise/resume flow, blinding,
the break interstitial, and the export format.

## Deployment (Railway)

Live at https://human-eval-production.up.railway.app (project `recall-human-eval`,
service `human-eval`). Deployed via Dockerfile; redeploy with
`railway up --service human-eval` from this directory. Required env vars:
`DATABASE_URL`, `ADMIN_PASSWORD`, `SECRET_KEY`, `BASE_URL` (no trailing slash).

## Data

`data/recalls_sample.csv` holds the 30 recall descriptions; the two
`data/recalls_extracted_*.csv` files hold 5 repeats of extractions per model.
The app loads only `repeat_id == 1` at startup (see `data_loader.py`).
