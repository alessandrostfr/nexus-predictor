"""Validate the V3.0 predictive audit block.

This script is intentionally strict because V3.0 is the guardrail that prevents
Nexus Predictor V3 from calling scoring, heuristics or optimization "ML".

Run from the repository root:

    python backend/scripts/check_v3_predictive_audit.py

The script checks:
- the expected branch;
- the required V3.0 files;
- the audit and README content;
- the recorded V3 start commit;
- that no frontend runtime file is currently modified for V3.0.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


EXPECTED_BRANCH = "refactor/v3-ml-first"

REQUIRED_FILES = [
    Path("README_V3.md"),
    Path("docs/ROADMAP_POSITION.md"),
    Path("docs/v3-predictive-audit.md"),
    Path("docs/v3-0-closure-decisions.md"),
    Path("backend/scripts/check_v3_predictive_audit.py"),
]

README_REQUIRED_TERMS = [
    "ML-first",
    "Nothing is called ML",
    "training dataset",
    "validation metrics",
    "persisted predictions",
    "baseline_",
    "heuristic_",
    "scoring_",
    "optimizer_",
    "evidence_",
    "feature_",
    "proxy_",
    "refactor/v3-ml-first",
]

AUDIT_REQUIRED_TERMS = [
    "Executive verdict",
    "Predictive endpoint inventory",
    "Predictive service inventory",
    "Backend audit",
    "Data audit",
    "Frontend audit",
    "Pipeline audit",
    "Documentation audit",
    "Reusable assets list",
    "Pieces to replace or demote",
    "Predictive debt and rescue plan",
    "V3.0 validation checklist",
    "Real ML",
    "Baseline",
    "Scoring",
    "Heuristic",
    "Optimization",
    "Evidence/data",
    "Frontend-only",
]

AUDIT_REQUIRED_ENDPOINTS = [
    "/api/predictions/{year}",
    "/api/predictions/v2/{year}",
    "/api/probable-timetables/{year}",
    "/api/optimized-timetables/{year}",
    "/api/room-risk/{year}",
    "/api/evidence",
    "/api/spotify",
    "/api/historical-timetables",
]

AUDIT_REQUIRED_SERVICES = [
    "scoring_service.py",
    "prediction_service.py",
    "demand_model_service.py",
    "probable_timetable_service.py",
    "optimized_timetable_service.py",
    "room_risk_service.py",
    "historical_timetable_service.py",
    "evidence_service.py",
    "spotify_service.py",
    "multi_genre_service.py",
]

CLOSURE_REQUIRED_TERMS = [
    "V3_BRANCH=refactor/v3-ml-first",
    "PUBLIC_PRODUCT_NAME=Nexus Predictor",
    "TECHNICAL_SUBTITLE=V3 — ML-first",
    "CURRENT_V2_PREDICTIVE_LAYER_STATUS=not_final_ml",
    "V3_0_RUNTIME_POLICY=docs_and_audit_only",
    "NEXT_BLOCK=V3.1",
]


def run_git_command(args: list[str]) -> str:
    """Run a git command and return stdout.

    A clear error is raised if Git cannot run, because this block relies on
    branch and working-tree checks.
    """
    try:
        completed = subprocess.run(
            ["git", *args],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("Git is not available in PATH.") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(exc.stderr.strip() or f"git {' '.join(args)} failed") from exc

    return completed.stdout.strip()


def read_text(path: Path) -> str:
    """Read a UTF-8 text file with a consistent error message."""
    return path.read_text(encoding="utf-8")


def require(condition: bool, message: str, errors: list[str]) -> None:
    """Collect validation errors without stopping at the first one."""
    if not condition:
        errors.append(message)


def check_required_files(errors: list[str]) -> None:
    """Ensure every V3.0 deliverable file exists."""
    for path in REQUIRED_FILES:
        require(path.exists(), f"Missing required file: {path}", errors)


def check_terms(label: str, content: str, required_terms: list[str], errors: list[str]) -> None:
    """Ensure a document contains all required audit terms."""
    for term in required_terms:
        require(term in content, f"{label} is missing required term: {term}", errors)


def check_branch(errors: list[str]) -> None:
    """Validate the current Git branch."""
    branch = run_git_command(["branch", "--show-current"])
    require(
        branch == EXPECTED_BRANCH,
        f"Expected branch {EXPECTED_BRANCH!r}, got {branch!r}.",
        errors,
    )


def check_closure_decisions(content: str, errors: list[str]) -> None:
    """Validate the V3.0 closure decisions file.

    The start commit must be replaced manually because only the local repository
    knows the exact hash that existed before committing V3.0.
    """
    check_terms("docs/v3-0-closure-decisions.md", content, CLOSURE_REQUIRED_TERMS, errors)

    match = re.search(r"V3_START_COMMIT=([0-9a-fA-F]{7,40})", content)
    require(
        match is not None,
        "docs/v3-0-closure-decisions.md must contain a real V3_START_COMMIT hash.",
        errors,
    )

    require(
        "PENDING_REPLACE_WITH_GIT_REV_PARSE_HEAD" not in content,
        "Replace PENDING_REPLACE_WITH_GIT_REV_PARSE_HEAD with `git rev-parse HEAD` before committing V3.0.",
        errors,
    )


def check_no_frontend_runtime_changes(errors: list[str]) -> None:
    """V3.0 must not touch frontend runtime files.

    Documentation-only/frontend metadata is acceptable in future blocks, but this
    audit block should not change the visible product runtime.
    """
    status = run_git_command(["status", "--porcelain", "--", "frontend"])
    require(
        status == "",
        "V3.0 should not modify frontend runtime files. Current frontend changes:\n"
        f"{status or '<none>'}",
        errors,
    )


def main() -> int:
    """Run every V3.0 validation check."""
    errors: list[str] = []

    check_branch(errors)
    check_required_files(errors)

    # Stop content checks only if required files are missing.
    if errors:
        print("V3.0 predictive audit validation failed:\n", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    readme = read_text(Path("README_V3.md"))
    roadmap_position = read_text(Path("docs/ROADMAP_POSITION.md"))
    audit = read_text(Path("docs/v3-predictive-audit.md"))
    closure = read_text(Path("docs/v3-0-closure-decisions.md"))

    check_terms("README_V3.md", readme, README_REQUIRED_TERMS, errors)
    check_terms("docs/v3-predictive-audit.md", audit, AUDIT_REQUIRED_TERMS, errors)
    check_terms("docs/v3-predictive-audit.md", audit, AUDIT_REQUIRED_ENDPOINTS, errors)
    check_terms("docs/v3-predictive-audit.md", audit, AUDIT_REQUIRED_SERVICES, errors)
    check_closure_decisions(closure, errors)
    check_no_frontend_runtime_changes(errors)

    require(
        "V3.0 — Auditoría crítica y nueva rama ML-first" in roadmap_position,
        "docs/ROADMAP_POSITION.md must point to V3.0.",
        errors,
    )
    require(
        "V3.1 — Contrato real Nexus 2026 y calendario continuo" in roadmap_position,
        "docs/ROADMAP_POSITION.md must identify V3.1 as next block.",
        errors,
    )
    require(
        "does not modify the visible frontend" in audit or "does not modify runtime prediction behavior" in audit,
        "docs/v3-predictive-audit.md must explicitly state that V3.0 does not change runtime behavior.",
        errors,
    )

    if errors:
        print("V3.0 predictive audit validation failed:\n", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("V3.0 predictive audit validation passed.")
    print("Next required validation: run `pytest` from the backend directory.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
