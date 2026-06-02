from __future__ import annotations

from collections.abc import Iterable

import asyncpg


async def _fetch_column_names(pool: asyncpg.Pool, table_schema: str, table_name: str) -> set[str]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = $1 AND table_name = $2
            """,
            table_schema,
            table_name,
        )
    return {row["column_name"] for row in rows}


async def _fetch_constraint_names(
    pool: asyncpg.Pool,
    constraint_names: Iterable[str],
    table_schema: str = "hermes",
    table_name: str = "topics",
) -> set[str]:
    wanted = list(constraint_names)
    if not wanted:
        return set()

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT conname
            FROM pg_constraint
            WHERE connamespace = $1::regnamespace
              AND conrelid = $2::regclass
              AND conname = ANY($3::text[])
            """,
            table_schema,
            f"{table_schema}.{table_name}",
            wanted,
        )
    return {row["conname"] for row in rows}


async def inspect_topic_schema(pool: asyncpg.Pool) -> dict[str, bool]:
    columns = await _fetch_column_names(pool, "hermes", "topics")
    constraints = await _fetch_constraint_names(
        pool,
        (
            "fk_topics_revisit_of",
            "chk_topics_revisit_of_not_self",
        ),
    )

    return {
        "topic_bucket": "embedding" in columns,
        "topic_revisit_of": {"revisit_of", "mother_theme"}.issubset(columns)
        and "fk_topics_revisit_of" in constraints
        and "chk_topics_revisit_of_not_self" in constraints,
        "list_revisit_chain": "revisit_of" in columns,
    }
