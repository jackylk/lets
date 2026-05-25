def test_gateway_install_script_uses_public_base_url(client):
    res = client.get(
        "/install/gateway.sh",
        headers={
            "host": "lets.up.railway.app",
            "x-forwarded-proto": "https",
        },
    )
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/x-shellscript")
    body = res.text
    assert 'BASE_URL="${LETS_HOST:-https://lets.up.railway.app}"' in body
    assert 'curl -fsSL "$BASE_URL/install/gateway.py"' in body
    # Installing the command should not assume the user has Claude Code or
    # Codex installed locally, and should not start any agent process.
    assert '"$LETS_HOME/bin/lets" add' not in body
    assert '"$LETS_HOME/bin/lets" install --host "$BASE_URL"' not in body
    assert "lets add claude" in body
    assert "lets add codex" in body
    assert "lets add cc-deepseek" in body
    assert "lets add cc-doubao" in body
    assert "$LETS_HOME/bin/lets" in body


def test_gateway_source_download(client):
    res = client.get("/install/gateway.py")
    assert res.status_code == 200
    assert "def main(" in res.text
    assert 'parser = argparse.ArgumentParser(prog="lets run")' in res.text
