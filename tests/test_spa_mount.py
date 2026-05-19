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
    """If LETS_FRONTEND_DIST is not set or dir missing, /app/ returns 404."""
    from fastapi.testclient import TestClient
    monkeypatch.delenv("LETS_FRONTEND_DIST", raising=False)

    import app.main as m
    importlib.reload(m)
    with TestClient(m.app) as c:
        r = c.get("/app/")
        assert r.status_code == 404
