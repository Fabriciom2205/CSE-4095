# Monroe Fund frontend

React 19 + Vite frontend using Astryx. The investing page shows Alpaca account performance, buying power, positions, Finnhub quotes, and Massive price history. Search finds active US-listed stocks and ETFs by ticker or company name. Asset pages show selectable 1D, 1W, 1M, 3M, YTD, 1Y, and all-time charts with period-specific price changes and hover date/price details, holdings context, and a confirmed paper-only limit order ticket. SEC filings and the deterministic daily-bar strategy replay have their own pages. Phil’s floating chat supports typed questions and microphone transcription.

## Run locally

Start the authenticated API on `127.0.0.1:8000` using the [local API setup](../docs/LOCAL_SETUP.md#phase-5-http-api). Then:

```bash
npm install
npm run dev
```

Open the URL printed by Vite and enter the `MONROE_API_TOKEN` configured for the API. Vite proxies `/api` to the local API. The token remains in React state and is not stored in browser storage.

To connect automatically on your own laptop, set `MONROE_LOCAL_AUTO_CONNECT=1` alongside `MONROE_API_TOKEN` in the repository-root `.env`. Restart Vite and open the printed `http://127.0.0.1:…` URL. The dev proxy adds the credential on requests to FastAPI. Only the auto-connect flag is sent to the frontend. Use the loopback URL with this mode.

Finnhub and Massive API keys must be configured in the backend environment for prices and charts. Alpaca account history, order history, proposals, and paper orders use backend credentials. Paper orders also require the shared execution database and are rejected outside regular market hours or when risk checks fail. Agent paper runs require a per-run confirmation and can submit at most one paper order. Strategy draft names, types, and parameters are saved in this browser. Voice input uses the browser microphone and needs microphone permission; transcripts appear in the composer for review before sending. Microphone access requires localhost or a secure HTTPS origin.

## Strategy replay

Choose moving average, monthly momentum, quality and value, or momentum plus news sentiment. Compare return, drawdown, and traded notional divided by starting cash with an equal-weight buy-and-hold benchmark using the same symbols and dates. The benchmark buys whole shares at the first open. Ranked strategies first rebalance when enough data is available, then at most once a month. Their selected assets receive equal allocations subject to the per-asset cap. Use **Discuss this draft with Phil** to get suggested settings before running a simulation.

Quality and value uses annual SEC return on assets and diluted earnings yield. Only completed filings dated before the decision day qualify. Use companies with comparable US GAAP filings. Momentum plus sentiment ranks recent price returns and the prior 30 days of Massive news labels. Article publication dates are a proxy for label availability. The replay excludes same-day articles and symbols without labels for the scoring window. Massive plan limits can affect the news and price requests. Saved snapshots need the matching fundamentals or news fields to replay those two strategy types.

Set `VITE_API_URL` to change the API prefix for another deployment. A remotely hosted API must allow the frontend origin and browser bearer requests; the current private Cloud Run service is not configured for direct browser access.

Run `npm run build` for a production static build. Astryx component and setup guidance is in [AGENTS.md](AGENTS.md).
