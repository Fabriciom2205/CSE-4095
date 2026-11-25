import {Fragment, useEffect, useRef, useState, type FormEvent} from 'react';
import {Button} from '@astryxdesign/core/Button';
import {Card} from '@astryxdesign/core/Card';
import {Grid} from '@astryxdesign/core/Grid';
import {Heading} from '@astryxdesign/core/Heading';
import {Tab, TabList} from '@astryxdesign/core/TabList';
import {Text} from '@astryxdesign/core/Text';
import {TextInput} from '@astryxdesign/core/TextInput';
import {VStack} from '@astryxdesign/core/VStack';

type Filing = {form: string; filing_date: string; report_date?: string; url?: string; snippet?: string};
type Quote = {symbol: string; price: number; change: number; percent_change: number; high: number; low: number; previous_close?: number; as_of: string};
type Bar = {date: string; close: number};
type Holding = {symbol: string; quantity: string; market_value?: string; cost_basis: string; unrealized_pl?: string};
type BrokerOrder = {external_order_id: string; symbol?: string; side?: string; type?: string; status: string; quantity?: string; filled_quantity?: string; filled_avg_price?: string; submitted_at?: string; filled_at?: string};
type Portfolio = {account: {environment: string; status: string; currency: string; equity: string; cash?: string; buying_power?: string}; positions: Holding[]; exposure?: {gross_notional: string; name_weights: Record<string, string>} | null; retrieved_at: string};
type History = {points: {timestamp: number; equity: number; profit_loss?: number; profit_loss_pct?: number}[]};
type AssetDetails = {name?: string; market?: string; primary_exchange?: string; type?: string; description?: string; homepage_url?: string};
type TickerResult = {ticker: string; name?: string; market?: string; type?: string; primary_exchange?: string};
type Citation = {title?: string; url?: string; accession_number?: string};
type VisualCell = {value: string | null; derived: boolean; sources: {accession: string; filed_at: string; url: string; role: string}[]};
type ResearchVisual = {kind: 'table' | 'bar' | 'line'; symbol: string; statement: string; title: string; unit: string; columns: {key: string; label: string}[]; rows: {period_end: string; period: string; cells: Record<string, VisualCell>}[]};
type ChatMessage = {id?: string; role: 'user' | 'phil'; text: string; citations?: Citation[]; visuals?: ResearchVisual[]};
const strategyTypes = {
  moving_average: {label: 'Moving average', rule: 'Buy above the moving average and exit below it or at the stop.'},
  momentum: {label: 'Momentum', rule: 'Rank assets by their recent price returns and rebalance monthly.'},
  quality_value: {label: 'Smart beta · Quality and value', rule: 'Rank companies by annual return on assets and earnings yield using filings available before each monthly decision. Use operating companies with annual SEC filings.'},
  sentiment: {label: 'Momentum + news sentiment', rule: 'Combine price momentum with the prior 30 days of labeled news and rebalance monthly. Symbols without labeled news are excluded. The replay uses article publication dates as a proxy for label availability.'},
};
type StrategyKind = keyof typeof strategyTypes;

type Backtest = {turnover: string; benchmark: {final_equity: string; max_drawdown: string; turnover: string}; start: string; end: string; input_sha256: string; final_equity: string; max_drawdown: string; initial_cash: string; fills: {symbol: string; side: string; quantity: number; price: string; fill_date: string}[]; equity_curve: {date: string; equity: string}[]};
type StrategyDraft = {kind?: StrategyKind; topN?: string; id: string; name: string; symbols: string; lookback: string; allocation: string; stopLoss: string};
type ProposalOutcome = {session_id: string; portfolio_retrieved_at: string; proposals: {symbol: string; target_weight: number; rationale: string; confidence: number; evidence: {accessions: string[]; market_as_of: string}}[]; breaches: {limit: string; actual: string; maximum: string; subject?: string}[]; quotes: {symbol: string; as_of: string; status: string}[]};

function loadStrategyDrafts(): StrategyDraft[] {
  try { const drafts: unknown = JSON.parse(localStorage.getItem('monroe-strategy-drafts') ?? '[]'); return Array.isArray(drafts) ? drafts.filter((item): item is StrategyDraft => item && typeof item.id === 'string' && typeof item.name === 'string' && typeof item.symbols === 'string' && typeof item.lookback === 'string' && typeof item.allocation === 'string' && typeof item.stopLoss === 'string') : []; } catch { return []; }
}

