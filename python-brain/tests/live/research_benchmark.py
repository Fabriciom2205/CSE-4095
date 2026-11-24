"""Run a cold and warm filing-plus-quote benchmark with live providers."""

import argparse
import asyncio
from collections import Counter
import json
import logging
import os
import re
from threading import Lock
from time import monotonic
from unittest.mock import patch

from google.genai.models import Models

from adk_runtime import AdkRuntime
from propose import SYMBOL


async def benchmark(tickers):
    runtime = AdkRuntime("sqlite+aiosqlite:///:memory:", os.environ["GOOGLE_CLOUD_PROJECT"],
                         os.getenv("GOOGLE_CLOUD_LOCATION", "global"))
    metrics = Counter()
    lock = Lock()
    embed = Models.embed_content

    def measure_embedding(self, *args, **kwargs):
        with lock:
            metrics["requests"] += 1
        result = embed(self, *args, **kwargs)
        with lock:
            if result.metadata and result.metadata.billable_character_count is not None:
                metrics["billable_characters"] += result.metadata.billable_character_count
            for vector in result.embeddings or []:
                if vector.statistics and vector.statistics.token_count is not None:
                    metrics["input_tokens"] += vector.statistics.token_count
        return result

    try:
        with patch.object(Models, "embed_content", measure_embedding):
            for ticker in tickers:
                for cache in ("cold", "warm"):
                    metrics.clear()
                    session = await runtime.session(runtime.research, None)
                    started = monotonic()
                    request = (f"Ticker: {ticker}\nQuestion: What material operating risk does the latest "
                               "annual filing disclose, and what is the latest quoted stock price and its as-of time?")
                    async for kind, result in runtime.events(runtime.research, session, request):
                        if kind == "final":
                            answer, citations = result
                    if not any(c.accession and c.symbol == ticker for c in citations) or not any(
                        c.source == "Finnhub" and c.as_of and c.symbol == ticker for c in citations
                    ):
                        raise RuntimeError(f"{ticker} {cache} run did not cite both filing and quote evidence")
                    print(json.dumps({"ticker": ticker, "cache": cache, "elapsed_seconds": round(monotonic()-started, 3),
                                      "embeddings": dict(metrics), "answer": answer,
                                      "citations": [c.model_dump(exclude_none=True) for c in citations]}), flush=True)
    finally:
        await runtime.research.close()
        await runtime.proposals.close()
        await runtime.sessions.db_engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tickers", nargs="+")
    args = parser.parse_args()
    tickers = list(dict.fromkeys(symbol.upper() for symbol in args.tickers))
    if len(tickers) > 3 or any(not re.fullmatch(SYMBOL, symbol) for symbol in tickers):
        parser.error("Provide one to three distinct ticker symbols")
    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("adk_runtime").setLevel(logging.INFO)
    # Use isolated memory indexes and sessions so the benchmark cannot write to deployed databases.
    with patch.dict(os.environ, dict.fromkeys(("SEC_DB_READ_DSN", "SEC_RAG_READ_DSN", "SEC_RAG_WRITE_DSN"), "")):
        asyncio.run(benchmark(tickers))


if __name__ == "__main__":
    main()
