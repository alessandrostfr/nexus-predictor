# Nexus Predictor

**Nexus Predictor** es una aplicación web full stack para analizar y simular el festival **Nexus en Fabrik Madrid** usando datos históricos, perfiles de artistas, señales externas, modelos predictivos/baselines y visualización interactiva.

> Proyecto personal de aprendizaje y portfolio. No está afiliado oficialmente a Fabrik, Nexus ni a sus organizadores. Las predicciones y simulaciones no son horarios oficiales.

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-Frontend-000000?logo=nextdotjs&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-4169E1?logo=postgresql&logoColor=white)
![Machine Learning](https://img.shields.io/badge/ML--ready-Data%20%2B%20Models-FF6F00)

---

## Qué problema resuelve

En festivales grandes como Nexus, la experiencia del público depende de muchos factores: popularidad real de los artistas, distribución por salas, horarios, solapamientos, capacidad de cada room y momentos de saturación.

Este proyecto convierte esa idea en un producto técnico completo:

- recopila y estructura datos históricos de ediciones anteriores;
- modela artistas, géneros, salas, horarios y fuentes externas;
- calcula demanda y presión esperada por sala/franja;
- genera horarios probables y variantes optimizadas;
- visualiza el resultado en un dashboard web con estética propia;
- evoluciona hacia una arquitectura **ML-first**, separando evidencia, features, labels, modelos y predicciones.

---

## Estado actual del proyecto

El proyecto tiene varias etapas históricas:

| Etapa | Estado | Descripción |
|---|---:|---|
| V1 | Cerrada | MVP funcional con dataset histórico, backend FastAPI, frontend React y simulación inicial. |
| V2 | Cerrada parcialmente como evolución de producto | PostgreSQL, Alembic, evidencia, Spotify/Last.fm, géneros, timetable histórico, demanda, horarios probables y frontend premium. |
| V3 | Activa | Replanteamiento **ML-first** para que las predicciones se basen en datos trazables, features, entrenamiento real, métricas y persistencia. |

**Punto actual de la V3:** `V3.4-B — Configuración, credenciales y probes oficiales` dentro del subroadmap de ingesta externa.  
La documentación operativa está en [`docs/ROADMAP_POSITION.md`](docs/ROADMAP_POSITION.md).

### Regla de honestidad ML

Este repositorio distingue claramente entre:

- **evidencia / datos brutos**: snapshots, métricas y fuentes externas;
- **features ML-ready**: datos preparados para entrenar modelos;
- **baselines / heurísticas**: scoring explicable provisional;
- **optimización**: variantes de timetable con reglas/constraints;
- **ML real**: solo cuando exista entrenamiento, validación, métricas y predicciones persistidas.

Nada se presenta como ML final si no cumple esos criterios.

---

## Funcionalidades principales

### Datos y backend

- API REST con FastAPI.
- PostgreSQL como base de datos principal.
- Migraciones con Alembic.
- Seed de ediciones históricas 2022-2026.
- Modelo de artistas, géneros, salas, horarios y fuentes.
- Capa de evidencia para métricas externas.
- Integración controlada con Spotify, Last.fm, MusicBrainz, YouTube y SoundCloud.
- Arquitectura de collectors con control de credenciales, rate limits, caché e idempotencia.

### Predicción, demanda y timetable

- Scoring de demanda por artista.
- Estimación de riesgo de saturación por sala.
- Timetable probable 2026 no oficial.
- Variantes optimizadas: anti-crowding, balanced y fan experience.
- Separación entre heurística, optimización y ML real.

### Frontend

- Aplicación Next.js + TypeScript.
- Dashboard visual de festival.
- Mapa de Fabrik y salas.
- Fichas de artistas.
- Métricas, ranking, riesgo y explicaciones.
- Estética cyberpunk/Fabrik-night con CSS propio.
- Enfoque responsive.

---

## Stack técnico

### Backend

- Python 3.11
- FastAPI
- Pydantic / Pydantic Settings
- SQLAlchemy 2
- Alembic
- PostgreSQL
- Prefect
- httpx / BeautifulSoup / lxml
- pytest / ruff

### Datos, IA y optimización

- pandas
- numpy
- scikit-learn
- OR-Tools
- Spotify Web API
- Last.fm API
- MusicBrainz API
- YouTube Data API
- SoundCloud access/probe strategy

### Frontend

- Next.js
- React
- TypeScript
- Recharts
- Framer Motion
- lucide-react
- CSS custom

### Infraestructura prevista

- Docker / Docker Compose
- VPS Linux
- Reverse proxy
- HTTPS
- PostgreSQL persistente
- Backups

---

## Arquitectura resumida

```text
nexus-predictor/
├── backend/
│   ├── app/api/                 # Endpoints FastAPI
│   ├── app/services/            # Lógica de negocio, scoring, evidencias, modelos
│   ├── app/collectors/          # Contratos y probes externos V3
│   ├── app/db/                  # SQLAlchemy + modelos
│   ├── app/data/                # Seeds históricos y datos base
│   ├── alembic/                 # Migraciones PostgreSQL
│   └── tests/                   # Tests backend
├── frontend/
│   ├── app/                     # Next.js App Router
│   ├── src/components/          # Componentes visuales
│   ├── src/api/                 # Cliente API
│   └── src/assets/              # Assets frontend
├── docs/                        # Roadmap, setup, decisiones y documentación técnica
└── docker-compose.yml           # PostgreSQL local
```

---

## Instalación local

Consulta la guía completa en [`docs/setup.md`](docs/setup.md).

### 1. Levantar PostgreSQL

```powershell
cd nexus-predictor
docker compose up -d
```

### 2. Backend

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
alembic upgrade head
pytest
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

API local:

```text
http://127.0.0.1:8000/api
http://127.0.0.1:8000/docs
```

### 3. Frontend

```powershell
cd frontend
npm install
copy .env.example .env.local
npm run typecheck
npm run build
npm run dev
```

Frontend local:

```text
http://127.0.0.1:3000
```

---

## Validación rápida

Backend:

```powershell
cd backend
pytest
python scripts/check_v3_predictive_audit.py
python scripts/check_v3_event_contract.py
python scripts/check_v3_ml_data_foundation.py
python scripts/check_v3_identity_resolution.py
python scripts/check_v3_external_ingestion_architecture.py
```

Frontend:

```powershell
cd frontend
npm run typecheck
npm run build
```

---

## Capturas y demo

La demo pública se desplegará más adelante dentro del bloque de despliegue VPS del portfolio.

Capturas previstas:

- dashboard principal;
- mapa de Fabrik;
- detalle de salas;
- ranking de artistas;
- timetable probable;
- variantes optimizadas;
- panel admin/data review.

Guía de capturas: [`docs/screenshots.md`](docs/screenshots.md).

---

## Documentación útil

- [`docs/ROADMAP_POSITION.md`](docs/ROADMAP_POSITION.md) — punto exacto actual del roadmap V3.
- [`README_V3.md`](README_V3.md) — guía operativa ML-first.
- [`docs/v3-predictive-audit.md`](docs/v3-predictive-audit.md) — auditoría del núcleo predictivo.
- [`docs/v3-ml-data-foundation.md`](docs/v3-ml-data-foundation.md) — base de datos ML-ready.
- [`docs/v3-identity-resolution.md`](docs/v3-identity-resolution.md) — resolución de identidad de artistas.
- [`docs/v3-external-ingestion.md`](docs/v3-external-ingestion.md) — arquitectura de ingesta externa.
- [`docs/case-study.md`](docs/case-study.md) — caso de estudio preparado para portfolio.
- [`docs/deployment.md`](docs/deployment.md) — plan de despliegue en VPS.

---

## Qué demuestra este proyecto

Este proyecto está pensado para enseñar competencias reales de desarrollo full stack y datos:

- diseño de producto a partir de un problema concreto;
- backend API con FastAPI;
- modelado de datos con SQLAlchemy y PostgreSQL;
- migraciones con Alembic;
- frontend moderno con Next.js y TypeScript;
- integración de APIs externas;
- arquitectura de ingesta trazable;
- separación honesta entre datos, heurísticas, optimización y ML;
- documentación técnica y decisiones de producto;
- preparación para despliegue real.

---

## Roadmap próximo

- Completar V3.4-B con probes oficiales.
- V3.4-C: yt-dlp, scraping controlado y evaluación open-source.
- V3.4-D: normalización, calidad y contratos de métricas.
- V3.4-E: ingesta real para artistas Nexus 2026.
- V3.4-F: Prefect, admin review y cierre del bloque.
- V3.5: SoundCloud-first artist intelligence.
- Entrenamiento real de modelos ML con métricas visibles.

---

## Autor

Desarrollado por **Alessandro Staiano Fernández** como proyecto personal de portfolio, aprendizaje full stack y Machine Learning aplicado.

- GitHub: [@alessandrostfr](https://github.com/alessandrostfr)
- LinkedIn: [alessandrostfr](https://www.linkedin.com/in/alessandrostfr)
