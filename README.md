# FitFinder API

AI size & fit recommendation API for online clothing. Online fashion sees roughly 24–30% returns
(vs. 8–10% in stores), mostly because sizes differ between brands. FitFinder takes a shopper's
body measurements (or just height + weight) and matches them against each brand's size chart to
recommend a size, with a confidence score and an estimated return risk.

Part 1 of a multi-surface product: **API (this repo)** → full-stack web app → browser extension → iOS app.

## Stack

Python 3.12 · FastAPI · Pydantic v2 · SQLAlchemy 2 (async) · SQLite (dev) / PostgreSQL (prod) ·
uv · Ruff · pytest · Docker (multi-stage, non-root) · GitHub Actions → GHCR

## Run it

```bash
# Docker (API + Postgres)
docker compose up --build
# -> http://localhost:8000/docs

# or locally
uv sync
uv run uvicorn app.main:app --reload
uv run pytest
```

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | liveness check |
| POST | `/v1/measurements/estimate` | height + weight + gender → chest/waist/hip/shoulder (cm) |
| POST | `/v1/recommend` | brand + garment + body → size, confidence, return risk, fit notes |
| GET/POST | `/v1/brands` | list brands / onboard a brand with its size charts (B2B) |
| POST | `/v1/feedback` | record kept/returned outcome — **the future training data** |

```bash
curl -X POST localhost:8000/v1/recommend -H 'content-type: application/json' \
  -d '{"brand":"demo-urban","category":"tshirt","gender":"male","height_cm":175,"weight_kg":70}'
```

Set `FITFINDER_API_KEYS=key1,key2` to require an `X-API-Key` header (empty = open, dev only).
Copy `.env.example` to `.env` for all settings.

## What is real vs. placeholder

- **Real & working:** API, validation, auth, DB, size-chart matching engine, return-risk scoring, feedback capture, tests, Docker, CI.
- **Placeholder (by design):** `BaselineEstimator` is a hand-fitted height/weight → girth heuristic (±5 cm), and the seeded `demo-*` brands are illustrative, **not real brand data**. The risk curve constants are hand-set. All three get replaced by learned models — see below.

## Training roadmap (when we're ready to train)

1. **Collect outcomes.** Every `/v1/feedback` row (brand, size bought, kept/returned, too_small/too_large, measurements) is a labelled example. Start logging from day one.
2. **Better measurements (biggest accuracy win).** Replace `BaselineEstimator` with a vision model: user records a short video/photos → pose/body-landmark estimation (e.g. MediaPipe / Apple Vision body pose + ARKit/LiDAR depth on iOS) → girths via a regressor. Train/validate on a public anthropometric dataset (e.g. ANSUR II) plus real tape-measure ground truth from beta users.
3. **Learn the fit model.** Gradient-boosted trees (LightGBM/XGBoost) predicting `P(return | body, brand, size, category)` from feedback; calibrate (isotonic/Platt) so `return_risk` is a true probability. Keep the rules engine as the cold-start fallback and as a feature.
4. **Brand embeddings.** Learn per-brand "runs small/large" offsets from returns, so brands without published charts still work.
5. **Evaluate.** Offline: AUC/log-loss on returns, size-accuracy vs. kept-purchases. Online: A/B test return rate with vs. without recommendations. Version every model (`model_version` is already in each response).
6. **Serve.** Export to ONNX, load behind the existing `Estimator`/recommender interfaces — no API change for clients.

## Privacy

Body measurements are sensitive. Use pseudonymous `user_ref` only (no names/emails), keep videos on-device where possible (iOS), and add consent + deletion endpoints before any public launch (India's DPDP Act applies).

## Project layout

```
app/            FastAPI app (routers/, services/, schemas, models)
tests/          pytest suite
Dockerfile      multi-stage uv build, non-root
docker-compose.yml   API + Postgres
.github/workflows/ci.yml   lint, test, docker build, push to GHCR on main
```
