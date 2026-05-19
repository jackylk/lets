"""Seed a Track F demo topic + a few messages against a running backend.

Usage:
    LETS_TOKEN=lets_xxx python scripts/seed-track-f-demo.py

The backend's mutating endpoints require a Bearer token (issued via the
auth flow). Read-only ``/api/identity/me`` accepts just ``X-Lets-Human``.

The plan's original draft assumed flat ``POST /api/topics`` endpoints;
the production backend only exposes the project-nested variant
(``POST /api/projects/{project_id}/topics``), so this script always
uses the project-nested form and creates a "demo" project on demand.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request


BASE = os.environ.get("LETS_API_BASE", "http://localhost:8000")
HUMAN = os.environ.get("LETS_HUMAN", "Neo")
TOKEN = os.environ.get("LETS_TOKEN")


def _headers(authed: bool) -> dict[str, str]:
    h = {
        "Content-Type": "application/json",
        "X-Lets-Human": HUMAN,
    }
    if authed:
        if not TOKEN:
            raise SystemExit(
                "LETS_TOKEN env var is required for mutating endpoints. "
                "Mint one via the v1.5 token flow and re-run."
            )
        h["Authorization"] = f"Bearer {TOKEN}"
    return h


def post(path: str, payload: dict, authed: bool = True) -> dict:
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(payload).encode("utf-8"),
        headers=_headers(authed),
        method="POST",
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def get(path: str, authed: bool = True) -> dict:
    req = urllib.request.Request(BASE + path, headers=_headers(authed))
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def _ensure_project() -> dict:
    """Return the demo project, creating it if missing."""
    projects = get("/api/projects")
    for p in projects:
        if p.get("slug") == "demo":
            return p
    try:
        return post(
            "/api/projects",
            {
                "name": "Demo",
                "slug": "demo",
                "description": "Seeded by seed-track-f-demo.py",
            },
        )
    except urllib.error.HTTPError as e:
        if e.code == 400:
            # Race: another seed created it.
            projects = get("/api/projects")
            for p in projects:
                if p.get("slug") == "demo":
                    return p
        raise


def _ensure_topic(project_id: int) -> dict:
    topics = get(f"/api/projects/{project_id}/topics")
    for t in topics:
        if t.get("slug") == "t-demo":
            return t
    try:
        return post(
            f"/api/projects/{project_id}/topics",
            {"slug": "t-demo", "title": "Track F demo topic"},
        )
    except urllib.error.HTTPError as e:
        if e.code in (400, 409):
            topics = get(f"/api/projects/{project_id}/topics")
            for t in topics:
                if t.get("slug") == "t-demo":
                    return t
        raise


def main() -> int:
    me = get("/api/identity/me", authed=False)
    print("identity:", me)

    project = _ensure_project()
    print("project:", project)

    topic = _ensure_topic(project["id"])
    print("topic:", topic)

    post(
        "/api/messages",
        {
            "topic_id": topic["id"],
            "type": "chat",
            "actor_type": "human",
            "actor_id": me["human"]["id"],
            "body": "demo seed: Neo says hi",
        },
    )
    post(
        "/api/messages",
        {
            "topic_id": topic["id"],
            "type": "spec_change",
            "actor_type": "human",
            "actor_id": me["human"]["id"],
            "body": "字号 10 → 14",
            "metadata": {
                "file": ".claude/skills/research-talk-style/SKILL.md",
                "before": 10,
                "after": 14,
                "approvers": [],
            },
        },
    )
    print("seeded.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
