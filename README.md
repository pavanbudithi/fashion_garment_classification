# Fashion Garment Classification & Inspiration Web App

A lightweight AI-powered web app for fashion designers to upload inspiration images, automatically classify them with a multimodal model, and search/filter a growing inspiration library.

This project was built as a pragmatic, timeboxed proof of concept for a take-home assignment. The goal was to optimize for speed, clarity, correctness, and a clean review discussion rather than overengineering.

## What it does

### Core features implemented
- Upload garment or street-fashion images through a web UI
- Classify each uploaded image with Gemini multimodal inference into:
  - a rich natural-language description
  - structured metadata such as garment type, style, material, pattern, season, occasion, trend notes, and location context
- Store image files and metadata in SQLite
- Display the image library in a visual grid
- Support dynamic metadata filters generated from stored data
- Support natural-language search across descriptions and metadata
- Support lightweight synonym expansion for natural queries such as:
  - `embroidered neckline`
  - `artisan market`
- Import a labeled evaluation dataset into the app so the gallery shows a realistic library and filters are demoable

### Partially implemented / next step
- The assignment asked for designer annotations (`tags`, `notes`, `observations`) to be searchable and clearly separated from AI metadata. The current submission focuses on the core upload, classify, search, filter, and evaluation workflow. Annotation support would be the next feature to add.

## Stack

- **Backend:** FastAPI
- **Frontend:** server-rendered HTML + vanilla JavaScript + CSS
- **Database:** SQLite + SQLAlchemy ORM
- **Model:** Google Gemini multimodal API
- **Storage:** local file storage under `data/uploads`
- **Testing:** Pytest
- **Evaluation:** JSON-based labeled dataset + Python evaluation script

## Why this stack

For a one-day prototype, this stack was chosen because it is lightweight, easy to run locally, and fast to explain in a review:
- **FastAPI** gives simple routing, typing, and quick API/UI integration
- **SQLite** avoids external infrastructure and keeps setup minimal
- **Local file storage** is enough for a proof of concept and easy to inspect
- **Vanilla JS + HTML** avoids frontend build tooling overhead while still proving the UI flow
- **Gemini multimodal API** lets the project focus on product behavior instead of training a custom vision model

In production, SQLite would likely be replaced by Postgres, local file storage by object storage, and search would evolve into a hybrid metadata + semantic retrieval system.

## Repository structure

```text
/app
  /api/routes
  /core
  /models
  /repositories
  /schemas
  /services
  /static
  /templates
/eval
/tests
README.md
```

## Architecture overview

### 1. Upload and classification flow
1. User uploads an image through the web UI
2. FastAPI receives the file at `/upload`
3. Image is saved under `data/uploads`
4. Gemini multimodal classification is called
5. The model returns:
   - a natural-language description
   - structured normalized attributes
6. Data is persisted into SQLite
7. The image appears in the gallery

### 2. Search and filtering flow
- The frontend calls:
  - `/garments/search`
  - `/garments/filters/`
- Filter values are computed dynamically from the DB, not hardcoded
- Search supports natural-language matching over:
  - description
  - trend notes
  - garment type
  - style
  - material
  - pattern
  - occasion
  - designer
  - location fields
- Lightweight synonym expansion is used to make natural queries work better

### 3. Evaluation flow
1. Build a labeled test set from open-source fashion/streetwear images
2. Manually define expected labels
3. Run the classifier against the test set
4. Compare predicted vs expected labels
5. Report per-attribute accuracy

## Setup

### 1. Create and activate virtual environment

**Windows PowerShell**

