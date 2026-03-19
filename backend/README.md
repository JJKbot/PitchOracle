# Project Hermes - Soccer Odds Guesser (Local)

This is a local-only FastAPI app that fetches daily soccer fixtures, computes win/draw/loss probabilities, and renders a web UI with a calendar date picker.

## Quick start

1. Create a virtual environment and install deps:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r .\backend\requirements.txt
```

2. Configure your API token:

```powershell
copy .\backend\.env.example .\backend\.env
```

Edit `.\backend\.env` and set:
- `API_FOOTBALL_KEY` (API-Sports direct key) or `API_FOOTBALL_RAPIDAPI_KEY` (RapidAPI key)
- `FOOTBALL_DATA_API_TOKEN` (optional fallback)

If you want full coverage, fill league IDs in `.\backend\app\data\leagues.json`. Premier League is prefilled (ID `39`). Others can be resolved automatically if your API key allows the `/leagues` search endpoint.

3. Run the server:

```powershell
uvicorn app.main:app --reload --app-dir .\backend
```

Open `http://127.0.0.1:8000`.

## Notes
- If `API_FOOTBALL_KEY` and `API_FOOTBALL_RAPIDAPI_KEY` are missing, the app serves sample data so the UI still works.
- The model is a transparent heuristic (recent form + Poisson goal model + top scorer boost). It is not betting advice.
- League coverage is configured in `.\\backend\\app\\data\\leagues.json`.
- Detailed fixtures (lineups, injuries, advanced stats) are capped by `DETAILS_MAX_FIXTURES` to avoid free-plan rate limits.

## Data sources
- API-Football (API-Sports) for fixtures and top scorers (global coverage).
- football-data.org API as a fallback fixtures source.