function RichAnswer({text}: {text: string}) {
  const inline = (value: string) => value.split(/(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`|\[[^\]]+\]\(https?:\/\/[^\s)]+\))/g).map((part, index) => {
    if (part.startsWith('**') && part.endsWith('**')) return <strong key={index}>{part.slice(2, -2)}</strong>;
    if (part.startsWith('*') && part.endsWith('*')) return <em key={index}>{part.slice(1, -1)}</em>;
    if (part.startsWith('`') && part.endsWith('`')) return <code key={index}>{part.slice(1, -1)}</code>;
    const link = part.match(/^\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)$/);
    if (link) return <a key={index} href={link[2]} target="_blank" rel="noreferrer">{link[1]}</a>;
    return part;
  });
  const blocks = text.trim().split(/\n\s*\n/).filter(Boolean);
  return <section className="rich-answer">{blocks.map((block, index) => {
    const lines = block.split('\n');
    if (lines.every(line => /^\s*\|.*\|\s*$/.test(line)) && lines.length > 1) {
      const rows = lines.map(line => line.trim().replace(/^\||\|$/g, '').split('|').map(cell => cell.trim()));
      const data = rows.filter(row => !row.every(cell => /^:?-{3,}:?$/.test(cell)));
      return <table key={index}><thead><tr>{data[0].map((cell, i) => <th key={i}>{inline(cell)}</th>)}</tr></thead><tbody>{data.slice(1).map((row, ri) => <tr key={ri}>{data[0].map((_, ci) => <td key={ci}>{inline(row[ci] ?? '')}</td>)}</tr>)}</tbody></table>;
    }
    if (/^#{1,3}\s/.test(lines[0])) return <h3 key={index}>{inline(lines[0].replace(/^#{1,3}\s+/, ''))}</h3>;
    if (lines.every(line => /^\s*[-*]\s+/.test(line))) return <ul key={index}>{lines.map((line, i) => <li key={i}>{inline(line.replace(/^\s*[-*]\s+/, ''))}</li>)}</ul>;
    if (lines.every(line => /^\s*\d+\.\s+/.test(line))) return <ol key={index}>{lines.map((line, i) => <li key={i}>{inline(line.replace(/^\s*\d+\.\s+/, ''))}</li>)}</ol>;
    if (lines.every(line => /^\s*>/.test(line))) return <blockquote key={index}>{lines.map((line, i) => <p key={i}>{inline(line.replace(/^\s*>\s?/, ''))}</p>)}</blockquote>;
    return <p key={index}>{lines.map((line, i) => <Fragment key={i}>{i > 0 && <br/>}{inline(line)}</Fragment>)}</p>;
  })}</section>;
}

function ResearchVisualCard({visual}: {visual: ResearchVisual}) {
  const series = visual.columns.map(column => ({...column, values: visual.rows.map(row => row.cells[column.key]?.value == null ? null : Number(row.cells[column.key].value))}));
  const values = series.flatMap(item => item.values.filter((value): value is number => value != null));
  const low = Math.min(0, ...values), high = Math.max(0, ...values), range = high - low || 1;
  const zero = 90 - (0 - low) / range * 78;
  const width = 100 / Math.max(1, visual.rows.length);
  const table = <table><thead><tr><th>Period</th>{visual.columns.map(column => <th key={column.key}>{column.label}</th>)}</tr></thead><tbody>{visual.rows.map(row => <tr key={row.period_end}><th>{row.period_end} · {row.period}</th>{visual.columns.map(column => {const cell = row.cells[column.key]; return <td key={column.key}>{cell?.value == null ? '—' : Number(cell.value).toLocaleString(undefined, {maximumFractionDigits: 2})}{cell?.derived ? ' †' : ''}</td>;})}</tr>)}</tbody></table>;
  return <Card padding={3} className="visual-card"><VStack gap={2}><Heading level={3}>{visual.title}</Heading><Text type="supporting" color="secondary">{visual.statement.replaceAll('_', ' ')} · {visual.unit}{visual.rows.some(row => Object.values(row.cells).some(cell => cell.derived)) ? ' · † derived from reported filings' : ''}</Text>{visual.kind !== 'table' && <svg className="research-chart" viewBox="0 0 100 100" role="img" aria-label={`${visual.kind} chart for ${visual.title}`}><path className="chart-gridline" d="M0 10H100 M0 50H100 M0 90H100"/>{visual.kind === 'line' ? series.map((item, si) => <polyline key={item.key} className={`research-line series-${si % 5}`} points={item.values.flatMap((value, i) => value == null ? [] : [`${i * width + width / 2},${90 - (value - low) / range * 78}`]).join(' ')}/>) : visual.rows.flatMap((row, ri) => visual.columns.map((column, ci) => {const raw = row.cells[column.key]?.value; if (raw == null) return null; const value = Number(raw); const barWidth = width / Math.max(1, visual.columns.length) * .72; const height = Math.abs(value) / range * 78; return <rect key={`${row.period_end}-${column.key}`} className={`research-bar series-${ci % 5}`} x={ri * width + ci * width / Math.max(1, visual.columns.length) + .1} y={value < 0 ? zero : zero - height} width={barWidth} height={height}/>;}))}</svg>}{visual.kind !== 'table' && <ul className="visual-legend">{visual.columns.map((column, index) => <li className={`series-label-${index % 5}`} key={column.key}>{column.label}</li>)}</ul>}{table}<VStack gap={1}>{visual.rows.flatMap(row => visual.columns.flatMap(column => (row.cells[column.key]?.sources ?? []).map(source => <a key={`${row.period_end}-${column.key}-${source.accession}`} href={source.url} target="_blank" rel="noreferrer">{source.accession} · filed {source.filed_at} ({source.role})</a>)))}</VStack></VStack></Card>;
}

const periods = ['1D', '1W', '1M', '3M', 'YTD', '1Y', 'ALL'];
const watchlist = ['NVDA', 'AAPL', 'MSFT', 'AMZN', 'GOOGL', 'SPY', 'VOO', 'QQQ'];
const apiBase = (import.meta.env.VITE_API_URL ?? '/api').replace(/\/$/, '');
const money = (value?: string | number, currency = 'USD') => value == null || !Number.isFinite(Number(value)) ? '—' : new Intl.NumberFormat('en-US', {style: 'currency', currency, minimumFractionDigits: 2, maximumFractionDigits: 2}).format(Number(value));
const pct = (value?: number | string) => value == null || !Number.isFinite(Number(value)) ? '—' : `${Number(value) >= 0 ? '+' : ''}${(Number(value) * 100).toFixed(2)}%`;

async function request<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBase}${path}`, {...init, headers: {Authorization: `Bearer ${token}`, ...(init?.body ? {'Content-Type': 'application/json'} : {}), ...init?.headers}});
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `Request failed (${response.status})`);
  }
  return response.json();
}

function PriceChart({bars}: {bars: Bar[]}) {
  const [hover, setHover] = useState<number | null>(null);
  if (bars.length < 2) return <p className="chart-empty">Price history is unavailable for this period.</p>;
  const closes = bars.map(bar => Number(bar.close));
  const low = Math.min(...closes), high = Math.max(...closes), spread = high - low || 1;
  const x = (index: number) => index * 100 / (closes.length - 1), y = (index: number) => 96 - (closes[index] - low) / spread * 88;
  const points = closes.map((_, index) => `${x(index)},${y(index)}`).join(' ');
  const positive = closes.at(-1)! >= closes[0];
  const selected = hover == null ? null : Math.min(hover, bars.length - 1);
  return <figure className="price-chart-wrap" onPointerLeave={() => setHover(null)}><svg className={`price-chart ${positive ? 'positive' : 'negative'}`} viewBox="0 0 100 100" preserveAspectRatio="none" role="img" aria-label={`${bars.length} prices from ${bars[0].date} through ${bars.at(-1)?.date}`} onPointerMove={event => {const bounds = event.currentTarget.getBoundingClientRect(); setHover(Math.round(Math.max(0, Math.min(1, (event.clientX - bounds.left) / bounds.width)) * (bars.length - 1)));}}><path className="chart-gridline" d="M0 8H100 M0 52H100 M0 96H100"/><polyline points={points}/>{selected != null && <><path className="chart-crosshair" d={`M${x(selected)} 0V100`}/><circle className="chart-point" cx={x(selected)} cy={y(selected)} r="1.5"/></>}</svg>{selected != null && <output className="chart-tooltip" style={{left: `${Math.max(8, Math.min(78, x(selected)))}%`}}><strong>{money(bars[selected].close)}</strong><small>{new Date(bars[selected].date).toLocaleString(undefined, bars[selected].date.includes('T') ? {dateStyle: 'medium', timeStyle: 'short'} : {dateStyle: 'medium', timeZone: 'UTC'})}</small></output>}<figcaption className="sr-only">Move over the chart to inspect each date and price.</figcaption></figure>;
}

