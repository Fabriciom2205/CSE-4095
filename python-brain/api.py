"""Authenticated Phase 5 application API. Execution remains a local CLI."""

import asyncio
from contextlib import aclosing, asynccontextmanager
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from hmac import compare_digest
import json
import os
from pathlib import Path
from time import monotonic
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, StringConstraints, model_serializer

import alpaca_client
import backtest
import portfolio_store
import portfolio_sectors
import sec_client
import voice
from adk_runtime import AdkRuntime, Citation
from portfolio_view import PortfolioView
from propose import SYMBOL, Target, UnitFraction, proposal_breaches
from research_visuals import ResearchVisual, VisualKind, VisualTurn, requested_visual
from risk import Position, RiskLimits, concentration
from strategy import Strategy

Symbol = Annotated[str, StringConstraints(pattern=SYMBOL)]
SessionID = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{32}$")]
SnapshotID = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_-]{1,80}$")]
PositiveAmount = Annotated[Decimal, Field(gt=0, allow_inf_nan=False)]
Amount = Annotated[Decimal, Field(ge=0, allow_inf_nan=False)]
CACHE_SECONDS = 15
QUOTE_SECONDS = 120


class Payload(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Health(BaseModel):
    status: str


class Filing(BaseModel):
    cik: str
    accession_number: str
    form: str
    filing_date: date
    report_date: date | None = None
    url: str | None = None
    snippet: str | None = None


class Filings(BaseModel):
    filings: list[Filing]
    truncated: bool


class ResearchRequest(Payload):
    ticker: Symbol | None = None
    question: str = Field(min_length=1, max_length=voice.MAX_QUESTION_LENGTH)
    session_id: SessionID | None = None
    visual: VisualKind | None = Field(default=None, description="Explicitly request a table, bar chart, or line chart.")


class ResearchResponse(BaseModel):
    session_id: SessionID
    answer: str
    citations: list[Citation]
    visuals: list[ResearchVisual] | None = Field(default=None, description="Structured visuals for this turn, when requested and supported by data.")

    @model_serializer(mode="wrap")
    def omit_absent_visuals(self, serialize):
        data = serialize(self)
        if self.visuals is None:
            data.pop("visuals", None)
        return data


class Transcription(BaseModel):
    transcript: str = Field(min_length=1, max_length=voice.MAX_QUESTION_LENGTH)


class Account(BaseModel):
    _external_account_id: str | None = PrivateAttr(default=None)
    environment: str
    status: str
    currency: str
    equity: PositiveAmount
    cash: Decimal | None
    buying_power: Decimal | None


class Holding(BaseModel):
    symbol: str
    asset_class: str
    side: str
    quantity: Decimal
    market_value: Decimal | None
    cost_basis: Decimal
    unrealized_pl: Decimal | None


class Exposure(BaseModel):
    gross_notional: Decimal
    name_weights: dict[str, Decimal]


class Portfolio(BaseModel):
    account: Account
    positions: list[Holding]
    exposure: Exposure | None
    retrieved_at: datetime
    age_seconds: float
    market_freshness: Literal["unknown"] = "unknown"


class Constraints(Payload):
    max_name_weight: UnitFraction | None = None
    max_sector_weight: UnitFraction | None = None
    max_order_notional: Amount | None = None
    max_gross_notional: Amount | None = None
    max_drawdown: UnitFraction | None = None


class ProposalRequest(Payload):
    tickers: list[Symbol] = Field(min_length=1, max_length=10)
    constraints: Constraints
    session_id: SessionID | None = None


class BreachFinding(BaseModel):
    limit: str
    actual: Decimal
    maximum: Decimal
    subject: str | None


class QuoteFreshness(BaseModel):
    symbol: str
    as_of: datetime
    status: Literal["fresh", "stale"]


class Proposals(BaseModel):
    session_id: SessionID
    proposals: list[Target]
    breaches: list[BreachFinding]
    portfolio_retrieved_at: datetime
    portfolio_market_freshness: Literal["unknown"] = "unknown"
    quotes: list[QuoteFreshness]


class BacktestRequest(Payload):
    strategy: Strategy
    snapshot_id: SnapshotID
    initial_cash: PositiveAmount = Decimal(10000)


class Fill(BaseModel):
    symbol: str
    side: Literal["buy", "sell"]
    quantity: int
    price: Decimal
    signal_date: date
    fill_date: date


class EquityPoint(BaseModel):
    date: date
    equity: Decimal


class BacktestResponse(BaseModel):
    source: str
    input_sha256: str
    start: date
    end: date
    strategy: Strategy
    initial_cash: Decimal
    final_cash: Decimal
    final_equity: Decimal
    max_drawdown: Decimal
    open_positions: dict[str, int]
    fills: list[Fill]
    equity_curve: list[EquityPoint]


def _filings(q, ticker, form):
    cik = sec_client.resolve_cik(ticker) if ticker else ""
    if not q:
        result = sec_client.filing_timeline(cik, form=form)
        return {"filings": [{"cik": cik, **row} for row in result["filings"]], "truncated": result["truncated"]}
    hits = sec_client.tool_full_text_search(q, form_type=form, cik=cik)
    rows = []
    for hit in hits:
        if not hit["adsh"] or not hit["file_date"] or not hit["cik"]:
            continue
        number = sec_client._validate_accession(hit["adsh"])
        filer = sec_client._validate_cik(hit["cik"])
        base = f"https://www.sec.gov/Archives/edgar/data/{int(filer)}/{number.replace('-', '')}"
        rows.append(Filing(cik=filer, accession_number=number, form=hit["form"], filing_date=hit["file_date"],
                           url=f"{base}/{number}-index.html", snippet=hit["snippet"]))
    return Filings(filings=rows, truncated=len(hits) == 10)


def _portfolio():
    raw_account = alpaca_client.get_account()
    account = Account.model_validate(raw_account)
    account._external_account_id = raw_account.get("external_account_id")
    positions = [Holding.model_validate(p) for p in alpaca_client.get_positions()]
    exposure = None
    if all(p.market_value is not None for p in positions):
        values = concentration((Position(p.symbol, None, p.market_value) for p in positions), account.equity)
        exposure = Exposure(gross_notional=values.gross_notional, name_weights=values.name_weights)
    return Portfolio(account=account, positions=positions, exposure=exposure,
                     retrieved_at=datetime.now(timezone.utc), age_seconds=0)


def _replay(data: BacktestRequest):
    root = Path(os.getenv("MONROE_SNAPSHOT_DIR", "snapshots")).resolve()
    path = (root / f"{data.snapshot_id}.json").resolve()
    if path.parent != root or not path.is_file():
        raise HTTPException(404, "Snapshot not found")
    with path.open("rb") as handle:
        raw = handle.read(2_000_001)
    if len(raw) > 2_000_000:
        raise HTTPException(422, "Snapshot exceeds replay size limit")
    try:
        return backtest.replay(data.strategy, json.loads(raw), data.initial_cash)
    except (ValueError, ArithmeticError, TypeError, KeyError):
        raise HTTPException(422, "Snapshot or strategy cannot be replayed") from None


def create_app(runtime=None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app):
        url = os.getenv("MONROE_SESSION_DSN")
        project = os.getenv("GOOGLE_CLOUD_PROJECT")
        app.state.runtime = runtime or (
            AdkRuntime(url, project, os.getenv("GOOGLE_CLOUD_LOCATION", "global")) if url and project else None
        )
        try:
            yield
        finally:
            if runtime is None and app.state.runtime:
                await app.state.runtime.research.close()
                await app.state.runtime.proposals.close()
                await app.state.runtime.sessions.db_engine.dispose()

    app = FastAPI(title="The Monroe Fund API", version="0.1.0", lifespan=lifespan)
    app.state.runtime = runtime
    bearer = HTTPBearer(auto_error=False)
    portfolio_lock = asyncio.Lock()
    cached = None
    cached_at = 0.0

    def authenticate(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]):
        secret = os.getenv("MONROE_API_TOKEN", "")
        if not secret:
            raise HTTPException(503, "API authentication is not configured")
        if not credentials or not compare_digest(credentials.credentials.encode(), secret.encode()):
            raise HTTPException(401, "Invalid bearer token", headers={"WWW-Authenticate": "Bearer"})

    def get_runtime():
        if app.state.runtime is None:
            raise HTTPException(503, "Agent runtime is not configured")
        return app.state.runtime

    async def get_session(service, runner, session_id):
        try:
            return await service.session(runner, session_id)
        except LookupError:
            raise HTTPException(404, "Conversation not found") from None
        except Exception:
            raise HTTPException(503, "Conversation storage unavailable") from None

    async def portfolio_data():
        nonlocal cached, cached_at
        async with portfolio_lock:
            if cached is None or monotonic() - cached_at >= CACHE_SECONDS:
                try:
                    cached = await asyncio.to_thread(_portfolio)
                except ValueError:
                    raise HTTPException(502, "Portfolio data unavailable") from None
                cached_at = monotonic()
            return cached.model_copy(update={"age_seconds": round(monotonic() - cached_at, 3)})

    @app.get("/health", response_model=Health, responses={503: {"model": Health}})
    async def health(response: Response):
        if not os.getenv("MONROE_API_TOKEN") or app.state.runtime is None:
            response.status_code = 503
            return Health(status="not_configured")
        return Health(status="ready")

    auth = [Depends(authenticate)]

    @app.post("/research/transcribe", response_model=Transcription, dependencies=auth,
              openapi_extra={"requestBody": {"required": True, "content": {
                  mime: {"schema": {"type": "string", "format": "binary"}} for mime in sorted(voice.AUDIO_TYPES)
              }}})
    async def transcribe(request: Request, response: Response):
        """Transcribe a recording for the operator to review and submit as a research question."""
        mime = request.headers.get("content-type", "").partition(";")[0].strip().lower()
        if mime not in voice.AUDIO_TYPES:
            raise HTTPException(415, "Unsupported audio format")
        audio = bytearray()
        async for chunk in request.stream():
            if len(audio) + len(chunk) > voice.MAX_AUDIO_BYTES:
                raise HTTPException(413, "Audio recording exceeds 4 MiB")
            audio.extend(chunk)
        if not audio:
            raise HTTPException(422, "Audio recording is empty")
        try:
            transcript = await asyncio.to_thread(voice.transcribe_question, bytes(audio), mime)
        except Exception:
            raise HTTPException(502, "Transcription unavailable") from None
        if not transcript or len(transcript) > voice.MAX_QUESTION_LENGTH:
            raise HTTPException(422, "The recording must contain a short, intelligible question")
        response.headers["Cache-Control"] = "no-store"
        return Transcription(transcript=transcript)

    @app.get("/filings", response_model=Filings, dependencies=auth)
    async def filings(q: Annotated[str, Query(max_length=2000)] = "",
                      ticker: Symbol | None = None,
                      form: Annotated[str, Query(pattern=r"^[A-Z0-9 /-]{0,32}$")] = ""):
        q = q.strip()
        if not q and not ticker:
            raise HTTPException(422, "Provide a keyword query or ticker")
        try:
            return await asyncio.to_thread(_filings, q, ticker, form)
        except Exception:
            raise HTTPException(502, "SEC filings unavailable") from None

    @app.post("/research", response_model=ResearchResponse, dependencies=auth, responses={
        200: {"content": {"text/event-stream": {"schema": {"type": "string"}}}}
    })
    async def research(data: ResearchRequest, request: Request):
        """Return JSON, or SSE when Accept is text/event-stream.

        Delta events contain {"text": "..."}; final contains the JSON response
        including session_id, citations and any requested visuals; error contains {"detail": "..."}.
        """
        service = get_runtime()
        session_id = await get_session(service, service.research, data.session_id)
        message = (f"Ticker: {data.ticker}\n" if data.ticker else "") + f"Question: {data.question}"
        kind = data.visual or requested_visual(data.question)
        visual = VisualTurn(kind) if kind else None
        if visual:
            message = f"Requested visual: {visual.kind}\n{message}"
        options = {"visual": visual} if visual else {}

        def result(value):
            return ResearchResponse(session_id=session_id, answer=value[0], citations=value[1],
                                    visuals=visual.visuals if visual and visual.visuals else None)

        if "text/event-stream" in request.headers.get("accept", ""):
            async def stream():
                try:
                    async with aclosing(service.events(service.research, session_id, message, stream=True, **options)) as events:
                        async for kind, value in events:
                            payload = result(value).model_dump(mode="json") if kind == "final" else {"text": value}
                            yield f"event: {kind}\ndata: {json.dumps(payload)}\n\n"
                except Exception:
                    yield 'event: error\ndata: {"detail":"Research unavailable"}\n\n'
            return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-store"})
        try:
            async for kind, value in service.events(service.research, session_id, message, **options):
                if kind == "final":
                    return result(value)
        except Exception:
            raise HTTPException(502, "Research unavailable") from None
        raise HTTPException(502, "Research did not return a response")

    @app.get("/portfolio", response_model=Portfolio, dependencies=auth)
    async def portfolio():
        return await portfolio_data()

    @app.post("/proposals", response_model=Proposals, dependencies=auth)
    async def proposals(data: ProposalRequest):
        limits = RiskLimits(**data.constraints.model_dump())
        if len(set(data.tickers)) != len(data.tickers):
            raise HTTPException(422, "Proposal symbols must be distinct")
        peak = None
        use_history = limits.max_drawdown is not None and bool(os.getenv("MONROE_PORTFOLIO_READ_DSN"))
        if limits.max_drawdown is not None and not use_history:
            try:
                peak = Decimal(os.getenv("MONROE_PEAK_EQUITY", ""))
                if not peak.is_finite() or peak <= 0:
                    raise InvalidOperation()
            except InvalidOperation:
                raise HTTPException(503, "Trusted historical peak equity is required for drawdown") from None
        service = get_runtime()
        session_id = await get_session(service, service.proposals, data.session_id)
        snapshot = await portfolio_data()
        if snapshot.exposure is None:
            raise HTTPException(422, "A position is missing a market value")

        async def stored_peak(state):
            try:
                return await asyncio.to_thread(portfolio_store.read_peak_equity, state.account.environment,
                                               state.account._external_account_id, state.retrieved_at)
            except ValueError:
                raise HTTPException(503, "Trusted historical peak equity is required for drawdown") from None

        async def stored_sectors(state):
            symbols = set(data.tickers) | {row.symbol for row in state.positions if row.market_value}
            try:
                return await asyncio.to_thread(portfolio_sectors.classifications, symbols)
            except ValueError as error:
                raise HTTPException(422, str(error)) from None

        if use_history:
            peak = await stored_peak(snapshot)
        sectors = await stored_sectors(snapshot) if limits.max_sector_weight is not None else None
        try:
            proposal = await service.proposal(session_id, data.tickers, data.constraints.model_dump(mode="json"))
        except Exception:
            raise HTTPException(502, "Validated proposal unavailable") from None
        state = await portfolio_data()
        if state.exposure is None:
            raise HTTPException(422, "A position is missing a market value")
        if use_history and snapshot.retrieved_at != state.retrieved_at:
            peak = await stored_peak(state)
        if sectors is not None and snapshot.retrieved_at != state.retrieved_at:
            sectors = await stored_sectors(state)
        equity = state.account.equity
        view = PortfolioView(equity, max(equity, peak or equity), tuple(
            Position(row.symbol, None, row.market_value) for row in state.positions
        ))
        findings = proposal_breaches(proposal, view, limits, sectors=sectors)
        now = datetime.now(timezone.utc)
        quotes = [QuoteFreshness(symbol=t.symbol, as_of=t.evidence.market_as_of, status=(
            "fresh" if 0 <= (now - t.evidence.market_as_of).total_seconds() <= QUOTE_SECONDS else "stale"
        )) for t in proposal.targets]
        return Proposals(session_id=session_id, proposals=proposal.targets,
                         breaches=[BreachFinding.model_validate(b, from_attributes=True) for b in findings],
                         portfolio_retrieved_at=state.retrieved_at, quotes=quotes)

    @app.post("/backtest", response_model=BacktestResponse, dependencies=auth)
    def replay(data: BacktestRequest):
        return _replay(data)

    return app


app = create_app()
