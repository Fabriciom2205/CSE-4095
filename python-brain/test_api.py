"""Typed HTTP contract, auth, persistence, and deterministic proposal checks."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from google.adk.events import Event, EventActions

from adk_runtime import AdkRuntime, Citation, USER
from api import create_app
from propose import Proposal
from test_backtest import year_fixture

TOKEN = {"Authorization": "Bearer test-token"}
SESSION = "1" * 32


class FakeRuntime:
    research = "research"
    proposals = "proposals"

    async def session(self, runner, session_id):
        if session_id not in (None, SESSION):
            raise LookupError()
        return SESSION

    async def events(self, runner, session_id, message, *, stream=False):
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
        self.assertEqual(set(spec["paths"]), {"/health", "/filings", "/research", "/portfolio", "/proposals", "/backtest"})
        for route, operations in spec["paths"].items():
            if route != "/health":
                self.assertEqual(next(iter(operations.values()))["security"], [{"HTTPBearer": []}])
        self.assertIn("text/event-stream", spec["paths"]["/research"]["post"]["responses"]["200"]["content"])

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

    def test_research_session_and_sse(self):
        data = {"ticker": "NVDA", "question": "What did they disclose?"}
        response = self.client.post("/research", json=data, headers=TOKEN)
        self.assertEqual(response.json()["session_id"], SESSION)
        self.assertEqual(response.json()["citations"][0]["source"], "SEC EDGAR")
        response = self.client.post("/research", json={**data, "session_id": SESSION},
                                    headers={**TOKEN, "Accept": "text/event-stream"})
        self.assertIn("event: delta", response.text)
        self.assertIn("event: final", response.text)
        self.assertEqual(self.client.post("/research", json={**data, "session_id": "2" * 32},
                                          headers=TOKEN).status_code, 404)

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
