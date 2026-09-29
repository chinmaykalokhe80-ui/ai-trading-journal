'use client';
import { useEffect, useRef, useState } from 'react';
import { BrainCircuit, Loader2, Sparkles } from 'lucide-react';
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

type Provider = { id: string; name: string; configured: boolean; model: string | null; url: string | null; note: string };
type Finding = { id: string; title: string; evidence: string; action: string; success_measure: string; principle: string; confidence: string };
type Metrics = {
  count: number; pnl: number; wins: number; losses: number; breakeven: number; win_rate: number;
  expectancy: number | null; profit_factor: number | null; average_win: number | null; average_loss: number | null;
  payoff_ratio: number | null; max_drawdown: number | null; pnl_without_best: number;
  max_win_streak: number | null; max_loss_streak: number | null; average_r: number | null;
  largest_win: number; largest_loss: number; win_rate_interval: [number, number] | null;
};
type Report = {
  source: string; summary: string; metrics: Metrics; excluded_open: number;
  strengths: Finding[]; weaknesses: Finding[];
  coverage: { notes: number; stop_plans: number; strategy_tags: number; risk_measurable: number; total: number };
  action_plan: { priority: number; focus: string; action: string; measure: string }[];
  breakdowns: Record<string, (Metrics & { name: string; preliminary: boolean })[]>;
  equity_curve: { date: string; pnl: number }[];
  review_candidates: { id: string; symbol: string; pnl: number; question: string }[];
  principles: { id: string; title: string; author: string; url: string; principle: string }[];
  limitations: string[]; methodology: string;
  llm: { status: string; provider: string; model?: string; message: string; summary?: string; review_questions?: string[]; practice_exercise?: string };
};
const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';
const money = (v: number | null) => v === null ? 'Not available' : `₹${v.toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;
const ratio = (v: number | null) => v === null ? 'Not available' : `${v.toFixed(2)}×`;
const card = 'rounded-xl border border-slate-800 bg-slate-950/60 p-4';
const initial: Provider[] = [{ id: 'rules', name: 'Local rules — no API key', configured: true, model: null, url: null, note: 'No data leaves the journal.' }];

export function AIPnLAnalyzer() {
  const [file, setFile] = useState<File | null>(null);
  const [provider, setProvider] = useState('rules');
  const [providers, setProviders] = useState(initial);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<Report | null>(null);
  const request = useRef<AbortController | null>(null);
  const busy = useRef(false);
  useEffect(() => {
    const controller = new AbortController();
    fetch(`${API}/ai-coach/providers`, { signal: controller.signal }).then((r) => r.ok ? r.json() : null)
      .then((d) => { if (d && !controller.signal.aborted) setProviders(d.providers); }).catch(() => {});
    return () => { controller.abort(); request.current?.abort(); };
  }, []);
  const analyze = async (source: 'journal' | 'upload') => {
    if (busy.current) return;
    if (source === 'upload' && !file) { setError('Select a P&L report first.'); return; }
    busy.current = true; setAnalyzing(true); setError(null); setReport(null);
    const controller = new AbortController(); request.current = controller;
    try {
      const form = new FormData(); if (file) form.append('file', file);
      const response = await fetch(source === 'upload' ? `${API}/ai-coach/analyze-csv?provider=${encodeURIComponent(provider)}` : `${API}/ai-coach/analyze-journal`, {
        method: 'POST', signal: controller.signal,
        ...(source === 'upload' ? { body: form } : { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ provider }) }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Could not analyze these records.');
      if (!controller.signal.aborted) setReport(data.report);
    } catch (err) {
      if (!controller.signal.aborted) setError(err instanceof Error ? err.message : 'Analysis failed.');
    } finally { busy.current = false; if (!controller.signal.aborted) setAnalyzing(false); }
  };
  const selected = providers.find((p) => p.id === provider);
  const finding = (f: Finding) => {
    const book = report?.principles.find((p) => p.id === f.principle);
    return <article className={card} key={f.id}><h4 className="font-semibold text-slate-100">{f.title}</h4><p className="text-xs text-slate-500">{f.confidence}</p>
      <p className="mt-2 text-slate-200">{f.evidence}</p><p className="mt-2 text-slate-400"><strong>Next step: </strong>{f.action}</p>
      <p className="mt-2 text-slate-400"><strong>Measure: </strong>{f.success_measure}</p>
      {book && <a href={book.url} target="_blank" rel="noreferrer" className="mt-2 inline-block text-xs text-cyan-400 underline">Principle: {book.title}</a>}
    </article>;
  };
  return <section className="rounded-2xl border border-cyan-500/30 bg-slate-900/80 p-4 md:p-6 space-y-5">
    <header className="flex gap-3"><BrainCircuit className="w-7 h-7 text-cyan-400 shrink-0" /><div><h2 className="text-xl font-bold text-slate-100">Trade review & improvement plan</h2><p className="text-sm text-slate-400 mt-1">Evidence first. Understand what worked, what needs attention, and what to practice next.</p></div></header>
    <div className="flex flex-wrap gap-3 items-end">
      <label className="text-xs text-slate-400">Analysis method<select value={provider} disabled={analyzing} onChange={(e) => setProvider(e.target.value)} className="block mt-1 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200">{providers.map((p) => <option key={p.id} value={p.id} disabled={!p.configured}>{p.name}{!p.configured ? ' — key required' : ''}</option>)}</select></label>
      <button onClick={() => analyze('journal')} disabled={analyzing} className="flex items-center gap-2 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 rounded-lg px-4 py-2 text-sm text-white font-semibold">{analyzing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}Analyze saved trades</button>
      <span className="text-xs text-slate-500">All closed records; dashboard filters do not limit this review.</span>
    </div>
    <p className="text-xs text-slate-400">{selected?.note} {provider !== 'rules' && 'Pressing Analyze sends computed aggregate metrics to this provider. Raw files, notes, symbols and account identifiers are excluded. Free-tier access depends on your account; paid accounts may incur charges.'}</p>
    <div className="flex flex-wrap items-center gap-3 rounded-xl border border-slate-800 p-3">
      <label className="text-sm text-slate-300">Or analyze a report<input type="file" accept=".csv,.xlsx,.xls" disabled={analyzing} onChange={(e) => { setFile(e.target.files?.[0] || null); setError(null); }} className="block mt-2 max-w-full text-xs text-slate-400" /></label>
      <button disabled={analyzing || !file} onClick={() => analyze('upload')} className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-200 disabled:opacity-40">Analyze report</button><span className="text-xs text-slate-500">Read-only · up to 10 MB · no trades added</span>
    </div>
    <details className="text-xs text-slate-400"><summary className="text-cyan-400 cursor-pointer">Optional free-tier LLM choices</summary><div className="mt-3 grid md:grid-cols-3 gap-3">{providers.filter((p) => p.id !== 'rules').map((p) => <div className={card} key={p.id}><a href={p.url!} target="_blank" rel="noreferrer" className="text-cyan-300 underline">{p.name}</a><p className="mt-2">{p.note}</p><p className="mt-2">{p.configured ? 'Configured' : 'Requires backend API-key setup'}</p></div>)}</div></details>
    {error && <p role="alert" className="text-sm text-rose-300 border border-rose-800 rounded-lg p-3">{error}</p>}
    {analyzing && <p role="status" className="text-sm text-cyan-300">Calculating evidence and preparing your review…</p>}
    {report && <div className="space-y-6 text-sm">
      <div className={card}><p className="text-xs uppercase tracking-wide text-cyan-400">{report.source === 'journal' ? 'Saved journal' : 'Uploaded report'} · local assessment</p><p className="mt-2 text-slate-200">{report.summary}</p>{report.excluded_open > 0 && <p className="mt-2 text-slate-400">{report.excluded_open} open records excluded.</p>}</div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">{[
        ['P&L', money(report.metrics.pnl)], ['Expectancy / record', money(report.metrics.expectancy)], ['Profit factor', ratio(report.metrics.profit_factor)], ['Payoff ratio', ratio(report.metrics.payoff_ratio)],
        ['Win rate', `${report.metrics.win_rate}%`], ['Average win / loss', `${money(report.metrics.average_win)} / ${money(report.metrics.average_loss)}`], ['Daily realized drawdown', money(report.metrics.max_drawdown)], ['P&L without best record', money(report.metrics.pnl_without_best)],
        ['Longest win / loss streak', `${report.metrics.max_win_streak ?? 'N/A'} / ${report.metrics.max_loss_streak ?? 'N/A'}`], ['Average R (measurable subset)', report.metrics.average_r === null ? 'Not available' : `${report.metrics.average_r.toFixed(2)}R`], ['Largest win / loss', `${money(report.metrics.largest_win)} / ${money(report.metrics.largest_loss)}`], ['Flat records', String(report.metrics.breakeven)],
      ].map(([label, value]) => <div className={card} key={label}><p className="text-xs text-slate-400">{label}</p><p className="mt-1 font-mono font-semibold text-slate-100">{value}</p></div>)}</div>
      <p className="text-xs text-slate-500">{report.metrics.win_rate_interval && `Approximate 95% win-rate interval: ${report.metrics.win_rate_interval[0]}–${report.metrics.win_rate_interval[1]}%. `}Unavailable ratios need both relevant outcomes. Missing dates or risk data are not treated as zero.</p>
      {report.equity_curve.length > 1 && <div className={card}><h3 className="font-semibold text-slate-200">Cumulative realized P&L by day</h3><div className="mt-3 h-56" role="img" aria-label="Daily cumulative realized P&L, not account equity"><ResponsiveContainer width="100%" height="100%"><AreaChart data={report.equity_curve}><CartesianGrid stroke="#1e293b" /><XAxis dataKey="date" tick={{ fill: '#94a3b8', fontSize: 11 }} /><YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} /><Tooltip contentStyle={{ background: '#0f172a', borderColor: '#334155' }} /><Area type="linear" dataKey="pnl" stroke="#22d3ee" fill="#0891b2" fillOpacity={0.18} /></AreaChart></ResponsiveContainer></div></div>}
      <div className="grid md:grid-cols-2 gap-4"><div className="space-y-3"><h3 className="text-base font-bold text-emerald-300">Strengths supported by the sample</h3>{report.strengths.length ? report.strengths.map(finding) : <p className={card}>Not enough evidence to identify a repeatable strength yet.</p>}</div><div className="space-y-3"><h3 className="text-base font-bold text-amber-300">Weaknesses & review priorities</h3>{report.weaknesses.length ? report.weaknesses.map(finding) : <p className={card}>No rule-based concern triggered. This does not establish that the process is sound.</p>}</div></div>
      <div className="space-y-3"><h3 className="text-base font-bold text-cyan-300">Your practice plan</h3>{report.action_plan.map((p) => <article className={card} key={p.priority}><h4 className="font-semibold text-slate-100">{p.priority}. {p.focus}</h4><p className="mt-2 text-slate-300">{p.action}</p><p className="mt-2 text-cyan-300">Track progress: {p.measure}</p></article>)}</div>
      <div className="grid lg:grid-cols-3 gap-3">{Object.entries(report.breakdowns).map(([kind, groups]) => <div className={`${card} overflow-x-auto`} key={kind}><h3 className="capitalize font-semibold text-slate-200 mb-3">By {kind}</h3><table className="w-full text-xs"><thead><tr className="text-left text-slate-500"><th>Group</th><th>Rows</th><th className="text-right">P&L</th><th className="text-right">Win %</th></tr></thead><tbody>{groups.map((g) => <tr key={g.name} className="border-t border-slate-800 text-slate-300"><td className="py-2 pr-2">{g.name}{g.preliminary ? ' *' : ''}</td><td>{g.count}</td><td className="text-right">{money(g.pnl)}</td><td className="text-right">{g.win_rate}%</td></tr>)}</tbody></table><p className="mt-2 text-xs text-slate-500">* Fewer than 5 records. Groups are descriptive, not causal comparisons.</p></div>)}</div>
      {report.review_candidates.length > 0 && <details className={card}><summary className="font-semibold text-slate-200 cursor-pointer">Records to review first</summary><div className="mt-3 space-y-3">{report.review_candidates.map((r) => <div key={r.id}><p className="text-amber-300">{r.symbol} · {money(r.pnl)}</p><p className="text-xs text-slate-500">{r.id}</p><p className="text-slate-400">{r.question}</p></div>)}</div></details>}
      {report.llm.provider !== 'rules' && <section className={card}><h3 className="font-semibold text-cyan-300">Optional LLM perspective · {report.llm.provider}</h3><p className="mt-2 text-xs text-slate-400">{report.llm.message} {report.llm.model}</p>{report.llm.summary && <p className="mt-3 text-slate-200">{report.llm.summary}</p>}{report.llm.review_questions && <ul className="mt-3 list-disc pl-5 space-y-1 text-slate-300">{report.llm.review_questions.map((q, i) => <li key={i}>{q}</li>)}</ul>}{report.llm.practice_exercise && <p className="mt-3 text-cyan-200">Practice: {report.llm.practice_exercise}</p>}</section>}
      <details className={card} open><summary className="font-semibold text-slate-200 cursor-pointer">What this data can and cannot establish</summary>{report.source === 'journal' && <p className="mt-3 text-slate-300">Coverage: {report.coverage.notes}/{report.coverage.total} notes, {report.coverage.stop_plans}/{report.coverage.total} stop plans, {report.coverage.strategy_tags}/{report.coverage.total} strategy tags. Risk measurable on {report.coverage.risk_measurable} records.</p>}<ul className="mt-3 list-disc pl-5 space-y-2 text-xs text-slate-400">{report.limitations.map((l) => <li key={l}>{l}</li>)}</ul></details>
      <details className={card}><summary className="font-semibold text-slate-200 cursor-pointer">Trading principles & sources</summary><p className="mt-3 text-xs text-slate-500">{report.methodology}</p><div className="mt-3 grid md:grid-cols-3 gap-4">{report.principles.map((p) => <div key={p.id}><a href={p.url} target="_blank" rel="noreferrer" className="text-cyan-300 underline">{p.title}</a><p className="text-xs text-slate-500">{p.author}</p><p className="mt-2 text-slate-400">{p.principle}</p></div>)}</div></details>
    </div>}
  </section>;
}
