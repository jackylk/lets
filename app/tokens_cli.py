"""Token issuance CLI.

Usage:
    python -m app.tokens_cli issue --human Neo
    python -m app.tokens_cli issue --human Neo --role claude --device neo-mbp
    python -m app.tokens_cli list --human Neo
    python -m app.tokens_cli revoke --id 5
"""
from __future__ import annotations

import argparse
import sys

from .auth import issue_token, list_tokens, revoke_token
from .db import init_db
from .identity import ensure_agent_instance, ensure_human


def cli_issue(
    human: str,
    role: str | None,
    device: str | None,
    label: str | None,
) -> None:
    human_id = ensure_human(human)
    agent_instance_id: int | None = None
    if role and device:
        agent_instance_id = ensure_agent_instance(
            role=role,
            human_id=human_id,
            device_label=device,
        )

    plaintext, token_id = issue_token(
        human_id=human_id,
        agent_instance_id=agent_instance_id,
        label=label,
    )
    print(plaintext)
    print(
        f"token_id={token_id} human={human} role={role or '-'} "
        f"device={device or '-'} label={label or '-'}",
        file=sys.stderr,
    )


def cli_list(human: str | None) -> None:
    human_id: int | None = None
    if human:
        human_id = ensure_human(human)

    for token in list_tokens(human_id=human_id):
        revoked = "(revoked)" if token["revoked_at"] else ""
        print(
            f"#{token['id']:>4}  human={token['human_id']}  "
            f"ai={token['agent_instance_id'] or '-':<4}  "
            f"label={token['label'] or '-':<24}  "
            f"last_used={token['last_used_at'] or 'never':<20}  {revoked}"
        )


def cli_revoke(token_id: int) -> None:
    revoke_token(token_id)
    print(f"revoked token #{token_id}")


def main(argv: list[str] | None = None) -> int:
    init_db()
    parser = argparse.ArgumentParser(prog="lets-tokens")
    subcommands = parser.add_subparsers(dest="cmd", required=True)

    issue_parser = subcommands.add_parser("issue")
    issue_parser.add_argument("--human", required=True)
    issue_parser.add_argument("--role", default=None)
    issue_parser.add_argument("--device", default=None)
    issue_parser.add_argument("--label", default=None)

    list_parser = subcommands.add_parser("list")
    list_parser.add_argument("--human", default=None)

    revoke_parser = subcommands.add_parser("revoke")
    revoke_parser.add_argument("--id", type=int, required=True)

    args = parser.parse_args(argv)
    if args.cmd == "issue":
        cli_issue(args.human, args.role, args.device, args.label)
    elif args.cmd == "list":
        cli_list(args.human)
    elif args.cmd == "revoke":
        cli_revoke(args.id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
