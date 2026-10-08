# What Quality Engineers Need to Know About Generative AI: Structured Data Extraction

Code and data for the two applications in the paper
**"What Quality Engineers Need to Know About Generative AI: Structured Data Extraction."**

**Authors:** Fadel M. Megahed, Ying-Ju Chen, Yamin Dahwich, Arthur Carvalho,
L. Allison Jones-Farmer, Ibrahim Yousif, and Inez M. Zwetsloot
(Miami University, University of Dayton, University of Cambridge, and University of Amsterdam)

**Status:** manuscript in preparation. The paper is not yet on arXiv and has not been
submitted to a journal. This page will link to it when it is available.

## Deployed apps

| Application | App | Deployed at | Source code |
|---|---|---|---|
| 1. Recall Notice Data Extraction | Structured extraction demo | **https://huggingface.co/spaces/fmegahed/structured_text_extraction** | Files tab of the Hugging Face Space |
| 1. Recall Notice Data Extraction | Reviewer app for the human evaluation | **https://human-eval-production.up.railway.app** | [`apps/human_eval/`](apps/human_eval/) in this repository |
| 2. Monitoring Quality Engineering Research | QE ArXiv Watch dashboard | **https://huggingface.co/spaces/fmegahed/arxiv_control_charts** | https://github.com/fmegahed/hf_arxiv_control_charts |
| 2. Monitoring Quality Engineering Research | Author review app for the factsheet evaluation | **https://author-review-production.up.railway.app** | https://github.com/fmegahed/author_review |

The two review apps open only through a personal reviewer link or the admin login, so
their home pages show no study content.

**Overview video of the Application 1 reviewer app (1:56):** https://youtu.be/6fa1jBlPgCY

The reviewer session shown in the video was a test run and was excluded from the results
reported in the paper.

## What is in this repository

```
apps/human_eval/     Reviewer app used for the Application 1 human evaluation
app1_eval_code/      R scripts and results for the Application 1 model comparison
```

The Application 2 apps are maintained in their own repositories, linked in the table above.

### `apps/human_eval/`: reviewer app

A FastAPI and PostgreSQL web app that collects human ratings of fields that a language
model extracted from vehicle recall descriptions.

- **Task:** 30 recall descriptions from the National Highway Traffic Safety Administration
  (NHTSA), each processed by two models (`gemma4:e2b` and `gpt-5.4-nano`), which gives
  each reviewer 60 extractions.
- **Fields rated:** manufacturer, vehicle models, and model years, each on a five-point
  correctness scale from 1 (Incorrect) to 5 (Correct).
- **Blinding:** extractions are shown in randomized order without model names. The
  presentation order is generated per reviewer and fixed when the reviewer link is created.
- **Reviewer workflow:** one recall description and one extraction per screen, rubric
  definitions on every screen, keyboard shortcuts, saved progress, and the option to
  revise earlier ratings or resume later with the same link.
- **Export:** the admin page downloads all ratings as a long-format CSV with the model
  names restored.

Setup, tests, and deployment notes are in [`apps/human_eval/README.md`](apps/human_eval/README.md).
To run it locally:

```bash
cd apps/human_eval
docker compose up --build
# App at http://localhost:8000
```

### `app1_eval_code/`: model comparison for Application 1

R scripts that run the same extraction task on seven models and compare them.

| File | Purpose |
|---|---|
| `recalls_sample.csv` | The sample of NHTSA recall descriptions |
| `01_extracting_the_results.R` | Extracts the three fields from each description with each model, with repeated runs, and saves the extractions and runtime summaries |
| `02_intra_model_consistency.R` | Computes how often repeated runs of the same model return identical values |
| `03_model_comparison_figure.R` | Builds the model comparison figure from the consistency and runtime results |
| `results/cpu/`, `results/gpu/` | Extractions, runtime summaries, consistency tables, and figures for the CPU and GPU runs |

Models compared: `gemma4:e2b`, `granite4.1:3b`, `granite4.1:8b`, `llama3.2:1b`,
`llama3.2:3b`, `phi4-mini`, and `gpt-5.4-nano`.

The scripts use the [`ellmer`](https://ellmer.tidyverse.org/) R package. The open-weight
models run locally through [Ollama](https://ollama.com/). `gpt-5.4-nano` needs an OpenAI
API key in the `OPENAI_API_KEY` environment variable, for example in a local `.Renviron`
file, which is not tracked in this repository. Run the scripts in numeric order from the
`app1_eval_code/` folder.

## Data source

The recall descriptions are public records from NHTSA:
https://www.nhtsa.gov/resources-investigations-recalls

## License

The code in this repository is released under the [MIT License](LICENSE). The recall
descriptions are public NHTSA records.

## Citation

A citation will be added here when the paper is publicly available.

## Contact

Corresponding author: Inez M. Zwetsloot, i.m.zwetsloot@uva.nl
