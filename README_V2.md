# Nexus Predictor V2 - setup inicial

Este documento acompaña el Bloque V2.0. La V1 queda estable y la V2 arranca en una rama nueva con PostgreSQL, Docker Compose, Alembic y una estructura preparada para pipelines Prefect.

## 1. Crear la rama V2

Ejecuta esto desde la raíz del repositorio actualizado de V1:

```bash
git status
git checkout main
git pull
git checkout -b refactor/v2-foundations
```

## 2. Aplicar los archivos del ZIP

Copia el contenido del ZIP `nexus-v2-block-00-foundations.zip` encima del proyecto, respetando las rutas.

## 3. Preparar variables de entorno

```bash
cp .env.example .env
cd backend
cp .env.example .env
```

En Windows PowerShell:

```powershell
Copy-Item .env.example .env
Set-Location backend
Copy-Item .env.example .env
```

## 4. Levantar PostgreSQL

Desde la raíz del proyecto:

```bash
docker compose up -d postgres
docker compose ps
```

## 5. Instalar dependencias backend

Desde `backend/`:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

En Windows PowerShell:

```powershell
py -3.11 -m venv .venv
. .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 6. Ejecutar migraciones Alembic

Desde `backend/`:

```bash
alembic -c alembic.ini upgrade head
```

## 7. Validar foundations

Desde `backend/`:

```bash
python scripts/check_environment.py
python scripts/check_v2_foundations.py
pytest
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Endpoints a revisar:

- `GET http://127.0.0.1:8000/api/health`
- `GET http://127.0.0.1:8000/api/database/status`
- `GET http://127.0.0.1:8000/api/editions`
- `GET http://127.0.0.1:8000/api/artists/project-one`

## 8. Commit y push

Cuando las validaciones pasen:

```bash
git add .
git commit -m "start v2 foundations and postgres architecture"
git push -u origin refactor/v2-foundations
```
