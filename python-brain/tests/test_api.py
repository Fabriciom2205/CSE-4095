"""Typed HTTP contract, auth, persistence, and deterministic proposal checks."""

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Barrier
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from google.adk.events import Event, EventActions
from google.adk.models.google_llm import Gemini
from google.adk.models.llm_response import LlmResponse
from google.genai import types

from adk_runtime import AdkRuntime, Citation, USER
from api import create_app
from propose import Proposal
from research_visuals import ResearchVisual, VisualTurn
from tests.test_backtest import year_fixture

TOKEN = {"Authorization": "Bearer test-token"}
SESSION = "1" * 32


class FakeRuntime:
    research = "research"
    proposals = "proposals"

    async def session(self, runner, session_id):
        if session_id not in (None, SESSION):
            raise LookupError()
        return SESSION

    async def events(self, runner, session_id, message, *, stream=False, visual=None):
        if visual is not None:
            visual.visuals.append(ResearchVisual(kind=visual.kind, symbol="NVDA", statement="income_statement",
                                                 title="NVDA income statement", unit="USD", columns=[], rows=[]))
        if stream:
            yield "delta", "Example"
        yield "final", ("Example answer", [Citation(source="SEC EDGAR", symbol="NVDA",
                                                     accession="0001045810-25-000023")])

    async def proposal(self, session_id, tickers, constraints):
        return Proposal.model_validate({"targets": [{
            "symbol": tickers[0], "target_weight": "0.2", "confidence": "0.5", "rationale": "Test evidence",
            "evidence": {"accessions": ["0001045810-25-000023"], "market_as_of": "2025-11-18T15:00:00Z"},
        }]})


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch.dict(os.environ, {"MONROE_API_TOKEN": "test-token"}))
        self.runtime = FakeRuntime()
        self.client = self.enterContext(TestClient(create_app(self.runtime)))

    def test_openapi_lists_every_route_with_auth_and_sse(self):
        spec = self.client.get("/openapi.json").json()
        self.assertEqual(set(spec["paths"]), {"/health", "/filings", "/research", "/research/transcribe",
                                             "/portfolio", "/proposals", "/backtest"})
        for route, operations in spec["paths"].items():
            if route != "/health":
                self.assertEqual(next(iter(operations.values()))["security"], [{"HTTPBearer": []}])
        self.assertIn("text/event-stream", spec["paths"]["/research"]["post"]["responses"]["200"]["content"])

    def test_transcription_is_authenticated_and_bounded_before_provider(self):
        path = "/research/transcribe"
        headers = {**TOKEN, "Content-Type": "audio/webm; codecs=opus"}
        with patch("voice.MAX_AUDIO_BYTES", 3), patch("voice.transcribe_question", return_value="Plot it.") as speech:
            self.assertEqual(self.client.post(path, content=b"x").status_code, 401)
            self.assertEqual(self.client.post(path, headers=TOKEN, content=b"x").status_code, 415)
            self.assertEqual(self.client.post(path, headers=headers, content=b"").status_code, 422)
            self.assertEqual(self.client.post(path, headers=headers, content=b"abcd").status_code, 413)
            speech.assert_not_called()
            response = self.client.post(path, headers=headers, content=b"abc")
        self.assertEqual(response.json(), {"transcript": "Plot it."})
        self.assertEqual(response.headers["cache-control"], "no-store")
        speech.assert_called_once_with(b"abc", "audio/webm")

    def test_proposal_sector_cap_combines_holdings_and_targets(self):
        account = {"environment": "paper", "status": "ACTIVE", "currency": "USD", "equity": "1000",
                   "cash": "700", "buying_power": "700"}
        holding = {"symbol": "AAPL", "asset_class": "us_equity", "side": "long", "quantity": "1",
                   "market_value": "300", "cost_basis": "300", "unrealized_pl": "0"}
        with patch("alpaca_client.get_account", return_value=account), \
             patch("alpaca_client.get_positions", return_value=[holding]), \
             patch("portfolio_sectors.classifications", return_value={"NVDA": "manufacturing", "AAPL": "manufacturing"}) as sectors:
            response = self.client.post("/proposals", headers=TOKEN,
                                        json={"tickers": ["NVDA"], "constraints": {"max_sector_weight": "0.4"}})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["breaches"][0]["subject"], "manufacturing")
        sectors.assert_called_once_with({"NVDA", "AAPL"})

    def test_missing_token_fails_closed_before_any_portfolio_read(self):
        with patch("alpaca_client.get_account") as read:
            self.assertEqual(self.client.get("/portfolio").status_code, 401)
            with patch.dict(os.environ, {"MONROE_API_TOKEN": ""}):
                self.assertEqual(self.client.get("/portfolio", headers=TOKEN).status_code, 503)
            read.assert_not_called()

    def test_filings_keywords_use_ticker_cik_for_search(self):
        with patch("sec_client.resolve_cik", return_value="0001045810"), \
             patch("sec_client.tool_full_text_search", return_value=[]) as search:
            response = self.client.get("/filings", params={"ticker": "NVDA", "q": "inventory", "form": "10-K"},
                                       headers=TOKEN)
        self.assertEqual(response.json(), {"filings": [], "truncated": False})
        search.assert_called_once_with("inventory", form_type="10-K", cik="0001045810")

    def test_research_accepts_figure_question_without_ticker(self):
        response = self.client.post("/research", json={"question": "What did Berkshire hold?"}, headers=TOKEN)
        self.assertEqual(response.status_code, 200)

    def test_research_session_and_sse(self):
        data = {"ticker": "NVDA", "question": "What did they disclose?"}
        response = self.client.post("/research", json=data, headers=TOKEN)
        self.assertEqual(response.json()["session_id"], SESSION)
        self.assertEqual(response.json()["citations"][0]["source"], "SEC EDGAR")
        self.assertNotIn("visuals", response.json())
        response = self.client.post("/research", json={**data, "session_id": SESSION},
                                    headers={**TOKEN, "Accept": "text/event-stream"})
        self.assertIn("event: delta", response.text)
        self.assertIn("event: final", response.text)
        self.assertNotIn('"visuals"', response.text)
        self.assertEqual(self.client.post("/research", json={**data, "session_id": "2" * 32},
                                          headers=TOKEN).status_code, 404)

    def test_research_visual_contract_in_json_and_sse(self):
        response = self.client.post("/research", json={"question": "Show revenue in a table."}, headers=TOKEN)
        self.assertEqual(response.json()["visuals"][0]["kind"], "table")
        response = self.client.post("/research", json={"question": "Compare revenue.", "visual": "bar"},
                                    headers={**TOKEN, "Accept": "text/event-stream"})
        events = [json.loads(event.split("data: ", 1)[1]) for event in response.text.strip().split("\n\n")]
        self.assertEqual(events[0], {"text": "Example"})
        self.assertEqual(events[-1]["visuals"][0]["kind"], "bar")
        schema = self.client.get("/openapi.json").json()["components"]["schemas"]
        self.assertIn("visuals", schema["ResearchResponse"]["properties"])
        self.assertIn("visual", schema["ResearchRequest"]["properties"])

    def test_portfolio_cache_and_proposal_breaches(self):
        account = {"environment": "paper", "status": "ACTIVE", "currency": "USD",
                   "equity": "1000", "cash": "1000", "buying_power": "1000", "external_account_id": "private"}
        with patch("alpaca_client.get_account", return_value=account) as read, \
             patch("alpaca_client.get_positions", return_value=[]):
            response = self.client.get("/portfolio", headers=TOKEN)
            self.assertEqual(response.json()["market_freshness"], "unknown")
            self.assertNotIn("external_account_id", response.json()["account"])
            response = self.client.post("/proposals", headers=TOKEN,
                                        json={"tickers": ["NVDA"], "constraints": {"max_name_weight": "0.1"}})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["proposals"][0]["symbol"], "NVDA")
        self.assertEqual(response.json()["breaches"][0]["limit"], "max_name_weight")
        self.assertEqual(response.json()["quotes"][0]["status"], "stale")
        read.assert_called_once()

    def test_proposal_checks_portfolio_before_running_agent(self):
        with patch("alpaca_client.get_account", side_effect=ValueError("Account unavailable")), \
             patch.object(self.runtime, "proposal", new_callable=AsyncMock) as proposal:
            response = self.client.post("/proposals", headers=TOKEN,
                                        json={"tickers": ["NVDA"], "constraints": {}})
        self.assertEqual(response.status_code, 502)
        proposal.assert_not_awaited()

    def test_proposal_drawdown_uses_database_peak_when_configured(self):
        account = {"environment": "paper", "status": "ACTIVE", "currency": "USD",
                   "equity": "1000", "cash": "1000", "buying_power": "1000", "external_account_id": "private"}
        with patch.dict(os.environ, {"MONROE_PORTFOLIO_READ_DSN": "reader", "MONROE_PEAK_EQUITY": "1000"}), \
             patch("alpaca_client.get_account", return_value=account), \
             patch("alpaca_client.get_positions", return_value=[]), \
             patch("portfolio_store.read_peak_equity", return_value=Decimal("1250")) as peak:
            response = self.client.post("/proposals", headers=TOKEN,
                                        json={"tickers": ["NVDA"], "constraints": {"max_drawdown": "0.1"}})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["breaches"][0]["limit"], "max_drawdown")
        self.assertEqual(peak.call_args.args[:2], ("paper", "private"))

    def test_replay_requires_known_snapshot_id(self):
        with TemporaryDirectory() as directory, patch.dict(os.environ, {"MONROE_SNAPSHOT_DIR": directory}):
            Path(directory, "test.json").write_text(json.dumps(year_fixture()))
            data = {"snapshot_id": "test", "strategy": {"symbols": ["TEST"]}}
            response = self.client.post("/backtest", json=data, headers=TOKEN)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["final_equity"], "8460")
            self.assertEqual(self.client.post("/backtest", json={**data, "snapshot_id": "../test"},
                                              headers=TOKEN).status_code, 422)


