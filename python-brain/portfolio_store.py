"""PostgreSQL audit and execution gate for the local paper runner."""

from contextlib import contextmanager
from hashlib import sha256
import json
import os

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from risk import RiskLimits


def json_data(value):
    return json.loads(json.dumps(value, default=str))


def digest(value):
    return sha256(json.dumps(json_data(value), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@contextmanager
def connect():
    dsn = os.getenv("MONROE_PORTFOLIO_DSN")
    if not dsn:
        raise ValueError("MONROE_PORTFOLIO_DSN is required for audited paper execution")
    try:
        with psycopg.connect(dsn, autocommit=True, row_factory=dict_row, connect_timeout=5) as conn:
            conn.execute("SET statement_timeout = '15s'")
            yield Ledger(conn)
    except psycopg.Error as error:
        raise ValueError(f"Portfolio database unavailable ({error.sqlstate or type(error).__name__})") from None


class Ledger:
    def __init__(self, conn):
        self.conn = conn

    def account(self, account):
        return self.conn.execute(
            """INSERT INTO portfolio.account
                   (provider, environment, external_account_id, status, currency, equity, cash, buying_power, observed_at)
               VALUES (%(provider)s, %(environment)s, %(external_account_id)s, %(status)s, %(currency)s,
                       %(equity)s, %(cash)s, %(buying_power)s, clock_timestamp())
               ON CONFLICT (provider, environment, external_account_id) DO UPDATE SET
                   status = excluded.status, currency = excluded.currency, equity = excluded.equity,
                   cash = excluded.cash, buying_power = excluded.buying_power, observed_at = excluded.observed_at
               RETURNING id""", account,
        ).fetchone()["id"]

    @contextmanager
    def lock(self, account_id):
        if not self.conn.execute("SELECT pg_try_advisory_lock(%s::bigint) AS locked", (account_id,)).fetchone()["locked"]:
            raise ValueError("Another execution or reconciliation is active for this account")
        try:
            yield
        finally:
            self.conn.execute("SELECT pg_advisory_unlock(%s::bigint)", (account_id,))

    def record_equity(self, account_id, value):
        self.conn.execute(
            "INSERT INTO portfolio.equity_snapshot VALUES (%s, clock_timestamp(), %s)", (account_id, value),
        )

    def controls(self, account_id):
        row = self.conn.execute("SELECT * FROM portfolio.risk_limit WHERE account_id = %s", (account_id,)).fetchone()
        if not row:
            raise ValueError("Configure trusted database risk limits for this paper account")
        order_count, notional = row["max_daily_orders"], row["max_daily_notional"]
        limits = RiskLimits(**{key: row[key] for key in RiskLimits.__dataclass_fields__})
        if limits.max_sector_weight is not None:
            raise ValueError("Sector cap cannot be evaluated without sector classifications")
        if any(value is None or value <= 0 for value in (
            order_count, notional, limits.max_drawdown, limits.max_name_weight,
            limits.max_gross_notional, limits.max_order_notional,
        )):
            raise ValueError("Positive order, gross, name, drawdown and daily database caps are required")
        peak = self.conn.execute("SELECT max(equity) AS peak FROM portfolio.equity_snapshot WHERE account_id = %s",
                                 (account_id,)).fetchone()["peak"]
        if peak is None:
            raise ValueError("Seed trusted equity history for this paper account before execution")
        return limits, peak, order_count, notional

    def existing(self, key, request_digest):
        row = self.conn.execute(
            """SELECT d.*, i.request_digest FROM portfolio.order_intent i
               JOIN portfolio.decision d ON d.id = i.decision_id WHERE i.decision_key = %s""", (key,),
        ).fetchone()
        if row and row["request_digest"] != request_digest:
            raise ValueError("Decision key is already associated with a different request")
        return row

    def reserve(self, account_id, key, request_digest, order, proposal, audit, daily_count, daily_notional):
        # Called under the account advisory lock, through submission. Autocommit makes the row durable before POST.
        identity = digest({"account_id": account_id, "order": order, "proposal": proposal, "limits": audit["limits"]})
        existing = self.conn.execute("SELECT * FROM portfolio.decision WHERE digest = %s", (identity,)).fetchone()
        if existing:
            return self._bind(key, request_digest, existing), False
        if self.conn.execute(
            "SELECT 1 FROM portfolio.decision WHERE account_id = %s AND settled_at IS NULL LIMIT 1", (account_id,),
        ).fetchone():
            raise ValueError("Reconcile the account's unsettled paper intent before another submission")
        consumed = self.conn.execute(
            """SELECT count(*) AS orders, coalesce(sum(quantity * limit_price), 0) AS notional
               FROM portfolio.decision WHERE account_id = %s
                 AND created_at >= date_trunc('day', now(), 'America/New_York')""", (account_id,),
        ).fetchone()
        if consumed["orders"] >= daily_count or consumed["notional"] + order["quantity"] * order["limit_price"] > daily_notional:
            raise ValueError("Paper order exceeds the daily ledger cap")
        try:
            with self.conn.transaction():
                row = self.conn.execute(
                    """INSERT INTO portfolio.decision
                         (account_id, digest, symbol, side, quantity, limit_price, client_order_id,
                          state, proposal, risk_inputs)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,'intent',%s,%s) RETURNING *""",
                    (account_id, identity, order["symbol"], order["side"], order["quantity"],
                     order["limit_price"], f"monroe-{identity[:32]}", Jsonb(proposal), Jsonb(json_data(audit))),
                ).fetchone()
                self.conn.execute("INSERT INTO portfolio.order_intent VALUES (%s,%s,%s)",
                                  (key, request_digest, row["id"]))
        except psycopg.errors.UniqueViolation:
            if existing := self.existing(key, request_digest):
                return existing, False
            raise
        return row, True

    def _bind(self, key, request_digest, row):
        self.conn.execute("INSERT INTO portfolio.order_intent VALUES (%s,%s,%s) ON CONFLICT DO NOTHING",
                          (key, request_digest, row["id"]))
        return self.existing(key, request_digest)

    def submission(self, row, receipt=None):
        self.conn.execute(
            """UPDATE portfolio.decision SET state = %s, broker_order_id = %s, broker_status = %s,
                   updated_at = clock_timestamp() WHERE id = %s""",
            ("submitted" if receipt else "unknown", receipt["id"] if receipt else None,
             receipt["status"] if receipt else None, row["id"]),
        )

    def pending(self, account_id):
        return self.conn.execute(
            """SELECT *, created_at < now() - interval '24 hours' AS expired_missing
                 FROM portfolio.decision WHERE account_id = %s AND settled_at IS NULL ORDER BY created_at""",
            (account_id,),
        ).fetchall()

    def missing(self, row):
        # A known broker order disappearing is never proof of rejection.
        expired = row["expired_missing"] and not row["broker_order_id"]
        self.conn.execute(
            """UPDATE portfolio.decision SET state = %s, settled_at = CASE WHEN %s THEN clock_timestamp() END,
                   updated_at = clock_timestamp() WHERE id = %s""",
            ("rejected" if expired else "unknown", expired, row["id"]),
        )

    def reconcile(self, row, order, fills):
        terminal = order["status"] in {"filled", "canceled", "rejected", "expired"}
        with self.conn.transaction():
            for fill in fills:
                self.conn.execute(
                    """INSERT INTO portfolio.trade
                         (account_id, external_trade_id, external_order_id, symbol, side, quantity, price, executed_at)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (account_id, external_trade_id) DO NOTHING""",
                    (row["account_id"], fill["id"], order["id"], fill["symbol"], fill["side"],
                     fill["quantity"], fill["price"], fill["executed_at"]),
                )
            recorded = self.conn.execute(
                """SELECT coalesce(sum(quantity), 0) AS quantity FROM portfolio.trade
                   WHERE account_id = %s AND external_order_id = %s""", (row["account_id"], order["id"]),
            ).fetchone()["quantity"]
            settled = terminal and recorded == order["filled_quantity"]
            self.conn.execute(
                """UPDATE portfolio.decision SET state = %s, broker_order_id = %s, broker_status = %s,
                       settled_at = CASE WHEN %s THEN clock_timestamp() END, updated_at = clock_timestamp()
                   WHERE id = %s""",
                ("rejected" if order["status"] == "rejected" else "submitted", order["id"], order["status"],
                 settled, row["id"]),
            )
            return settled
