# Validation Guide

## General validation

Run:

git status
git diff

## Python validation

Run:

python --version
python -m compileall .
python main.py

When using a virtual environment:

python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip

## Node validation

Run:

node --version
npm --version
node test-node.js

For frontend projects:

npm install
npm run build
npm run lint

## Docker validation

If Docker Desktop socket permissions fail, run:

~/Scripts/fix-docker-desktop-socket.sh

Then run:

docker --version
docker compose version
docker run --rm alpine echo "Docker environment ready from WSL2"

## Manual UI validation

When frontend changes are made, manually check:

- page loads correctly;
- layout is not broken;
- responsive/mobile view works;
- existing navigation still works;
- forms still submit correctly;
- no console errors;
- no existing feature disappeared.
