def test_smoke_can_import():
    from app import db, main
    assert db is not None
    assert main is not None


def test_smoke_temp_db_works(temp_db):
    from app.db import connect
    with connect() as conn:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    table_names = {r["name"] for r in rows}
    assert "work_items" in table_names
    assert "agents" in table_names


def test_smoke_client_works(client):
    r = client.get("/api/context")
    assert r.status_code == 200
    assert r.json()["project"]["name"] == "Lets"
