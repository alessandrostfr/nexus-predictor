"""API tests for Block 4 hard dance genre classification."""

from fastapi.testclient import TestClient

from app.core.paths import GENRE_OVERRIDES_PATH
from app.main import app

client = TestClient(app)


def test_genre_taxonomy_endpoint_returns_mvp_labels() -> None:
    """The taxonomy endpoint should expose the closed MVP hard dance labels."""
    response = client.get("/api/genres/taxonomy")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    names = [genre["name"] for genre in body["data"]["taxonomy"]]
    assert "Rawstyle" in names
    assert "Uptempo Hardcore" in names
    assert "Classic / Legacy Hardstyle" in names
    assert "Unknown" in names


def test_manual_override_wins_for_project_one() -> None:
    """Manual overrides should win over seed data and keyword rules."""
    response = client.get("/api/genres/artists/project-one")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["slug"] == "project-one"
    assert body["data"]["main_genre"] == "Classic / Legacy Hardstyle"
    assert body["data"]["genre_source"] == "manual_override"
    assert body["data"]["artist_kind"] == "duo_project"
    assert body["data"]["related_canonical_artists"] == ["Headhunterz", "Wildstylez"]


def test_2026_genre_artist_filter_returns_rawstyle_artists() -> None:
    """The 2026 lineup should be filterable by classified subgenre."""
    response = client.get("/api/genres/artists?year=2026&genre=Rawstyle&limit=100")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    slugs = {item["slug"] for item in body["data"]["items"]}
    assert "sub-zero-project" in slugs
    assert "phuture-noize" in slugs
    assert all(item["main_genre"] == "Rawstyle" for item in body["data"]["items"])


def test_2026_distribution_uses_classified_main_genres() -> None:
    """Edition genre distribution should use classified main_genre values."""
    response = client.get("/api/genres/editions/2026")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["year"] == 2026
    assert body["data"]["total_artists"] >= 60
    names = {item["name"] for item in body["data"]["distribution"]}
    assert "Rawstyle" in names
    assert "Uptempo Hardcore" in names
    assert "Unknown" in names


def test_special_show_is_not_mixed_with_main_artist() -> None:
    """Special shows should carry artist_kind metadata instead of being merged silently."""
    response = client.get("/api/genres/artists/spoontech-legacy")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["slug"] == "spoontech-legacy"
    assert body["data"]["is_special_show"] is True
    assert body["data"]["artist_kind"] == "label_show"
    assert body["data"]["related_canonical_artists"] == ["Faceless"]


def test_genre_overrides_file_exists() -> None:
    """Genre overrides should be versioned as editable project data."""
    assert GENRE_OVERRIDES_PATH.exists()
