"""
Reset the memory subsystem database tables.

Strict scope (team decision): only long-term memory layers are cleared.
    - semantic_memories
    - episodic_memories
    - user_profiles
    - consolidation_log
    - memories (legacy table)

Tables that do not exist (e.g. pgvector is not installed) are skipped with a
warning. Chat history (conversations/messages), emotional state
(emotional_history), tasks, and users are left untouched.

Usage:
    python scripts/reset_memory.py --dry-run   # show what would be cleared
    python scripts/reset_memory.py --yes       # clear without confirmation
    python scripts/reset_memory.py             # confirm interactively
"""
import argparse
import asyncio

from sqlalchemy import text

from backend.core.database import engine

STRICT_TABLES = [
    "semantic_memories",
    "episodic_memories",
    "user_profiles",
    "consolidation_log",
    "memories",
]


async def table_exists(conn, table: str) -> bool:
    row = await conn.execute(
        text(f"SELECT to_regclass('public.{table}')")
    )
    return row.scalar() is not None


async def run(dry_run: bool) -> int:
    async with engine.connect() as conn:
        existing = [t for t in STRICT_TABLES if await table_exists(conn, t)]

        if not existing:
            print("No memory tables found — nothing to reset.")
            return 0

        print("Will reset the following tables:")
        for t in existing:
            print(f"  - {t}")

        if dry_run:
            print("\nDry run: no changes made.")
            return 0

        for t in existing:
            await conn.execute(
                text(f'TRUNCATE TABLE "{t}" RESTART IDENTITY CASCADE')
            )
        await conn.commit()
        print("\nReset complete.")

    return 0


async def _main(dry_run: bool) -> int:
    try:
        return await run(dry_run)
    finally:
        await engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reset memory subsystem database tables (strict scope)."
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="only show what would be reset, make no changes",
    )
    parser.add_argument(
        "-y", "--yes", action="store_true",
        help="skip the confirmation prompt",
    )
    args = parser.parse_args()

    if not args.dry_run and not args.yes:
        answer = input("This clears all long-term memory data. Continue? [y/N] ")
        if answer.strip().lower() not in ("y", "yes"):
            print("Aborted.")
            return 1

    return asyncio.run(_main(args.dry_run))


if __name__ == "__main__":
    raise SystemExit(main())