class SessionTests(unittest.IsolatedAsyncioTestCase):
    async def test_visual_tool_is_per_turn_and_uses_backend_figures(self):
        model_calls = []

        async def model(self, request, stream=False):
            enabled = "sec_statement_visual" in request.tools_dict
            model_calls.append(enabled)
            part = (types.Part.from_function_call(name="sec_statement_visual", args={
                "symbol": "NVDA", "statement": "income_statement", "line_items": ["revenue"],
                "period_ends": ["2025-01-26"],
            }) if enabled and model_calls == [False, True] else types.Part(text="Example answer."))
            yield LlmResponse(content=types.Content(role="model", parts=[part]))

        runtime = AdkRuntime("sqlite+aiosqlite:///:memory:", "test", "global")
        self.addAsyncCleanup(runtime.sessions.db_engine.dispose)
        session = await runtime.session(runtime.research, None)
        turn = VisualTurn("line")
        accession = "0001045810-25-000023"
        series = [{"period_end": "2025-01-26", "period": "annual", "lines": {"revenue": {
            "value": "123.45", "period_start": "2024-01-29", "sources": [
                {"accession": accession, "filed_at": "2025-02-26", "role": "reported"},
            ],
        }}}]
        with patch.object(Gemini, "generate_content_async", model), \
             patch("sec_client.resolve_cik", return_value="0001045810"), \
             patch("sec_statements.company_statements", return_value=series) as statement:
            _ = [event async for event in runtime.events(runtime.research, session, "Tell me about annual revenue.")]
            events = [event async for event in runtime.events(runtime.research, session, "Plot it.", visual=turn)]
            _ = [event async for event in runtime.events(runtime.research, session, "Explain the values.")]
        self.assertEqual(model_calls, [False, True, True, False])
        statement.assert_called_once()
        self.assertEqual(events[-1][1][1][0].accession, accession)
        self.assertEqual(turn.visuals[0].rows[0].cells["revenue"].value, Decimal("123.45"))

    async def test_adk_session_survives_reopening_database_and_is_scoped(self):
        with TemporaryDirectory() as directory:
            url = f"sqlite+aiosqlite:///{directory}/sessions.db"
            first = AdkRuntime(url, "test", "global")
            session_id = await first.session(first.research, None)
            session = await first.sessions.get_session(app_name=first.research.app_name, session_id=session_id, user_id=USER)
            await first.sessions.append_event(session, Event(author="system", actions=EventActions(
                state_delta={"test_marker": "survives"})))
            await first.sessions.db_engine.dispose()
            second = AdkRuntime(url, "test", "global")
            try:
                self.assertEqual(await second.session(second.research, session_id), session_id)
                session = await second.sessions.get_session(app_name=second.research.app_name,
                                                            session_id=session_id, user_id=USER)
                self.assertEqual(session.state["test_marker"], "survives")
                with self.assertRaises(LookupError):
                    await second.session(second.proposals, session_id)
            finally:
                await second.sessions.db_engine.dispose()

    async def test_direct_quote_uses_two_model_calls_and_preserves_citations(self):
        calls = []

        async def model(self, request, stream=False):
            calls.append(request)
            part = (types.Part.from_function_call(name="market_quote", args={"symbol": "NVDA"})
                    if len(calls) == 1 else types.Part(text="NVDA traded at $100."))
            yield LlmResponse(content=types.Content(role="model", parts=[part]),
                              usage_metadata=types.GenerateContentResponseUsageMetadata(prompt_token_count=50))

        runtime = AdkRuntime("sqlite+aiosqlite:///:memory:", "test", "global")
        self.addAsyncCleanup(runtime.sessions.db_engine.dispose)
        session_id = await runtime.session(runtime.research, None)
        with patch.object(Gemini, "generate_content_async", model), \
             patch("market_data.finnhub_quote", return_value={
                 "symbol": "NVDA", "price": 100, "as_of": "2026-11-23T15:30:00Z",
             }) as quote, self.assertLogs("adk_runtime", "INFO") as logs:
            events = [event async for event in runtime.events(runtime.research, session_id, "Quote NVDA")]
            self.assertEqual(events[-1][1][1][0].symbol, "NVDA")
            self.assertEqual(len(calls), 2)
            self.assertIn("model_calls=2 input_tokens=100", logs.output[0])
            quote.assert_called_once_with("NVDA")
            restored = [event async for event in runtime.events(runtime.research, session_id, "Repeat that")]
        self.assertEqual(restored[-1][1][1], events[-1][1][1])

    async def test_coordinator_and_specialist_share_model_budget(self):
        calls = []

        async def model(self, request, stream=False):
            calls.append(request)
            part = (types.Part.from_function_call(name="market_specialist", args={"request": "Compare quotes"})
                    if len(calls) == 1 else types.Part(text="Comparison."))
            yield LlmResponse(content=types.Content(role="model", parts=[part]))

        runtime = AdkRuntime("sqlite+aiosqlite:///:memory:", "test", "global")
        self.addAsyncCleanup(runtime.sessions.db_engine.dispose)
        session_id = await runtime.session(runtime.research, None)
        with patch.object(Gemini, "generate_content_async", model), patch("adk_runtime.MAX_MODEL_CALLS", 2):
            with self.assertRaisesRegex(RuntimeError, "Agent run failed"):
                async for _ in runtime.events(runtime.research, session_id, "Compare quotes"):
                    pass
        self.assertEqual(len(calls), 2)

    async def test_missing_history_does_not_reuse_prior_turn_citations(self):
        calls = []

        async def model(self, request, stream=False):
            calls.append(request)
            part = (types.Part.from_function_call(name="sec_query_filing_history", args={
                "symbol": "NVDA", "question": "What changed?",
            }) if len(calls) == 1 else types.Part(text="Historical filing indexes are unavailable."))
            yield LlmResponse(content=types.Content(role="model", parts=[part]))

        runtime = AdkRuntime("sqlite+aiosqlite:///:memory:", "test", "global")
        self.addAsyncCleanup(runtime.sessions.db_engine.dispose)
        session_id = await runtime.session(runtime.research, None)
        state = await runtime.sessions.get_session(app_name=runtime.research.app_name, user_id=USER,
                                                   session_id=session_id)
        await runtime.sessions.append_event(state, Event(author="system", actions=EventActions(
            state_delta={"citations": [{"source": "Finnhub", "symbol": "MSFT"}]})))
        with patch.object(Gemini, "generate_content_async", model), patch("mcp_server.sec_query_filing_history",
                return_value={"data": {"ticker": "NVDA", "filings": [], "excerpts": []}}):
            events = [event async for event in runtime.events(runtime.research, session_id, "What changed?")]
        self.assertEqual(events[-1][1][1], [])

    async def test_proposal_overlaps_filings_and_fetches_quotes_afterward(self):
        runtime = AdkRuntime("sqlite+aiosqlite:///:memory:", "test", "global")
        self.addAsyncCleanup(runtime.sessions.db_engine.dispose)
        barrier = Barrier(3)
        tickers = ["NVDA", "MSFT", "AAPL"]
        finished = set()
        quoted = set()

        def filing(symbol, question):
            barrier.wait(timeout=5)
            finished.add(symbol)
            return Citation(source="SEC EDGAR", accession="0001045810-25-000023"), "Evidence"

        async def quote(symbol):
            self.assertEqual(finished, set(tickers))
            quoted.add(symbol)
            return {"citation": {"as_of": "2026-11-23T15:30:00Z"}, "price": 100}

        async def events(runner, session, message):
            self.assertEqual(quoted, set(tickers))
            self.assertEqual(list(json.loads(message)["untrusted_public_evidence"]), tickers)
            yield "final", ('{"targets":[]}', [])

        with patch("adk_runtime.filing_evidence", filing), patch("adk_runtime.market_quote", quote), \
             patch.object(runtime, "events", events):
            proposal = await asyncio.wait_for(runtime.proposal(SESSION, tickers, {}), timeout=10)
        self.assertEqual(proposal.targets, [])
