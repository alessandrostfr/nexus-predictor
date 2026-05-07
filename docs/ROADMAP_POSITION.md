# Nexus Predictor - Roadmap position

## Current closed blocks

- Block 0 - Environment, structure, Git and GitHub.
- Block 1 - Historical Nexus and Fabrik dataset.
- Block 2 - FastAPI backend foundation.
- Block 3 - Artist enrichment foundation.
- Block 4 - Hard dance subgenre classification.
- Block 5 - Predictive scoring and attendance engine.
- Block 6 - Minimalist responsive React shell.
- Block 7 - Dashboard, rankings and artist profiles.

## Current block scope

Block 8 models Fabrik room capacity, timetable readiness and theoretical saturation risk:

- Fabrik rooms: Hangar, Open Air, Main Room, Satelite, Club Area, Crystal Area and Area 19.
- Hotel Fabrik appears only as a support/orientation area, not as a music room.
- `room_pressure_score` is calculated from estimated capacity, artist demand and room fit.
- The 2026 timetable JSON is ready for official slot import.
- Until official slots exist, the backend and frontend clearly label the result as theoretical simulation.
- The frontend includes a custom interactive map inspired by the user-provided Fabrik map.

## Explicitly not included in this block

- Final polish, README/deploy and release QA.
- Any claim that the simulated room pressure is official.
- Real timetable data before the official schedule is published.

Those belong to Block 9 or a later timetable update.

## Commit

`add room capacity and timetable risk model`

## Estimated progress after closing

95%
