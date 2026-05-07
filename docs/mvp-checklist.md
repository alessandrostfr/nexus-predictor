# Final MVP checklist

## Backend

- [ ] `pip install -r requirements.txt` completes.
- [ ] `python scripts/check_environment.py` passes.
- [ ] `python scripts/validate_dataset.py` passes.
- [ ] `python scripts/generate_predictions.py --year 2026` completes.
- [ ] `pytest` passes.
- [ ] `uvicorn app.main:app --reload --host 127.0.0.1 --port 8000` starts.
- [ ] `/api/health` responds with success.
- [ ] `/docs` opens.

## Frontend

- [ ] `npm install` completes.
- [ ] `npm run build` completes.
- [ ] `npm run dev` starts.
- [ ] App opens at `http://127.0.0.1:5173`.
- [ ] Mobile width has no horizontal overflow.
- [ ] Bottom navigation works on mobile.
- [ ] Dashboard loads.
- [ ] Ranking filters work.
- [ ] Artist profile opens from ranking.
- [ ] Room map loads and time filter changes saturation.

## Data honesty

- [ ] Estimated values are clearly labelled.
- [ ] Timetable status is not presented as official.
- [ ] Hotel Fabrik is not counted as a music room.
- [ ] API keys and `.env` files are not committed.

## Release commit

```bash
git add .
git commit -m "polish responsive UI and deployment setup"
git push
```
