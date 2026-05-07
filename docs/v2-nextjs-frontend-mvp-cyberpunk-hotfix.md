# V2.10 Hotfix — MVP structure with cyberpunk V2 styling

This hotfix keeps the V2.10 Next.js + TypeScript frontend, but corrects the UX direction after visual review.

## Scope

- Keeps the first V2.10 premium/cyberpunk visual identity: dark Fabrik night, violet, yellow, acid green, cyan, glow and glass layers.
- Reorganizes the product closer to the MVP structure without copying it exactly.
- Removes `Ficha` from the main menu; artist detail is opened from the ranking as a deeplink-style internal view.
- Adds a dedicated `Horarios` view for probable timetable and optimized variants.
- Keeps V2 metrics/components instead of simplifying the app: evidence coverage, V2 demand, genre coverage, probable timetable, optimized variants and social/music-platform status.
- Rebuilds room risk from V2.8/V2.9 model fields, especially `expected_pressure_score`, `crowding_score`, `demand_score`, `crowd_risk` and `room_capacity` when available.

## Main views

```text
Dashboard | Ranking | Salas | Horarios
```

## Validation

From `frontend/`:

```powershell
npm install
npm audit
npm run typecheck
npm run build
npm run dev
```

From `backend/` in another terminal:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:3000
```

## Commit

This remains part of V2.10:

```text
migrate frontend to nextjs typescript
```
