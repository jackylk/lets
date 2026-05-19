def test_mcp_endpoint_mounted(client):
    """The MCP streamable-http endpoint should be reachable under /mcp."""
    response = client.get("/mcp/")

    assert response.status_code != 404, f"MCP endpoint not mounted; got 404"


def test_mcp_endpoint_requires_auth(client):
    """MCP POST without Bearer should be 401."""
    response = client.post(
        "/mcp/",
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {},
        },
    )

    assert response.status_code in (401, 403)


def test_mcp_tools_list_with_auth(client):
    """With valid Bearer, MCP tools/list should return registered tools."""
    from app.auth import issue_token
    from app.identity import ensure_human

    human_id = ensure_human("admin")
    token, _ = issue_token(human_id=human_id, label="mcp-test")
    response = client.post(
        "/mcp/",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json, text/event-stream",
        },
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {},
        },
    )

    assert response.status_code == 200
    assert "tools" in response.text or "result" in response.text
