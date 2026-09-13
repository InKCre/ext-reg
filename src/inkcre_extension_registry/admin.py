"""Operator commands. Credentials are read through stdin and stored only as SHA-256."""

import argparse
import asyncio
import hashlib
import os
import sys

from tortoise.context import TortoiseContext
from tortoise.transactions import in_transaction

from .contracts.models import validate_segment
from .service.database import Credential, Namespace
from .service.settings import database_config


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("grant", "revoke"))
    parser.add_argument("namespace", type=validate_segment)
    parser.add_argument("--label", required=True)
    args = parser.parse_args()
    url = os.environ.get("MIGRATION_DATABASE_URL") or os.environ["DATABASE_URL"]
    async with TortoiseContext() as context:
        await context.init(config=database_config(url))
        async with in_transaction():
            if args.operation == "grant":
                token = sys.stdin.readline().strip()
                if not 24 <= len(token) <= 512:
                    raise ValueError("Provide a random publisher credential through stdin")
                namespace, _ = await Namespace.get_or_create(name=args.namespace)
                await Credential.filter(namespace=namespace, label=args.label).update(disabled=True)
                await Credential.update_or_create(
                    token_hash=hashlib.sha256(token.encode()).hexdigest(),
                    defaults={"namespace": namespace, "label": args.label, "disabled": False},
                )
            else:
                await Credential.filter(namespace_id=args.namespace, label=args.label).update(
                    disabled=True
                )
    print(f"{args.operation}: {args.namespace} / {args.label}")


if __name__ == "__main__":
    asyncio.run(main())
