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
    # The script writes a `lets` shim and runs `lets add <role>` so a fresh
    # user is fully authorized AND has a background gateway after one
    # curl-bash run (no second manual step needed).
    assert '"$LETS_HOME/bin/lets" add' in body
    assert '"$LETS_HOME/bin/lets" install --host "$BASE_URL"' in body
    assert "$LETS_HOME/bin/lets" in body


def test_gateway_source_download(client):
    res = client.get("/install/gateway.py")
    assert res.status_code == 200
    assert "def main(" in res.text
    assert 'parser = argparse.ArgumentParser(prog="lets run")' in res.text