export default function App() {
  const [token, setToken] = useState('');
  const [connected, setConnected] = useState(false);
  const [apiHealth, setApiHealth] = useState('');
  const [tab, setTab] = useState('investing');
  const [period, setPeriod] = useState('1D');
  const [ticker, setTicker] = useState('NVDA');
  const [detail, setDetail] = useState(false);
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [history, setHistory] = useState<History | null>(null);
  const [orders, setOrders] = useState<BrokerOrder[]>([]);
  const [quotes, setQuotes] = useState<Record<string, Quote>>({});
  const [bars, setBars] = useState<Bar[]>([]);
  const [assetPeriod, setAssetPeriod] = useState('1D');
  const [assetSearch, setAssetSearch] = useState('');
  const [assetResults, setAssetResults] = useState<TickerResult[]>([]);
  const [details, setDetails] = useState<AssetDetails>({});
  const [filings, setFilings] = useState<Filing[]>([]);
  const [form, setForm] = useState('');
  const [search, setSearch] = useState('');
  const [strategyKind, setStrategyKind] = useState<StrategyKind>('moving_average');
  const [topN, setTopN] = useState('1');
  const assetRequest = useRef(0);
  const [strategySymbols, setStrategySymbols] = useState('SPY, QQQ');
  const [strategyName, setStrategyName] = useState('Moving-average strategy');
  const [strategyDrafts, setStrategyDrafts] = useState<StrategyDraft[]>(loadStrategyDrafts);
  const [selectedStrategy, setSelectedStrategy] = useState('');
  const [lookback, setLookback] = useState('20');
  const [allocation, setAllocation] = useState('0.25');
  const [stopLoss, setStopLoss] = useState('0.10');
  const [initialCash, setInitialCash] = useState('10000');
  const [strategyStart, setStrategyStart] = useState('');
  const [strategyEnd, setStrategyEnd] = useState('');
  const [snapshotId, setSnapshotId] = useState('');
  const [backtest, setBacktest] = useState<Backtest | null>(null);
  const [agentMode, setAgentMode] = useState<'proposal' | 'execute'>('proposal');
  const [proposalTickers, setProposalTickers] = useState('NVDA, AAPL');
  const [proposalCaps, setProposalCaps] = useState({max_name_weight: '', max_sector_weight: '', max_order_notional: '', max_gross_notional: '', max_drawdown: ''});
  const [proposalSession, setProposalSession] = useState<string>();
  const [proposalResult, setProposalResult] = useState<ProposalOutcome | null>(null);
  const [agentSymbol, setAgentSymbol] = useState('NVDA');
  const [agentPrompt, setAgentPrompt] = useState('Research the company and propose a cautious paper position based on current evidence.');
  const [agentConfirmed, setAgentConfirmed] = useState(false);
  const [agentResult, setAgentResult] = useState('');
  const [agentIntent, setAgentIntent] = useState<{symbol: string; prompt: string; decision_key: string; confirm_paper_only: true} | null>(null);
  const [orderSide, setOrderSide] = useState<'buy' | 'sell'>('buy');
  const [quantity, setQuantity] = useState('1');
  const [orderKey, setOrderKey] = useState('');
  const [orderReview, setOrderReview] = useState(false);
  const [orderResult, setOrderResult] = useState('');
  const [question, setQuestion] = useState('');
  const [visualMode, setVisualMode] = useState<'auto' | 'table' | 'bar' | 'line'>('auto');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessionId, setSessionId] = useState<string>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [chatError, setChatError] = useState('');
  const [chatOpen, setChatOpen] = useState(false);
  const [chatMinimized, setChatMinimized] = useState(false);
  const [teaser, setTeaser] = useState(() => !sessionStorage.getItem('monroe-phil-seen'));
  const [recording, setRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const [voiceStatus, setVoiceStatus] = useState('');
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const bytesRef = useRef(0);

  useEffect(() => {
    if (!teaser) return;
    const timer = window.setTimeout(() => setTeaser(false), 5000);
    sessionStorage.setItem('monroe-phil-seen', '1');
    return () => window.clearTimeout(timer);
  }, [teaser]);

  async function loadAccount(credential = token) {
    const [accountResult, historyResult, orderResult] = await Promise.allSettled([
      request<Portfolio>('/portfolio', credential),
      request<History>(`/portfolio/history?period=${period}`, credential),
      request<BrokerOrder[]>('/orders?status=all', credential),
    ]);
    if (accountResult.status === 'rejected') throw accountResult.reason;
    const account = accountResult.value;
    setPortfolio(account); setHistory(historyResult.status === 'fulfilled' ? historyResult.value : null); setOrders(orderResult.status === 'fulfilled' ? orderResult.value : []); setConnected(true);
    if (historyResult.status === 'rejected' || orderResult.status === 'rejected') setError(`Account connected; ${[historyResult.status === 'rejected' ? 'performance history' : '', orderResult.status === 'rejected' ? 'order history' : ''].filter(Boolean).join(' and ')} temporarily unavailable.`);
    const symbols = [...new Set([...watchlist, ...account.positions.map(position => position.symbol)])];
    void Promise.allSettled(symbols.map(async symbol => {
      const quote = await request<Quote>(`/market/quote/${encodeURIComponent(symbol)}`, credential);
      setQuotes(previous => ({...previous, [symbol]: quote}));
    }));
  }

  async function connect(event: FormEvent) {
    event.preventDefault();
    if (!token.trim()) return;
    setBusy(true); setError('');
    void fetch(`${apiBase}/health`).then(response => response.json()).then(result => setApiHealth(result.status ?? 'unknown')).catch(() => setApiHealth('unavailable'));
    try { await loadAccount(token.trim()); }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Unable to connect'); setConnected(false); }
    finally { setBusy(false); }
  }

  async function loadPeriod(value: string) {
    setPeriod(value);
    if (!connected) return;
    setBusy(true); setError('');
    try { setHistory(await request<History>(`/portfolio/history?period=${value}`, token)); }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Performance history unavailable'); setHistory(null); }
    finally { setBusy(false); }
  }

  async function openAsset(symbol: string, chartPeriod = assetPeriod) {
    const normalized = symbol.trim().toUpperCase();
    if (!normalized || !connected) return;
    const id = ++assetRequest.current;
    setBars([]); setDetails({});
    setTicker(normalized); setDetail(true); setOrderReview(false); setOrderResult(''); setError(''); setBusy(true);
    try {
      const [quote, chart, company] = await Promise.allSettled([
        request<Quote>(`/market/quote/${encodeURIComponent(normalized)}`, token),
        request<{bars: Bar[]}>(`/market/bars/${encodeURIComponent(normalized)}?period=${chartPeriod}`, token),
        request<AssetDetails>(`/market/details/${encodeURIComponent(normalized)}`, token),
      ]);
      if (id !== assetRequest.current) return;
      if (quote.status === 'fulfilled') setQuotes(previous => ({...previous, [normalized]: quote.value}));
      if (company.status === 'fulfilled') setDetails(company.value);
      if (chart.status === 'fulfilled') setBars(chart.value.bars);
      else setError('Price history unavailable for this period');
    } finally { if (id === assetRequest.current) setBusy(false); }
  }

  async function searchAssets(event: FormEvent) {
    event.preventDefault(); if (!connected || !assetSearch.trim()) return;
    setBusy(true); setError('');
    try { const result = await request<{results: TickerResult[]}>(`/market/search?q=${encodeURIComponent(assetSearch.trim())}`, token); setAssetResults(result.results); }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Stock and ETF search failed'); setAssetResults([]); }
    finally { setBusy(false); }
  }

  async function loadAssetPeriod(value: string) {
    const id = ++assetRequest.current;
    setAssetPeriod(value); setBars([]); setBusy(true); setError('');
    try {
      const result = await request<{bars: Bar[]}>(`/market/bars/${encodeURIComponent(ticker)}?period=${value}`, token);
      if (id === assetRequest.current) setBars(result.bars);
    } catch (cause) {
      if (id === assetRequest.current) setError(cause instanceof Error ? cause.message : 'Price history unavailable');
    } finally { if (id === assetRequest.current) setBusy(false); }
  }

  async function searchFilings(event: FormEvent) {
    event.preventDefault(); if (!connected) return;
    setBusy(true); setError('');
    try {
      const params = new URLSearchParams();
      if (ticker.trim()) params.set('ticker', ticker.trim().toUpperCase());
      if (search.trim()) params.set('q', search.trim());
      if (form) params.set('form', form);
      const result = await request<{filings: Filing[]}>(`/filings?${params}`, token);
      setFilings(result.filings);
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Filing search failed'); }
    finally { setBusy(false); }
  }

  async function runBacktest(event: FormEvent) {
    event.preventDefault(); if (!connected) return;
    setBusy(true); setError(''); setBacktest(null);
    try {
      const result = await request<Backtest>('/strategy/backtest', token, {method: 'POST', body: JSON.stringify({strategy: strategyConfig(), start: strategyStart, end: strategyEnd, initial_cash: initialCash})});
      setBacktest(result);
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Strategy replay failed'); }
    finally { setBusy(false); }
  }

  function saveStrategyDraft() {
    if (!strategyName.trim() || !strategySymbols.trim()) return;
    const draft: StrategyDraft = {id: selectedStrategy || crypto.randomUUID(), name: strategyName.trim(), symbols: strategySymbols, lookback, allocation, stopLoss, kind: strategyKind, topN};
    const drafts = selectedStrategy ? strategyDrafts.map(item => item.id === selectedStrategy ? draft : item) : [...strategyDrafts, draft];
    setStrategyDrafts(drafts); setSelectedStrategy(draft.id);
    try { localStorage.setItem('monroe-strategy-drafts', JSON.stringify(drafts)); } catch { setError('Draft is available for this session but could not be saved in browser storage.'); }
  }

  function selectStrategyDraft(id: string) {
    const draft = strategyDrafts.find(item => item.id === id);
    setSelectedStrategy(id);
    if (!draft) return;
    setStrategyKind(draft.kind && Object.hasOwn(strategyTypes, draft.kind) ? draft.kind : 'moving_average'); setTopN(draft.topN ?? '1');
    setStrategyName(draft.name); setStrategySymbols(draft.symbols); setLookback(draft.lookback); setAllocation(draft.allocation); setStopLoss(draft.stopLoss); setBacktest(null);
  }

  function newStrategyDraft() {
    setStrategyKind('moving_average'); setTopN('1');
    setSelectedStrategy(''); setStrategyName('New strategy'); setStrategySymbols('SPY, QQQ'); setLookback('20'); setAllocation('0.25'); setStopLoss('0.10'); setBacktest(null);
  }

  function strategyConfig() {
    return {kind: strategyKind, top_n: strategyKind === 'moving_average' ? 1 : Number(topN), symbols: strategySymbols.split(',').map(symbol => symbol.trim().toUpperCase()).filter(Boolean), lookback_sessions: strategyKind === 'quality_value' ? 20 : Number(lookback), allocation_fraction: allocation, stop_loss_fraction: strategyKind === 'moving_average' ? stopLoss : '0.10'};
  }

  async function replaySnapshot(event: FormEvent) {
    event.preventDefault(); if (!connected) return;
    setBusy(true); setError(''); setBacktest(null);
    try { setBacktest(await request<Backtest>('/backtest', token, {method: 'POST', body: JSON.stringify({strategy: strategyConfig(), snapshot_id: snapshotId.trim(), initial_cash: initialCash})})); }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Saved snapshot replay failed'); }
    finally { setBusy(false); }
  }

  async function buildProposal(event: FormEvent) {
    event.preventDefault(); if (!connected) return;
    setBusy(true); setError(''); setProposalResult(null);
    try {
      const constraints = Object.fromEntries(Object.entries(proposalCaps).filter(([, value]) => value.trim()).map(([key, value]) => [key, value]));
      const result = await request<ProposalOutcome>('/proposals', token, {method: 'POST', body: JSON.stringify({tickers: proposalTickers.split(',').map(symbol => symbol.trim().toUpperCase()).filter(Boolean), constraints, session_id: proposalSession})});
      setProposalSession(result.session_id); setProposalResult(result);
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Portfolio proposal failed'); }
    finally { setBusy(false); }
  }

  async function runAgentPaper(intent = agentIntent) {
    if (!connected || (!agentConfirmed && !intent)) return;
    const run = intent ?? {symbol: agentSymbol.trim().toUpperCase(), prompt: agentPrompt.trim(), decision_key: crypto.randomUUID(), confirm_paper_only: true as const};
    if (!run.prompt || !run.symbol) return;
    setAgentIntent(run); setBusy(true); setError(''); setAgentResult('');
    try {
      const result = await request<{mode: string; order?: {state: string; status?: string; symbol: string; side: string; quantity: number; limit_price: string; duplicate: boolean}}>('/agent/paper-run', token, {method: 'POST', body: JSON.stringify(run)});
      setAgentResult(result.order ? `${result.order.duplicate ? 'Existing ' : ''}${result.order.state} · ${result.order.side} ${result.order.quantity} ${result.order.symbol} · ${result.order.status ?? 'status pending'} · limit ${money(result.order.limit_price)}` : 'Phil returned no eligible paper order.');
      if (result.order?.state !== 'unknown') setAgentIntent(null);
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Agent paper run failed. Retry uses the same decision key.'); }
    finally { setBusy(false); setAgentConfirmed(false); }
  }

  async function submitOrder() {
    if (!connected || !orderKey) return;
    setBusy(true); setError('');
    try {
      const result = await request<{order?: {client_order_id: string; state: string; status?: string; limit_price: string; duplicate: boolean}}>('/orders/paper', token, {method: 'POST', body: JSON.stringify({symbol: ticker, side: orderSide, quantity: Number(quantity), decision_key: orderKey})});
      setOrderResult(result.order ? `${result.order.duplicate ? 'Existing ' : ''}paper order ${result.order.state} · ${result.order.status ?? 'status pending'} · limit ${money(result.order.limit_price)}` : 'No order was submitted.');
      setOrderReview(false);
      if (result.order?.state !== 'unknown') setOrderKey('');
      try { await loadAccount(); } catch { setError('Order response received; account refresh failed. Refresh before placing another order.'); }
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Paper order was not submitted'); }
    finally { setBusy(false); }
  }

  async function sendToPhil(prompt: string, visual?: 'table' | 'bar' | 'line') {
    if (!prompt || !connected) return;
    const responseId = crypto.randomUUID();
    setQuestion(''); setBusy(true); setChatError(''); setMessages(previous => [...previous, {role: 'user', text: prompt}, {id: responseId, role: 'phil', text: ''}]);
    const updateResponse = (update: Partial<ChatMessage>) => setMessages(previous => previous.map(message => message.id === responseId ? {...message, ...update} : message));
    try {
      const response = await fetch(`${apiBase}/research`, {method: 'POST', headers: {Authorization: `Bearer ${token}`, 'Content-Type': 'application/json', Accept: 'text/event-stream'}, body: JSON.stringify({ticker, question: prompt, session_id: sessionId, ...(visual ? {visual} : {})})});
      if (!response.ok) { const body = await response.json().catch(() => null); throw new Error(body?.detail ?? `Request failed (${response.status})`); }
      if (!response.body) throw new Error('Phil stream is unavailable in this browser');
      const reader = response.body.getReader(), decoder = new TextDecoder();
      let buffer = '', answer = '', complete = false;
      const consume = (frame: string) => {
        const lines = frame.split(/\r?\n/), event = lines.find(line => line.startsWith('event:'))?.slice(6).trim();
        const payload = lines.filter(line => line.startsWith('data:')).map(line => line.slice(5).trim()).join('\n');
        if (!payload) return;
        const data = JSON.parse(payload);
        if (event === 'delta') { answer += data.text ?? ''; updateResponse({text: answer}); }
        if (event === 'final') { complete = true; setSessionId(data.session_id); updateResponse({text: data.answer, citations: data.citations, visuals: data.visuals}); }
        if (event === 'error') throw new Error(data.detail ?? 'Phil could not complete that request');
      };
      while (true) {
        const {value, done} = await reader.read();
        buffer += decoder.decode(value, {stream: !done}).replaceAll('\r\n', '\n');
        const frames = buffer.split('\n\n'); buffer = frames.pop() ?? '';
        frames.forEach(consume);
        if (done) break;
      }
      if (buffer.trim()) consume(buffer);
      if (!complete) throw new Error('Phil’s response ended before it was complete');
    } catch (cause) { setChatError(cause instanceof Error ? cause.message : 'Phil could not complete that request'); }
    finally { setBusy(false); }
  }

  function askPhil(event: FormEvent) {
    event.preventDefault();
    void sendToPhil(question.trim(), visualMode === 'auto' ? undefined : visualMode);
  }

  function designStrategyWithPhil() {
    setChatOpen(true); setChatMinimized(false);
    void sendToPhil(`Help me draft settings for a historical simulation. The available types are ${Object.values(strategyTypes).map(({label, rule}) => `${label}: ${rule}`).join(' ')}. All use next-session open fills. My current draft is “${strategyName}”: ${JSON.stringify(strategyConfig())}. Return suggested form settings, explain assumptions and data requirements, and suggest what to compare against the equal-weight benchmark. Keep this to backtest design.`);
  }

  async function transcribe(audio: Blob, mime: string) {
    setTranscribing(true); setVoiceStatus('Transcribing…'); setChatError('');
    try {
      const result = await request<{transcript: string}>('/research/transcribe', token, {method: 'POST', body: audio, headers: {'Content-Type': mime}});
      setQuestion(result.transcript); setVoiceStatus('Transcript ready. Review it, then send to Phil.');
    } catch (cause) { setVoiceStatus(''); setChatError(cause instanceof Error ? cause.message : 'Speech transcription failed'); }
    finally { setTranscribing(false); }
  }

  async function startRecording() {
    setChatError(''); setVoiceStatus('');
    try {
      if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) throw new Error('Microphone recording is not supported in this browser');
      const stream = await navigator.mediaDevices.getUserMedia({audio: true}); streamRef.current = stream; chunksRef.current = []; bytesRef.current = 0;
      const mime = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4'].find(type => MediaRecorder.isTypeSupported(type));
      const recorder = new MediaRecorder(stream, mime ? {mimeType: mime} : undefined); recorderRef.current = recorder;
      recorder.ondataavailable = event => { if (!event.data.size) return; chunksRef.current.push(event.data); bytesRef.current += event.data.size; if (bytesRef.current > 4 * 1024 * 1024 && recorder.state === 'recording') recorder.stop(); };
      recorder.onstop = () => { stream.getTracks().forEach(track => track.stop()); streamRef.current = null; setRecording(false); const audio = new Blob(chunksRef.current, {type: recorder.mimeType}); if (audio.size > 4 * 1024 * 1024) { setChatError('Recording exceeds the 4 MiB limit. Try a shorter question.'); return; } if (!audio.size) { setChatError('No audio was recorded. Try again.'); return; } void transcribe(audio, recorder.mimeType.split(';')[0]); };
      recorder.start(); setRecording(true); setVoiceStatus('Listening… select stop when you are done.');
    } catch (cause) { streamRef.current?.getTracks().forEach(track => track.stop()); streamRef.current = null; setChatError(cause instanceof Error ? cause.message : 'Microphone access is unavailable'); }
  }

  useEffect(() => () => { if (recorderRef.current?.state === 'recording') { recorderRef.current.onstop = null; recorderRef.current.stop(); } streamRef.current?.getTracks().forEach(track => track.stop()); }, []);

  const activeQuote = quotes[ticker];
  const firstAssetPrice = bars[0]?.close;
  const lastAssetPrice = bars.at(-1)?.close;
  const assetChange = bars.length >= 2 && firstAssetPrice > 0 ? lastAssetPrice! - firstAssetPrice : undefined;
  const assetChangePercent = assetChange == null ? undefined : assetChange / firstAssetPrice;
  const activeHolding = portfolio?.positions.find(position => position.symbol === ticker);
  const latest = history?.points.at(-1);
  const first = history?.points[0];
  const periodChange = latest && first ? Number(latest.equity) - Number(first.equity) : undefined;
  const periodPercent = latest && first && Number(first.equity) ? Number(latest.equity) / Number(first.equity) - 1 : undefined;
  const performanceBars = history?.points.map(point => ({date: new Date(point.timestamp * 1000).toISOString().slice(0, 10), close: point.equity})) ?? [];

  return <VStack as="main" gap={4} className="app-shell">
    <header className="topbar">
      <a className="brand" href="#investing" onClick={() => {setTab('investing'); setDetail(false);}} aria-label="The Monroe Fund home"><img className="brand-logo" src="/monroe-fund-logo.png" alt=""/><p><strong>MONROE</strong><small>INVESTMENT RESEARCH</small></p></a>
      <nav aria-label="Main navigation"><TabList value={tab} onChange={value => {setTab(value); setDetail(false);}}><Tab value="investing" label="Investing"/><Tab value="search" label="Search"/><Tab value="filings" label="SEC filings"/><Tab value="strategies" label="Strategies"/></TabList></nav>
      <form className="access-form" onSubmit={connect}><TextInput label="API bearer token" isLabelHidden type="password" value={token} onChange={setToken} placeholder="Operator API token" autoComplete="off"/><Button label={connected ? 'Refresh' : 'Connect'} type="submit" variant="primary" isLoading={busy}/></form>
    </header>

    <VStack as="section" gap={4} className="page-content">
      <header className="page-heading"><VStack gap={1}><Text type="label" color="secondary">THE MONROE FUND / {tab.toUpperCase()}</Text><Heading level={1}>{detail ? ticker : tab === 'investing' ? 'Investing' : tab === 'search' ? 'Search stocks & ETFs' : tab === 'filings' ? 'SEC filings' : 'Strategies'}</Heading></VStack><Text type="supporting" color="secondary">{connected ? `Connected · ${portfolio?.account.environment ?? 'API'}${apiHealth ? ` · service ${apiHealth}` : ''}` : 'Connect to view current data'}</Text></header>
      {error && <p role="alert" className="error-message">{error}</p>}
      {!connected && <Card variant="muted" padding={3}><Text>Enter your API token to load your account, current market data, filings, and research tools. The token stays in this browser tab.</Text></Card>}

      {tab === 'investing' && !detail && <VStack gap={4}>
        {portfolio && <>
          <Card padding={4} className="performance-card"><VStack gap={3}>
            <Text type="label" color="secondary">TOTAL ACCOUNT VALUE</Text><Heading level={1}>{money(portfolio.account.equity, portfolio.account.currency)}</Heading>
            <Text className={periodChange == null ? '' : periodChange >= 0 ? 'gain' : 'loss'}>{periodChange == null ? 'Performance unavailable' : `${periodChange >= 0 ? '+' : ''}${money(periodChange, portfolio.account.currency)} (${pct(periodPercent)})`} · {period}</Text>
            <PriceChart bars={performanceBars}/>
            <nav className="period-picker" aria-label="Performance period">{periods.map(value => <button className={period === value ? 'period-active' : ''} key={value} onClick={() => void loadPeriod(value)}>{value}</button>)}</nav>
          </VStack></Card>
          <Grid columns={{minWidth: 220, max: 4, repeat: 'fit'}} gap={3}><Card padding={3}><Text type="label" color="secondary">BUYING POWER</Text><Heading level={2}>{money(portfolio.account.buying_power, portfolio.account.currency)}</Heading></Card><Card padding={3}><Text type="label" color="secondary">CASH</Text><Heading level={2}>{money(portfolio.account.cash, portfolio.account.currency)}</Heading></Card><Card padding={3}><Text type="label" color="secondary">OPEN POSITIONS</Text><Heading level={2}>{portfolio.positions.length}</Heading></Card><Card padding={3}><Text type="label" color="secondary">GROSS EXPOSURE</Text><Heading level={2}>{money(portfolio.exposure?.gross_notional, portfolio.account.currency)}</Heading></Card></Grid>
          <Card padding={4}><VStack gap={2}><Heading level={2}>Your investments</Heading>{portfolio.positions.map(position => <button className="asset-row" key={position.symbol} onClick={() => void openAsset(position.symbol)}><strong className="asset-symbol">{position.symbol}<small>{position.quantity} shares</small></strong><strong>{money(position.market_value, portfolio.account.currency)}<small className={Number(position.unrealized_pl) >= 0 ? 'gain' : 'loss'}>{money(position.unrealized_pl, portfolio.account.currency)}</small></strong><strong className="asset-price">{money(quotes[position.symbol]?.price)}<small>Market price</small></strong></button>)}{portfolio.positions.length === 0 && <Text color="secondary">No open positions yet. Browse stocks and ETFs below.</Text>}</VStack></Card>
          {portfolio.exposure && <Card padding={4}><VStack gap={2}><Heading level={2}>Portfolio exposure</Heading>{Object.entries(portfolio.exposure.name_weights).map(([symbol, weight]) => <article className="position-row" key={symbol}><strong>{symbol}</strong><Text>{pct(weight)} of equity</Text></article>)}</VStack></Card>}
          <Card padding={4}><VStack gap={2}><Heading level={2}>Recent broker orders</Heading>{orders.slice(0, 20).map(order => <article className="filing-row" key={order.external_order_id}><strong>{order.side?.toUpperCase()} {order.symbol}</strong><Text>{order.quantity ?? '—'} shares{order.filled_quantity ? ` · ${order.filled_quantity} filled` : ''}</Text><Text>{order.status.replaceAll('_', ' ')}</Text><Text>{order.filled_avg_price ? `Avg ${money(order.filled_avg_price)}` : order.type ?? 'Order'}</Text></article>)}{orders.length === 0 && <Text color="secondary">No recent broker orders.</Text>}</VStack></Card>
        </>}
        <Card padding={4}><VStack gap={2}><Heading level={2}>Stocks & ETFs</Heading><Text type="supporting" color="secondary">Select an asset to view its chart and place a paper order.</Text>{watchlist.map(symbol => {const quote = quotes[symbol]; return <button className="asset-row" key={symbol} onClick={() => void openAsset(symbol)}><strong className="asset-symbol">{symbol}<small>{['SPY','VOO','QQQ'].includes(symbol) ? 'ETF' : 'Equity'}</small></strong><strong>{quote ? money(quote.price) : '—'}<small className={quote ? quote.change >= 0 ? 'gain' : 'loss' : ''}>{quote ? `${quote.change >= 0 ? '+' : ''}${quote.percent_change.toFixed(2)}%` : 'Quote unavailable'}</small></strong><strong className="asset-price">{quote ? new Date(quote.as_of).toLocaleTimeString() : '—'}<small>Finnhub quote</small></strong></button>;})}</VStack></Card>
        <Text type="supporting" color="secondary">Prices may be delayed. Account performance is provided by Alpaca. Research is informational.</Text>
      </VStack>}

      {tab === 'investing' && detail && <VStack gap={4}>
        <Button label="← Back to investing" variant="secondary" onClick={() => setDetail(false)}/>
        <Card padding={4} className="chart-panel"><VStack gap={3}><header className="instrument-header"><VStack gap={1}><Text type="label" color="secondary">{details.name ?? ticker} · {details.primary_exchange ?? details.market ?? 'MARKET DATA'}</Text><Heading level={2}>{money(activeQuote?.price)}</Heading></VStack><Text className={assetChange == null ? '' : assetChange >= 0 ? 'gain' : 'loss'}>{assetChange == null ? (busy ? 'Loading period change…' : 'Period change unavailable') : `${assetChange >= 0 ? '+' : ''}${money(assetChange)} (${pct(assetChangePercent)})`} · {assetPeriod}</Text></header><nav className="period-picker" aria-label="Price chart period">{periods.map(value => <button className={assetPeriod === value ? 'period-active' : ''} key={value} disabled={busy} aria-pressed={assetPeriod === value} onClick={() => void loadAssetPeriod(value)}>{value}</button>)}</nav><PriceChart key={`${ticker}-${assetPeriod}`} bars={bars}/><footer className="chart-footer"><Text type="supporting" color="secondary">{bars.length ? `${bars[0].date} — ${bars.at(-1)?.date} · Massive ${assetPeriod === '1D' ? '5-minute' : assetPeriod === 'ALL' ? 'weekly' : 'daily'} bars` : busy ? 'Loading chart…' : 'Price history unavailable'}</Text><Text type="supporting" color="secondary">Quote · {activeQuote ? new Date(activeQuote.as_of).toLocaleString() : '—'}</Text></footer></VStack></Card>
        <Grid columns={{minWidth: 180, max: 4, repeat: 'fit'}} gap={3}><Card padding={3}><Text type="label" color="secondary">SHARES HELD</Text><Heading level={3}>{activeHolding?.quantity ?? '0'}</Heading></Card><Card padding={3}><Text type="label" color="secondary">MARKET VALUE</Text><Heading level={3}>{money(activeHolding?.market_value)}</Heading></Card><Card padding={3}><Text type="label" color="secondary">AVERAGE COST</Text><Heading level={3}>{activeHolding && Number(activeHolding.quantity) ? money(Number(activeHolding.cost_basis) / Number(activeHolding.quantity)) : '—'}</Heading></Card><Card padding={3}><Text type="label" color="secondary">DAY RANGE</Text><Heading level={3}>{money(activeQuote?.low)} – {money(activeQuote?.high)}</Heading></Card></Grid>
        {details.description && <Card padding={4}><VStack gap={2}><Heading level={3}>About {details.name ?? ticker}</Heading><Text>{details.description}</Text><Text type="supporting" color="secondary">{details.type ?? 'Security'}{details.homepage_url ? ` · ${details.homepage_url}` : ''}</Text></VStack></Card>}
        <Card padding={4}><VStack gap={3}><Heading level={2}>Paper order</Heading><Text type="supporting" color="secondary">Whole-share limit order at the current quote. Submission is paper-only and subject to account risk controls and market hours.</Text><form className="order-form" onSubmit={event => {event.preventDefault(); setOrderSide(orderSide); setOrderKey(crypto.randomUUID()); setOrderReview(true); setOrderResult('');}}><nav className="side-toggle" aria-label="Order side"><button type="button" disabled={orderReview} className={orderSide === 'buy' ? 'period-active' : ''} onClick={() => setOrderSide('buy')}>Buy</button><button type="button" disabled={orderReview} className={orderSide === 'sell' ? 'period-active' : ''} onClick={() => setOrderSide('sell')}>Sell</button></nav><label className="native-field">Whole shares<input type="number" disabled={orderReview} value={quantity} onChange={event => setQuantity(event.target.value)} min="1" step="1" max={orderSide === 'sell' ? activeHolding?.quantity ?? '0' : '1000000'}/></label><Text>Estimated value · {money(Number(quantity) * (activeQuote?.price ?? 0))}</Text><Button label="Review paper order" type="submit" variant="primary" isDisabled={!activeQuote || !connected || !Number.isInteger(Number(quantity)) || Number(quantity) < 1 || Number(quantity) > 1000000 || (orderSide === 'sell' && Number(quantity) > Number(activeHolding?.quantity ?? 0))}/></form>{orderReview && <section className="order-review"><Text>Confirm {orderSide} {quantity} {ticker} at an estimated {money(activeQuote?.price)} per share? The broker rechecks quote freshness, cash, risk limits, and market hours.</Text><Button label="Confirm paper order" onClick={() => void submitOrder()} variant="primary" isLoading={busy}/><Button label="Cancel" variant="secondary" onClick={() => setOrderReview(false)}/></section>}{orderResult && <p role="status" className="order-result">{orderResult}{orderKey && <Button label="Check same order status" variant="secondary" onClick={() => void submitOrder()} isLoading={busy}/>}</p>}</VStack></Card>
      </VStack>}

      {tab === 'search' && <VStack gap={4}><Card padding={4}><VStack gap={3}><Heading level={2}>Find a stock or ETF</Heading><Text type="supporting" color="secondary">Search by ticker or company name across active US listings.</Text><form className="filing-search" onSubmit={searchAssets}><TextInput label="Ticker or company name" value={assetSearch} onChange={setAssetSearch} placeholder="NVDA or NVIDIA"/><Button label="Search" type="submit" variant="primary" isLoading={busy} isDisabled={!connected || !assetSearch.trim()}/></form></VStack></Card><Card padding={4}><VStack gap={2}><Heading level={2}>Results</Heading>{assetResults.map(result => <button className="asset-row" key={result.ticker} onClick={() => {setTab('investing'); void openAsset(result.ticker);}}><strong className="asset-symbol">{result.ticker}<small>{result.type ?? 'Security'}</small></strong><strong>{result.name ?? result.ticker}<small>{result.primary_exchange ?? result.market ?? 'US listing'}</small></strong><strong className="asset-price">View asset<small>Chart and paper order</small></strong></button>)}{connected && assetResults.length === 0 && <Text color="secondary">Enter a ticker or company name to search.</Text>}</VStack></Card></VStack>}

      {tab === 'filings' && <VStack gap={4}><Card padding={4}><VStack gap={3}><Heading level={2}>Search SEC filings</Heading><form className="filing-search" onSubmit={searchFilings}><TextInput label="Ticker" value={ticker} onChange={setTicker} placeholder="NVDA"/><TextInput label="Keyword (optional)" value={search} onChange={setSearch} placeholder="Revenue, risk factors…"/><label className="form-label">Form type<select value={form} onChange={event => setForm(event.target.value)}><option value="">All forms</option><option value="10-K">10-K</option><option value="10-Q">10-Q</option><option value="8-K">8-K</option><option value="4">Form 4</option><option value="13F-HR">13F-HR</option></select></label><Button label="Search filings" type="submit" variant="primary" isLoading={busy} isDisabled={!connected}/></form></VStack></Card><Card padding={4}><VStack gap={2}><Heading level={2}>Filing results</Heading>{filings.map((filing, index) => <article className="filing-row" key={`${filing.form}-${filing.filing_date}-${index}`}><strong>{filing.form}</strong><time>{filing.filing_date}</time><Text color="secondary">{filing.report_date ? `Period ${filing.report_date}` : ''}</Text>{filing.url && <a href={filing.url} target="_blank" rel="noreferrer">Open SEC filing ↗</a>}{filing.snippet && <Text color="secondary">{filing.snippet}</Text>}</article>)}{connected && !filings.length && <Text color="secondary">Search by ticker to load filing history.</Text>}</VStack></Card></VStack>}

      {tab === 'strategies' && <VStack gap={4}>
        <Card padding={4}><VStack gap={3}>
          <Heading level={2}>Agent portfolio workflow</Heading>
          <Text>Choose proposal-only research or explicitly opt in to one agent-directed paper run. No live trading is available.</Text>
          <nav className="period-picker" aria-label="Agent workflow mode"><button className={agentMode === 'proposal' ? 'period-active' : ''} onClick={() => setAgentMode('proposal')}>Proposal only</button><button className={agentMode === 'execute' ? 'period-active' : ''} onClick={() => setAgentMode('execute')}>Agent paper execution</button></nav>
          {agentMode === 'proposal' ? <>
            <Text type="supporting" color="secondary">The research agent proposes target weights; the API validates them against current account holdings and the limits below. This mode never submits an order.</Text>
            <form className="proposal-form" onSubmit={buildProposal}>
              <TextInput label="Symbols (up to 10)" value={proposalTickers} onChange={setProposalTickers} placeholder="NVDA, AAPL"/>
              <Grid columns={{minWidth: 180, max: 3, repeat: 'fit'}} gap={2}>
                {([['max_name_weight', 'Max name weight'], ['max_sector_weight', 'Max sector weight'], ['max_order_notional', 'Max order value ($)'], ['max_gross_notional', 'Max gross exposure ($)'], ['max_drawdown', 'Max drawdown']] as const).map(([key, label]) => <label className="native-field" key={key}>{label}<input type="number" min="0" step="any" max={key.includes('weight') || key === 'max_drawdown' ? '1' : undefined} value={proposalCaps[key]} onChange={event => setProposalCaps(previous => ({...previous, [key]: event.target.value}))}/></label>)}
              </Grid>
              <Text type="supporting" color="secondary">Fractions use 0–1 (for example 0.25 = 25%). Leave a limit blank to use the configured backend controls.</Text>
              <Button label="Generate validated proposal" type="submit" variant="primary" isLoading={busy} isDisabled={!connected}/>
            </form>
            {proposalResult && <VStack gap={3} className="proposal-results"><Heading level={3}>Portfolio proposal</Heading><Text type="supporting" color="secondary">Validated against account snapshot · {new Date(proposalResult.portfolio_retrieved_at).toLocaleString()}</Text>
              {proposalResult.breaches.length > 0 && <section className="error-message"><strong>Risk limit findings</strong>{proposalResult.breaches.map((item, index) => <p key={`${item.limit}-${index}`}>{item.limit}: {item.actual} exceeds {item.maximum}{item.subject ? ` · ${item.subject}` : ''}</p>)}</section>}
              {proposalResult.proposals.map(target => {return <article className="proposal-row" key={target.symbol}><strong>{target.symbol}</strong><strong>{pct(target.target_weight)} target</strong><Text>Confidence {pct(target.confidence)}</Text><Text>{target.rationale}</Text><Text type="supporting" color="secondary">Evidence {target.evidence.accessions.join(', ')} · quote {proposalResult.quotes.find(item => item.symbol === target.symbol)?.status ?? 'unknown'}</Text><Button label={`Open ${target.symbol} paper ticket`} variant="secondary" onClick={() => {setTicker(target.symbol); setOrderSide('buy'); setQuantity('1'); setTab('investing'); void openAsset(target.symbol);}}/></article>;})}
              {proposalResult.proposals.length === 0 && <Text color="secondary">No target weights were proposed for these symbols.</Text>}
            </VStack>}
          </> : <>
            <Text type="supporting" color="secondary">Phil will research your selected company and may submit at most one paper limit order. The server enforces Alpaca paper endpoint, regular market hours, fresh quote, cash, holdings, risk caps, and a durable idempotency key.</Text>
            <form className="agent-run-form" onSubmit={event => {event.preventDefault(); void runAgentPaper();}}>
              <TextInput label="Selected symbol" value={agentSymbol} onChange={setAgentSymbol} placeholder="NVDA"/>
              <label className="native-field">Research instructions<textarea value={agentPrompt} onChange={event => setAgentPrompt(event.target.value)} maxLength={4000} rows={4}/></label>
              <label className="confirm-paper"><input type="checkbox" checked={agentConfirmed} onChange={event => setAgentConfirmed(event.target.checked)}/> I confirm this one run may submit at most one order to the Alpaca paper account only.</label>
              <Button label={agentIntent ? 'Retry same paper run' : 'Run agent in paper mode'} type="submit" variant="primary" isLoading={busy} isDisabled={!connected || !agentConfirmed || !agentSymbol.trim() || !agentPrompt.trim()}/>
            </form>
            {agentResult && <p role="status" className="order-result">{agentResult}{agentIntent && <Button label="Check same run status" variant="secondary" onClick={() => void runAgentPaper(agentIntent)} isLoading={busy}/>}</p>}
          </>}
        </VStack></Card>

        <Card padding={4}><VStack gap={3}>
          <Heading level={2}>Strategy designer & replay</Heading>
          <Text>{strategyTypes[strategyKind].rule} Signals fill at the next session open in the simulation.</Text>
          <section className="strategy-drafts" aria-label="Saved strategy drafts"><label className="form-label">Saved drafts<select value={selectedStrategy} onChange={event => selectStrategyDraft(event.target.value)}><option value="">Unsaved draft</option>{strategyDrafts.map(draft => <option value={draft.id} key={draft.id}>{draft.name}</option>)}</select></label><Button label="New draft" type="button" variant="secondary" onClick={newStrategyDraft}/><Button label={selectedStrategy ? 'Update saved draft' : 'Save strategy draft'} type="button" variant="secondary" onClick={saveStrategyDraft}/></section>
          <form className="strategy-form" onSubmit={runBacktest}>
            <label className="form-label">Strategy type<select value={strategyKind} onChange={event => {setStrategyKind(event.target.value as StrategyKind); setBacktest(null);}}>{Object.entries(strategyTypes).map(([key, value]) => <option value={key} key={key}>{value.label}</option>)}</select></label>
            {strategyKind !== 'moving_average' && <label className="native-field">Number of selections<input type="number" min="1" max="10" step="1" value={topN} onChange={event => setTopN(event.target.value)} required/></label>}
            <TextInput label="Strategy name" value={strategyName} onChange={setStrategyName} placeholder="Monthly momentum replay"/>
            <TextInput label="Symbols (up to 10, comma separated)" value={strategySymbols} onChange={setStrategySymbols} placeholder="SPY, QQQ"/>
            {strategyKind !== 'quality_value' && <label className="native-field">Lookback sessions (2–200)<input type="number" min="2" max="200" step="1" value={lookback} onChange={event => setLookback(event.target.value)} required/></label>}
            <label className="native-field">Max allocation per asset (0–1)<input type="number" min="0.01" max="1" step="0.01" value={allocation} onChange={event => setAllocation(event.target.value)}/></label>
            {strategyKind === 'moving_average' && <label className="native-field">Stop-loss fraction (0–1)<input type="number" min="0.01" max="1" step="0.01" value={stopLoss} onChange={event => setStopLoss(event.target.value)} required/></label>}
            <label className="native-field">Initial cash ($)<input type="number" min="1" step="any" value={initialCash} onChange={event => setInitialCash(event.target.value)}/></label>
            <label className="native-field">Start date<input type="date" value={strategyStart} onChange={event => setStrategyStart(event.target.value)} required/></label>
            <label className="native-field">End date<input type="date" value={strategyEnd} onChange={event => setStrategyEnd(event.target.value)} required/></label>
            <Button label="Run live-data replay" type="submit" variant="primary" isLoading={busy} isDisabled={!connected}/>
            <Button label="Discuss this draft with Phil" type="button" variant="secondary" onClick={designStrategyWithPhil} isDisabled={!connected || busy}/>
          </form>
          <Text type="supporting" color="secondary">Strategy settings are editable for this replay. They are not saved to the backend.</Text>
          <form className="snapshot-form" onSubmit={replaySnapshot}><TextInput label="Saved snapshot ID" value={snapshotId} onChange={setSnapshotId} placeholder="Snapshot ID from the configured snapshots folder"/><Button label="Replay saved snapshot" type="submit" variant="secondary" isLoading={busy} isDisabled={!connected || !snapshotId.trim()}/></form>
        </VStack></Card>
        {backtest && <><Card padding={4}><VStack gap={2}><Heading level={2}>Replay comparison</Heading>
          <table className="replay-comparison"><thead><tr><th scope="col">Metric</th><th scope="col">Strategy</th><th scope="col">Equal-weight buy and hold</th></tr></thead><tbody>
            <tr><th scope="row">Final equity</th><td>{money(backtest.final_equity)}</td><td>{money(backtest.benchmark.final_equity)}</td></tr>
            <tr><th scope="row">Simulated return</th><td>{pct(Number(backtest.final_equity) / Number(backtest.initial_cash) - 1)}</td><td>{pct(Number(backtest.benchmark.final_equity) / Number(backtest.initial_cash) - 1)}</td></tr>
            <tr><th scope="row">Max drawdown</th><td>{pct(backtest.max_drawdown).replace(/^\+/, '')}</td><td>{pct(backtest.benchmark.max_drawdown).replace(/^\+/, '')}</td></tr>
            <tr><th scope="row">Traded value / starting cash</th><td>{pct(backtest.turnover).replace(/^\+/, '')}</td><td>{pct(backtest.benchmark.turnover).replace(/^\+/, '')}</td></tr>
          </tbody></table>
        </VStack></Card><Card padding={4}><VStack gap={3}><Heading level={2}>{strategyName} · Equity curve</Heading><PriceChart bars={backtest.equity_curve.map(point => ({date: point.date, close: Number(point.equity)}))}/><Text type="supporting" color="secondary">{backtest.start} — {backtest.end} · {backtest.fills.length} fills · SHA-256 {backtest.input_sha256}</Text>{backtest.fills.slice(0, 20).map((fill, index) => <article className="filing-row" key={`${fill.symbol}-${fill.fill_date}-${index}`}><strong>{fill.side.toUpperCase()} {fill.symbol}</strong><time>{fill.fill_date}</time><Text>{fill.quantity} shares</Text><Text>{money(fill.price)}</Text></article>)}</VStack></Card><Text type="supporting" color="secondary">Historical replay uses a fixed universe and excludes fees, slippage, and cash dividends. It is not a forecast.</Text></>}
        </VStack>}
    </VStack>

    {chatOpen ? <aside className={`phil-chat ${chatMinimized ? 'is-minimized' : ''}`} aria-label="Chat with Phil"><VStack gap={0} className="phil-shell"><header className="phil-header"><strong className="phil-avatar" aria-hidden="true">P</strong><VStack gap={0}><strong>Phil</strong><Text type="supporting" color="secondary">Monroe research agent</Text></VStack><i className={connected ? 'phil-online' : 'phil-offline'} aria-label={connected ? 'Connected' : 'Not connected'}/><Button label={chatMinimized ? "Restore" : "Minimize"} variant="ghost" onClick={() => setChatMinimized(value => !value)}/><Button label="Close" variant="ghost" onClick={() => {setChatOpen(false); setChatMinimized(false);}}/></header><section className="phil-messages" aria-live="polite" aria-label="Conversation">{messages.length === 0 && <article className="phil-bubble phil-reply">Hi, I’m Phil. Ask me about a company, its filings, or what’s moving the market.</article>}{messages.map((message, index) => <article className={`phil-bubble ${message.role === 'user' ? 'phil-prompt' : 'phil-reply'}`} key={`${message.role}-${index}`}><RichAnswer text={message.text}/>{message.visuals?.map((visual, vi) => <ResearchVisualCard key={`${visual.symbol}-${visual.statement}-${vi}`} visual={visual}/>)}{message.citations?.map((citation, citationIndex) => <p key={`${citation.url}-${citationIndex}`} className="chat-citation">{citation.url ? <a href={citation.url} target="_blank" rel="noreferrer">{citation.title || citation.accession_number || 'Source'}</a> : citation.title || citation.accession_number || 'Source'}</p>)}</article>)}{busy && <Text type="supporting" color="secondary">Phil is researching…</Text>}{chatError && <p className="chat-error" role="alert">{chatError}</p>}</section><form className="phil-composer" onSubmit={askPhil}><TextInput label="Message Phil" isLabelHidden value={question} onChange={setQuestion} placeholder="Ask Phil anything…" isDisabled={!connected || busy || transcribing}/><Button label={recording ? 'Stop recording' : 'Record question'} variant={recording ? 'destructive' : 'secondary'} isDisabled={!connected || busy || transcribing} onClick={() => recording ? recorderRef.current?.stop() : void startRecording()}/><Button label="Send" type="submit" variant="primary" isDisabled={!connected || busy || !question.trim()} isLoading={busy}/></form>{voiceStatus && <Text type="supporting" color="secondary" className="voice-status">{voiceStatus}</Text>}<label className="visual-select">Response visual<select value={visualMode} onChange={event => setVisualMode(event.target.value as typeof visualMode)}><option value="auto">Automatic</option><option value="table">SEC table</option><option value="bar">Bar chart</option><option value="line">Line chart</option></select></label><Text type="supporting" color="secondary" className="phil-disclaimer">Voice transcripts are shown for review before sending.</Text></VStack></aside> : <><button className="phil-launcher" onClick={() => {setChatOpen(true); setTeaser(false);}} aria-label="Open Phil chat">P</button>{teaser && <button className="phil-teaser" onClick={() => {setChatOpen(true); setTeaser(false);}}>Need a hand? Ask Phil <strong aria-hidden="true">×</strong></button>}</>}
    <footer className="site-footer"><Text type="supporting" color="secondary">Investing information is provided for research. Paper orders are subject to backend risk controls. No live order route is available.</Text></footer>
  </VStack>;
}