```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

### 2. Install dependencies

```powershell
pip install -r requirements.txt
```

Key packages used:
- `fastapi`
- `uvicorn`
- `sqlalchemy`
- `pydantic-settings`
- `jinja2`
- `pillow`
- `google-genai`
- `pytest`

### 3. Configure environment

Create a `.env` file at repo root:

```env
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.5-flash-lite
DATABASE_URL=sqlite:///./data/fash_garm.db
UPLOAD_DIR=./data/uploads
```

### 4. Run the app

```powershell
.\.venv\Scripts\python -m uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/
```

## Evaluation dataset

A manually labeled evaluation set was created in:
- `eval/labeled_dataset_normalized.json`

Evaluation images were stored in:
- `data/fash_pics`

The final project library was then imported into SQLite using `eval/import_eval_to_db.py` so the frontend could browse a realistic image set.

## Final evaluation results

The latest evaluation run used **50 successfully evaluated images** from a **51-image labeled dataset**. One image encountered a transient Gemini API timeout (`503 UNAVAILABLE`) during the run.

Per-attribute accuracy:
- **garment_type:** 48.00%
- **style:** 62.00%
- **material:** 52.00%
- **occasion:** 82.00%
- **location_context:** 100.00%

### Interpretation
- **Occasion** performed best among the core semantic labels
- **Style** and **material** improved significantly after constraining outputs to a fixed taxonomy
- **Garment type** remained the hardest because many images contain layered outfits or multiple strong garment candidates
- **Location context** scored very high because it was intentionally normalized coarsely

### Why the metrics improved
The biggest gains came from:
- constraining Gemini output to a fixed taxonomy
- few-shot prompting
- structured JSON output constraints
- canonical normalization of model outputs
- synonym-aware / normalized comparison during evaluation

## How to run evaluation

### Run classifier evaluation

```powershell
.\.venv\Scripts\python eval\run_eval.py
```

### Import evaluation images into the app database

```powershell
.\.venv\Scripts\python eval\import_eval_to_db.py
```

## Browser validation completed

The following were manually validated in the browser:
- homepage loads successfully
- dynamic filters load from `/garments/filters/`
- gallery data loads from `/garments/search`
- imported images load correctly from `/uploads/...`
- natural-language search works for example queries such as:
  - `embroidered neckline`
  - `gucci`
  - `puffer`
- combined filters work for designer and material combinations
- after DB reset and re-import, the clean imported gallery loads again without stale manual rows

## API endpoints

### Core
- `GET /`
- `GET /health`

### Upload
- `POST /upload`

### Search / filters
- `GET /garments/search`
- `GET /garments/filters/`

## Example search queries

- `embroidered neckline`
- `artisan market`
- `gucci`
- `paris`
- `streetwear jacket`

## Product tradeoffs

This was intentionally built as a lightweight proof of concept:
- SQLite instead of Postgres for minimal local setup
- local file storage instead of cloud storage
- vanilla JS instead of React to keep the frontend simple and fast to deliver
- imported evaluation images were also used as the browseable library so the UI would look complete quickly
- search is metadata + text matching with synonym expansion, not embedding-based semantic retrieval

These are deliberate tradeoffs for a one-day take-home.

## Limitations

- Full designer annotations (`tags`, `notes`, `observations`) are not yet implemented as a searchable first-class feature
- One evaluation image hit a transient API timeout during the latest run
- Search is lightweight keyword + synonym expansion, not vector search
- Material classification is still visually ambiguous for some images
- Some images contain multiple garments, making dominant-garment labeling subjective
- Frontend is intentionally minimal rather than polished for production

## What I would do next with more time

1. Add full designer annotation support:
   - tags
   - notes
   - observations
   - searchable separately from AI metadata

2. Improve evaluation:
   - confusion matrix for garment type
   - error buckets by category
   - automatic retry queue for transient API failures
   - more human-reviewed analysis of failure cases

3. Improve search quality:
   - hybrid metadata + semantic search
   - stronger phrase boosting
   - better synonym expansion
   - optional vector retrieval for visual inspiration similarity

4. Improve frontend:
   - annotation forms
   - detail drawer / modal
   - pagination
   - clearer loading and empty states

5. Improve testing:
   - dedicated unit test for structured parsing
   - stronger end-to-end coverage for upload → classify → filter
   - annotation workflow tests

## Submission note

This submission prioritizes the core workflow:
- upload
- classify
- browse
- search
- filter
- evaluate

Some secondary features, especially designer annotations, are not fully finished yet. They are called out honestly here along with the next steps.
