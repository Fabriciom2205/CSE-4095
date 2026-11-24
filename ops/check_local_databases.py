"""Wait for the local API's configured conversations and SEC database connections."""

import asyncio
import os
from pathlib import Path
from time import monotonic, sleep

from dotenv import load_dotenv
import psycopg
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def check_sessions(dsn):
    engine = create_async_engine(dsn, connect_args={"timeout": 3, "command_timeout": 3})
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    finally:
        await engine.dispose()


def check_sec(dsn):
    with psycopg.connect(dsn, connect_timeout=3) as connection:
        connection.execute("SET LOCAL statement_timeout = '3s'")
        connection.execute("SELECT id FROM sec.filing_retrieval_index LIMIT 1")


def main():
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    sessions = os.getenv("MONROE_SESSION_DSN")
    reader = os.getenv("SEC_RAG_READ_DSN") or os.getenv("SEC_DB_READ_DSN")
    if not all((sessions, reader, os.getenv("MONROE_API_TOKEN"), os.getenv("GOOGLE_CLOUD_PROJECT"))):
        raise SystemExit("Configure the session DSN, SEC reader DSN, API token and Cloud project in .env.")
    if not sessions.startswith("postgresql+asyncpg://"):
        raise SystemExit("The local Cloud SQL service requires a PostgreSQL asyncpg session DSN.")

    deadline = monotonic() + 25
    while True:
        database = "conversation"
        try:
            asyncio.run(check_sessions(sessions))
            database = "SEC"
            check_sec(reader)
        except Exception as error:
            if monotonic() >= deadline:
                raise SystemExit(f"The {database} database check failed ({type(error).__name__}).") from None
            sleep(1)
        else:
            print("Conversation and SEC database connections are ready.")
            return


if __name__ == "__main__":
    main()
