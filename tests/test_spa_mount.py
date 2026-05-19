import importlib
import pytest


def test_spa_mount_serves_index(tmp_path, monkeypatch):
    """When LETS_FRONTEND_DIST points to a built dist dir, /app/ serves index.html."""
    from fastapi.testclient import TestClient
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html><body>Lets SPA</body></html>")
    monkeypatch.setenv("LETS_FRONTEND_DIST", str(dist))

    import app.main as m
    importlib.reload(m)
    with TestClient(m.app) as c:
        r = c.get("/app/")
        assert r.status_code == 200, f"got {r.status_code}: {r.text}"
        assert "Lets SPA" in r.text


def test_spa_mount_absent_when_no_dist(tmp_path, monkeypatch):
    """If LETS_FRONTEND_DIST points at a missing dir (and no fallback build),
    /app/ returns 404."""
    from fastapi.testclient import TestClient
    # Point env var at a non-existent dir so auto-discovery of
    # ``<repo>/frontend/dist`` (Track F Task 39) is bypassed.
    monkeypatch.setenv("LETS_FRONTEND_DIST", str(tmp_path / "nope"))

    import app.main as m
    importlib.reload(m)
    with TestClient(m.app) as c:
        r = c.get("/app/")
        assert r.status_code == 404
