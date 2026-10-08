# What Quality Engineers Need to Know About Generative AI: Structured Data Extraction

Companion repository for the paper
**"What Quality Engineers Need to Know About Generative AI: Structured Data Extraction."**

**Authors:** Fadel M. Megahed, Ying-Ju Chen, Yamin Dahwich, Arthur Carvalho,
L. Allison Jones-Farmer, Ibrahim Yousif, and Inez M. Zwetsloot
(Miami University, University of Dayton, University of Cambridge, and University of Amsterdam)

**Status:** manuscript in preparation, to be submitted to *Quality Engineering*. The paper
is not yet on arXiv. This page will link to it when it is available.

## What this is about

Much of the information that quality engineers work with arrives as free text or scanned
documents: warranty claims, customer complaints, recall notices, maintenance logs, and
inspection forms. Structured data extraction uses a large language model to convert such
records into a table. The engineer defines the columns and describes each one in plain
language, and the model fills in one row per record.

The paper explains the method, shows where it fits in quality engineering work, and
presents two applications that anyone can try. The extracted table is a first draft of the
data. The field definitions, the validation, and the interpretation remain the engineer's
responsibility, which is why each application below was also evaluated by human reviewers.

## The two applications

Both applications are public and free to use. No programming is needed to try them.

### Application 1: Recall Notice Data Extraction

**Try it: https://huggingface.co/spaces/fmegahed/structured_text_extraction**

You define the fields you want in the browser, for example the manufacturer, the affected
component, and whether the defect involves software. You then paste text or upload a PDF
or an image, and the app returns a table that you can download as a CSV file. The paper
demonstrates it on vehicle recall notices from the National Highway Traffic Safety
Administration (NHTSA), but the fields are yours to define, so the same app works for
other record types.

The hosted demo sends your input to an OpenAI model. For sensitive or proprietary records,
the paper notes that the app can be run on your own infrastructure with a different model
provider.

Source code: [files of the Hugging Face Space](https://huggingface.co/spaces/fmegahed/structured_text_extraction/tree/main)

### Application 2: QE ArXiv Watch

**Try it: https://huggingface.co/spaces/fmegahed/arxiv_control_charts**

A dashboard that checks arXiv every day for new research in three areas: statistical
process control, design of experiments, and reliability. For each paper it extracts a
structured factsheet, so you can filter and compare papers by their methods without
reading every abstract.

Source code: https://github.com/fmegahed/hf_arxiv_control_charts

## How we evaluated the applications

An extracted table is only useful if its values can be trusted, so we asked people to
check the output of each application against the source documents.

**Application 1.** Four reviewers rated the manufacturer, vehicle models, and model years
that two models extracted from 30 NHTSA recall descriptions. Each field was rated on a
five-point correctness scale from 1 (Incorrect) to 5 (Correct). The extractions were shown
in random order, and the reviewers did not know which model had produced each one.

**Application 2.** Authors of papers in the dashboard rated the factsheet that was
extracted from their own paper.

For each evaluation we built a review app that presents one item at a time, keeps the
rating definitions on screen, and records the ratings. These review apps are study
instruments. A reviewer opens one through a personal link, so the web addresses below show
no study content to other visitors.

| Evaluation | Review app | Source code |
|---|---|---|
| Application 1 | Hosted on Railway at https://human-eval-production.up.railway.app | [`apps/human_eval/`](apps/human_eval/) in this repository |
| Application 2 | Hosted on Railway at https://author-review-production.up.railway.app | https://github.com/fmegahed/author_review |

**A two-minute video shows the Application 1 review app from the reviewer's side:**
https://youtu.be/6fa1jBlPgCY

The reviewer session shown in the video was a test run and was excluded from the results
reported in the paper.

For Application 1 we also compared seven language models on the same extraction task. Six
of them are small open-weight models that run on a local computer, which matters when
records cannot leave the organization. The comparison covers how consistently each model
repeats its own answer, how long it takes, how large it is, and what it costs. That code
is in [`app1_eval_code/`](app1_eval_code/).

## What is in this repository

This repository holds the evaluation materials for Application 1. The applications
themselves and the Application 2 review app live at the links above.

```
apps/human_eval/     Review app used for the Application 1 human evaluation
app1_eval_code/      R scripts and results for the Application 1 model comparison
```

The rest of this page is for readers who want to rerun or adapt the code.

### `apps/human_eval/`: review app for Application 1

A web app (FastAPI and PostgreSQL) that collects the reviewers' ratings.

- **Items:** 30 recall descriptions, each processed by two models (`gemma4:e2b` and
  `gpt-5.4-nano`), which gives each reviewer 60 extractions.
- **Blinding:** extractions are shown in randomized order without model names. The order
  is generated separately for each reviewer.
- **Reviewer workflow:** one recall description and one extraction per screen, rating
  definitions on every screen, keyboard shortcuts, saved progress, and the option to
  revise earlier ratings or resume later with the same link.
- **Output:** all ratings download as one CSV file, with the model names restored for
  analysis.

The fields and the rating scale are defined in `apps/human_eval/config.py`, and the items
are loaded from the CSV files in `apps/human_eval/data/`. These are the places to start
when adapting the app to another rating study. Setup, tests, and
deployment notes are in [`apps/human_eval/README.md`](apps/human_eval/README.md). To run
it locally:

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

## Use of AI coding tools

We used [Claude Code](https://claude.com/claude-code) in building all four apps listed
above: the two applications and the two review apps.

The overview video of the Application 1 review app was also produced with Claude Code. It
uses a skill for scripted, narrated demo videos that Fadel M. Megahed created as part of
his ongoing work.

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
