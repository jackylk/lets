import pytest
from app.workspaces import (
    slugify,
    create_workspace,
    list_workspaces_for_human,
    is_workspace_member,
    generate_invite_token,
)
from app.db import connect


def _make_human(name="alice", email=None):
    with connect() as conn:
        row = conn.execute(
            "INSERT INTO humans (name, email) VALUES (?, ?) RETURNING id",
            (name, email),
        ).fetchone()
    return int(row["id"])


def test_slugify_ascii(temp_db):
    assert slugify("User Auth") == "user-auth"
    assert slugify("API v2 Design!") == "api-v2-design"
    assert slugify("  Whitespace  ") == "whitespace"


def test_slugify_cjk_fallback(temp_db):
    s = slugify("用户认证")
    assert s.startswith("ws-")
    assert len(s) == 9  # "ws-" + 6 hex chars


def test_slugify_conflict_appends_counter(temp_db):
    hid = _make_human()
    create_workspace(name="User Auth", owner_human_id=hid)
    ws2 = create_workspace(name="User Auth", owner_human_id=hid)
    assert ws2["slug"] == "user-auth-2"


def test_create_workspace_returns_dict(temp_db):
    hid = _make_human()
    ws = create_workspace(name="User Auth", owner_human_id=hid)
    assert ws["id"] > 0
    assert ws["slug"] == "user-auth"
    assert ws["name"] == "User Auth"
    assert ws["owner_human_id"] == hid


def test_create_workspace_auto_adds_owner_member(temp_db):
    hid = _make_human()
    ws = create_workspace(name="User Auth", owner_human_id=hid)
    assert is_workspace_member(ws["id"], hid)


def test_list_workspaces_for_human(temp_db):
    a = _make_human("alice")
    b = _make_human("bob", "b@b")
    ws_a = create_workspace(name="A", owner_human_id=a)
    ws_b = create_workspace(name="B", owner_human_id=b)
    a_list = list_workspaces_for_human(a)
    assert [w["id"] for w in a_list] == [ws_a["id"]]
    b_list = list_workspaces_for_human(b)
    assert [w["id"] for w in b_list] == [ws_b["id"]]


def test_generate_invite_token_unique(temp_db):
    tokens = {generate_invite_token() for _ in range(50)}
    assert len(tokens) == 50
    for t in tokens:
        assert len(t) >= 20
