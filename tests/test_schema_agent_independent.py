import pytest
from app import db

def test_agent_instances_has_new_columns():
    """Verify agent_instances has owner_human_id, display_name, paused_at, deleted_at, no workspace_id"""
    with db.connect() as conn:
        cur = conn.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'agent_instances'
        """)
        cols = {r["column_name"] for r in cur.fetchall()}

    assert 'owner_human_id' in cols, "human_id renamed to owner_human_id"
    assert 'display_name' in cols
    assert 'paused_at' in cols
    assert 'deleted_at' in cols
    assert 'workspace_id' not in cols, "workspace_id dropped"

def test_workspace_agent_members_exists():
    with db.connect() as conn:
        cur = conn.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'workspace_agent_members'
        """)
        cols = {r["column_name"] for r in cur.fetchall()}

    assert cols >= {'workspace_id', 'agent_instance_id', 'joined_at', 'joined_by_human_id'}

def test_agent_instances_unique_constraint():
    with db.connect() as conn:
        cur = conn.execute("""
            SELECT indexname FROM pg_indexes
            WHERE tablename = 'agent_instances' AND indexname LIKE '%owner_role_device%'
        """)
        names = {r["indexname"] for r in cur.fetchall()}

    assert 'agent_instances_owner_role_device_key' in names
