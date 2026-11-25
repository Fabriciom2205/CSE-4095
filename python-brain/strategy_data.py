"""Historical inputs for portfolio ranking strategies."""

from datetime import date, timedelta
from decimal import Decimal

import market_data
import sec_client


def annual_fundamentals(symbol):
    cik = sec_client.resolve_cik(symbol)
    facts = sec_client.company_facts(cik)["facts"].get("us-gaap", {})
    filings = {}
    for label, tag, unit in (
        ("income", "NetIncomeLoss", "USD"),
        ("assets", "Assets", "USD"),
        ("eps", "EarningsPerShareDiluted", "USD/shares"),
    ):
        for row in facts.get(tag, {}).get("units", {}).get(unit, []):
            if row["form"] not in ("10-K", "10-K/A"):
                continue
            end = date.fromisoformat(row["end"])
            filed = date.fromisoformat(row["filed"])
            if end > filed:
                continue
            if label != "assets" and not 330 <= (end - date.fromisoformat(row["start"])).days <= 380:
                continue
            key = (row["end"], row["filed"], row["accn"])
            filings.setdefault(key, {})[label] = str(row["val"])
    return [
        {"period_end": end, "filed": filed, "accession": accession, **values}
        for (end, filed, accession), values in sorted(filings.items())
        if len(values) == 3 and Decimal(values["assets"]) > 0
    ]


def capture_signals(strategy, start, end):
    if strategy.kind == "quality_value":
        return {"fundamentals": {symbol: annual_fundamentals(symbol) for symbol in strategy.symbols}}
    if strategy.kind == "sentiment":
        since = date.fromisoformat(start) - timedelta(days=30)
        return {"news_sentiment": {
            symbol: market_data.massive_news_sentiment(symbol, since, date.fromisoformat(end))
            for symbol in strategy.symbols
        }}
    return {}


def rank_scores(values):
    """Convert raw metrics to comparable ranks, sharing the same rank on ties."""
    ordered = sorted(values.values())
    return {symbol: ordered.index(value) for symbol, value in values.items()}


def select_symbols(strategy, day, closes, signals):
    if strategy.kind == "quality_value":
        quality, value = {}, {}
        for symbol in closes:
            rows = [row for row in signals[symbol]
                    if date.fromisoformat(row["filed"]) < day
                    and day - timedelta(days=550) <= date.fromisoformat(row["period_end"])
                    <= date.fromisoformat(row["filed"])]
            if rows:
                row = max(rows, key=lambda row: (row["period_end"], row["filed"], row["accession"]))
                assets = Decimal(row["assets"])
                if not assets.is_finite() or assets <= 0:
                    raise ValueError("Invalid annual asset value in snapshot")
                income, eps = Decimal(row["income"]), Decimal(row["eps"])
                if not income.is_finite() or not eps.is_finite():
                    raise ValueError("Invalid annual income or earnings per share in snapshot")
                quality[symbol] = income / assets
                value[symbol] = eps / closes[symbol][-1]
        first, second = rank_scores(quality), rank_scores(value)
        scores = {symbol: first[symbol] + second[symbol] for symbol in quality}
    else:
        scores = {symbol: values[-1] / values[-strategy.lookback_sessions] - 1
                  for symbol, values in closes.items()}
        if strategy.kind == "sentiment":
            sentiment = {}
            for symbol in scores:
                # shortcut: use a one-day publication lag; use observed feed arrival times when archived.
                labels = [row["score"] for row in signals[symbol]
                          if day - timedelta(days=30) <= date.fromisoformat(row["published"]) < day]
                if labels:
                    sentiment[symbol] = Decimal(sum(labels)) / len(labels)
            momentum_rank = rank_scores({symbol: scores[symbol] for symbol in sentiment})
            sentiment_rank = rank_scores(sentiment)
            scores = {symbol: momentum_rank[symbol] + sentiment_rank[symbol] for symbol in sentiment}
    return sorted(scores, key=lambda symbol: (-scores[symbol], symbol))[:strategy.top_n]
