# Nexus Predictor

**Predicción y análisis de demanda para Nexus Festival en Fabrik Madrid.**

Nexus Predictor es una aplicación full stack que combina datos de artistas, historial de ediciones, salas de Fabrik, horarios probables y señales externas para entender qué artistas pueden concentrar más público y cómo podría repartirse la presión entre salas y franjas horarias.

El proyecto empezó como un MVP de visualización y scoring, pero actualmente está evolucionando hacia una versión **ML-first**: datasets trazables, evidencias auditables, modelos entrenables y predicciones persistidas.

> Estado actual: rama `refactor/v3-ml-first` · V3.4-B en curso · foco en ingesta externa controlada y preparación de datos para ML real.

---

## Qué problema intenta resolver

En festivales grandes como Nexus, la experiencia del público depende mucho de cómo se distribuyen los artistas entre salas, horarios y estilos. Una mala combinación puede generar:

- salas demasiado saturadas;
- choques fuertes entre artistas similares;
- horarios poco equilibrados;
- dificultad para anticipar dónde habrá más presión de público.

La idea de este proyecto es construir una herramienta que ayude a analizar esos factores con datos y que, con el tiempo, pueda generar predicciones más fiables sobre demanda, riesgo por sala y planificación de horarios.

---

## Qué hace ahora mismo

- Consulta ediciones de Nexus y lineups por año.
- Muestra perfiles de artistas y señales de popularidad.
- Clasifica artistas por géneros y afinidad con Nexus.
- Analiza salas de Fabrik y capacidad estimada.
- Genera predicciones de demanda y riesgo de saturación.
- Construye horarios probables no oficiales.
- Compara variantes optimizadas de timetable.
- Mantiene una capa de evidencias para saber de dónde sale cada dato.
- Prepara una base de datos ML-ready para futuros modelos reales.

La parte más importante del estado actual no es “adivinar” un horario, sino dejar una base seria para que las futuras predicciones puedan ser explicables, auditables y entrenables.

---

## Lo que NO pretende hacer

Este proyecto no publica horarios oficiales ni sustituye información de la organización. Las predicciones son hipótesis técnicas basadas en datos disponibles, heurísticas, evidencias y, más adelante, modelos ML entrenados.

También hay una regla interna clara: **no se llama Machine Learning a una heurística**. Si algo no tiene dataset, features, target/proxy, entrenamiento, métricas y persistencia de predicciones, se documenta como scoring, baseline u optimización.

---

## Stack

| Área | Tecnologías |
|---|---|
| Backend | Python, FastAPI, SQLAlchemy 2, Alembic |
| Base de datos | PostgreSQL |
| Frontend | Next.js, React, TypeScript, CSS propio |
| Datos / ML | pandas, scikit-learn, datasets versionados, métricas trazables |
| Ingesta | Prefect, APIs oficiales, collectors, caché, rate limiting |
| Validación | pytest, scripts de checks por bloque |
| Deploy previsto | VPS con Docker, reverse proxy y HTTPS |

---

## Arquitectura general

```text
fuentes externas
      ↓
raw snapshots
      ↓
normalización + entity resolution
      ↓
métricas trazables
      ↓
features + labels/proxies
      ↓
datasets de entrenamiento
      ↓
model runs + métricas
      ↓
predicciones persistidas
      ↓
API FastAPI
      ↓
frontend Next.js
```

La arquitectura está pensada para separar muy bien cuatro cosas:

1. **Datos brutos**: lo que se captura de una fuente.
2. **Evidencia normalizada**: lo que ya se puede usar como señal.
3. **Modelos o heurísticas**: cómo se calcula una predicción o baseline.
4. **Producto**: cómo se muestra al usuario de forma clara.

---

## Estado del roadmap

La rama principal de trabajo es:

```text
refactor/v3-ml-first
```

Bloques V3 cerrados:

- V3.0 — Auditoría predictiva y reglas ML-first.
- V3.1 — Contrato real del evento Nexus 2026.
- V3.2 — Fundación de datos ML-ready.
- V3.3 — Resolución de identidad de artistas.
- V3.4-A — Arquitectura de collectors externos.

Bloque actual:

- V3.4-B — Credenciales y probes con APIs oficiales.

Siguientes pasos:

- V3.4-C — Evaluación de herramientas open-source y scraping controlado.
- V3.4-D — Normalización, calidad y fallback manual.
- V3.4-E — Primera ingesta real sobre artistas Nexus 2026.
- V3.4-F — Prefect, revisión admin y cierre del bloque.

---

## Capturas

Las capturas finales se añadirán cuando el proyecto quede desplegado y visualmente cerrado.

Estructura prevista:

```text
docs/assets/screenshots/
  dashboard.png
  artist-profile.png
  room-risk.png
  timetable-comparison.png
  data-review.png
```

---

## Instalación local

### 1. Clonar el repositorio

```powershell
git clone https://github.com/alessandrostfr/nexus-predictor.git
cd nexus-predictor
git switch refactor/v3-ml-first
```

### 2. Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
alembic upgrade head
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

API local:

```text
http://127.0.0.1:8000/api
```

### 3. Frontend

```powershell
cd frontend
npm install
copy .env.example .env.local
npm run dev
```

Frontend local:

```text
http://localhost:3000
```

---

## Validaciones útiles

Backend:

```powershell
cd backend
pytest
python scripts/check_v3_predictive_audit.py
python scripts/check_v3_event_contract.py
python scripts/check_v3_ml_data_foundation.py
python scripts/check_v3_identity_resolution.py
python scripts/check_v3_external_ingestion_architecture.py
python scripts/check_v3_external_credentials.py
```

Frontend:

```powershell
cd frontend
npm run typecheck
npm run build
```

---

## Documentación clave

- `README_V3.md` — guía operativa de la rama ML-first.
- `docs/v3-predictive-audit.md` — auditoría del núcleo predictivo anterior.
- `docs/v3-ml-data-foundation.md` — contrato de datos preparados para ML.
- `docs/v3-identity-resolution.md` — resolución de identidad de artistas.
- `docs/v3-external-ingestion-contract.md` — arquitectura de ingesta externa.
- `docs/v3-official-api-setup.md` — configuración de APIs oficiales.

---

## Qué demuestra este proyecto

Este repositorio no está pensado como una prueba pequeña de framework. Es un proyecto largo donde se trabajan problemas reales de producto y arquitectura:

- diseño de APIs con FastAPI;
- modelado de datos con SQLAlchemy y Alembic;
- separación entre evidencia, scoring, optimización y ML;
- trazabilidad de datos para evitar predicciones inventadas;
- frontend técnico con Next.js y TypeScript;
- documentación de decisiones y límites del sistema;
- evolución progresiva de MVP a producto más serio.

---

## Roadmap cercano

- Completar la ingesta externa de datos de artistas.
- Construir datasets reales de entrenamiento.
- Entrenar primeros modelos de demanda.
- Persistir predicciones con versión de modelo y métricas.
- Añadir panel de revisión de datos.
- Preparar demo pública desplegada.
- Añadir capturas y caso de estudio al portfolio.

---

## Autor

**Alessandro Staiano Fernández**  
Desarrollador web junior orientado a backend, datos, automatización e IA aplicada a producto.

- GitHub: [@alessandrostfr](https://github.com/alessandrostfr)
- LinkedIn: [alessandrostfr](https://www.linkedin.com/in/alessandrostfr)
