"""Dev-only CLI to mint a browser session cookie without going through GitHub OAuth.

Useful for local smoke testing and Playwright real-mode E2E
(``LETS_REAL_SESSION``). NEVER ship a UI that exposes this — the OAuth
callback is the only flow used in production.

Usage:
    python -m app.sessions_cli issue --human Neo
    # → prints a value; paste into the browser DevTools cookie
    #   `lets_session=<value>` for `http://127.0.0.1:8000`
"""
from __future__ import annotations

import argparse
import sys

from .auth import issue_session, revoke_session
from .db import init_db
from .identity import ensure_human


def cmd_issue(args: argparse.Namespace) -> int:
    init_db()
    human_id = ensure_human(args.human)
    value = issue_session(human_id)
    if args.cookie_line:
        print(f"lets_session={value}; Path=/; HttpOnly; SameSite=Lax")
    else:
        print(value)
    return 0


def cmd_revoke(args: argparse.Namespace) -> int:
    init_db()
    revoke_session(args.value)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="app.sessions_cli")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_issue = sub.add_parser("issue", help="Mint a session for a human")
    p_issue.add_argument("--human", required=True, help="Human name (will be created if missing)")
    p_issue.add_argument(
        "--cookie-line",
        action="store_true",
        help="Print as Set-Cookie line instead of the raw value",
    )
    p_issue.set_defaults(func=cmd_issue)

    p_revoke = sub.add_parser("revoke", help="Revoke a session by raw value")
    p_revoke.add_argument("--value", required=True)
    p_revoke.set_defaults(func=cmd_revoke)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
