# Nexus Predictor

Nexus Predictor is a small Python + React application to research Nexus Festival editions, enrich artists with public music data, and estimate demand, attendance, and crowd pressure for future editions.

## Block 0 goal

This first block only prepares the project foundation:

- Python virtual environment.
- FastAPI backend skeleton.
- React frontend skeleton.
- Editable data folders.
- Git and GitHub workflow.

No prediction logic is implemented yet. That belongs to later roadmap blocks.

---

## 1. Create the project folder

Unzip this project and enter the folder:

```bash
cd nexus-predictor
```

---

## 2. Backend setup

### Windows PowerShell

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### macOS / Linux

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Backend health check:

```txt
http://127.0.0.1:8000/api/health
```

Interactive API docs:

```txt
http://127.0.0.1:8000/docs
```

---

## 3. Frontend setup

Open another terminal from the project root:

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

On Windows PowerShell, use:

```powershell
cd frontend
npm install
copy .env.example .env
npm run dev
```

Frontend URL:

```txt
http://127.0.0.1:5173
```

---

## 4. Run backend tests

From `backend/` with the virtual environment active:

```bash
pytest
```

---

## 5. Create the Git repository

From the project root:

```bash
git init
git add .
git commit -m "initialize project structure"
git branch -M main
```

Then create an empty repository on GitHub named `nexus-predictor` without README, without `.gitignore`, and without license. After that:

```bash
git remote add origin https://github.com/YOUR_USERNAME/nexus-predictor.git
git push -u origin main
```

Alternative with GitHub CLI:

```bash
gh repo create nexus-predictor --private --source=. --remote=origin --push
```

---

## 6. Current roadmap position

Current block: `Block 0 - Environment, structure, Git and GitHub`.

Next block: `Block 1 - Historical research and dataset foundation`.
