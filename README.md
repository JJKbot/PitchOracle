# PitchOracle - Soccer Odds Guesser

A local-first web app that aggregates daily soccer fixtures, computes win/draw/loss probabilities, and surfaces rich match detail (lineups, injuries, standings, and advanced stats) across major and niche leagues.

## Highlights
- Multi-provider pipeline with API-Football as the primary source and football-data.org as fallback.
- Daily fixtures view with a calendar date picker.
- Match odds driven by form, Poisson scoring, and player impact.
- Player highlights, lineups, injuries, standings, and advanced stats per fixture.
- Caching and request caps to respect free-plan rate limits.

## Tech stack
- Backend: FastAPI + httpx
- UI: server-rendered HTML + vanilla JS
- Storage: in-memory cache (optional DB can be added)

## Quick start

1. Create a virtual environment and install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r .\backend\requirements.txt
```

2. Configure environment variables:

```powershell
copy .\backend\.env.example .\backend\.env
```

Set at least one of:
- `API_FOOTBALL_KEY` (API-Sports direct key)
- `API_FOOTBALL_RAPIDAPI_KEY` (RapidAPI key)

Optional:
- `FOOTBALL_DATA_API_TOKEN` for fallback fixtures
- `DETAILS_MAX_FIXTURES` to cap per-fixture detail calls

3. Run the server:

```powershell
uvicorn app.main:app --reload --app-dir .\backend
```

Open `http://127.0.0.1:8000`.

## League coverage
League targets live in `./backend/app/data/leagues.json`. Premier League is prefilled. Add or adjust league IDs for:
- Premier League, La Liga, Serie A, Bundesliga, Ligue 1
- MLS, Saudi Pro League, Botola Pro

## Model notes
The odds model blends recent form, Poisson scoring, and a player-impact boost. It is for analysis only and is not betting advice.

## License
Apache-2.0. See `LICENSE`.
