'use client';

import React, { useEffect, useState, useRef } from 'react';
import { fetchTrades, clearTrades, Trade } from '@/lib/api';
import { TradeTable } from '@/components/TradeTable';
import { TradeUploadModal } from '@/components/TradeUploadModal';
import { ManualTradeModal } from '@/components/ManualTradeModal';
import { AIPnLAnalyzer } from '@/components/AIPnLAnalyzer';
import { formatSignedPnl, pnlTextClass } from '@/lib/pnlDisplay';
import {
  TrendingUp,
  TrendingDown,
  Upload,
  Plus,
  RefreshCw,
  SlidersHorizontal,
} from 'lucide-react';

export default function DashboardPage() {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);
  const [analysisKey, setAnalysisKey] = useState(0);
  const requestVersion = useRef(0);
  const clearingRef = useRef(false);
  const [clearing, setClearing] = useState(false);

  const [segmentFilter, setSegmentFilter] = useState<string>('');
  const [emotionFilter, setEmotionFilter] = useState<string>('');

  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [isManualOpen, setIsManualOpen] = useState(false);

  const loadData = () => {
    requestVersion.current += 1;
    setLoading(true);
    setRevision((value) => value + 1);
  };

  useEffect(() => {
    let active = true;
    const version = ++requestVersion.current;
    if (clearing) return;
    fetchTrades({ segment: segmentFilter, emotion_tag: emotionFilter }).then((tradesData) => {
      if (!active || version !== requestVersion.current) return;
      setTrades(tradesData);
      setError(null);
    }).catch((err: unknown) => {
      if (active && version === requestVersion.current) {
        setError(err instanceof Error ? err.message : 'Failed to load journal');
      }
    }).finally(() => {
      if (active && version === requestVersion.current) setLoading(false);
    });
    return () => { active = false; };
  }, [segmentFilter, emotionFilter, revision, clearing]);

  const handleRefresh = async () => {
    if (clearingRef.current) return;
    clearingRef.current = true;
    requestVersion.current += 1;
    setClearing(true);
    setLoading(true);
    setError(null);
    try {
      await clearTrades();
      setTrades([]);
      setSegmentFilter('');
      setEmotionFilter('');
      setAnalysisKey((key) => key + 1);
      setIsUploadOpen(false);
      setIsManualOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to clear trades.');
    } finally {
      clearingRef.current = false;
      setClearing(false);
      setLoading(false);
    }
  };

  // Aggregate Metrics
  const totalTrades = trades.length;
  const grossPnL = trades.reduce((acc, t) => acc + (t.gross_pnl || 0), 0);
  const closedTrades = trades.filter((t) => t.status === 'closed');
  const winningTrades = closedTrades.filter((t) => (t.gross_pnl || 0) > 0).length;
  const winRate = closedTrades.length > 0 ? ((winningTrades / closedTrades.length) * 100).toFixed(1) : '0.0';

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans selection:bg-cyan-500 selection:text-slate-950 p-4 md:p-8">
      {/* Background Accent Gradients */}
      <div className="fixed top-0 left-1/4 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none -z-10" />
      <div className="fixed top-1/3 right-10 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl pointer-events-none -z-10" />

      <main className="max-w-7xl mx-auto space-y-6">
        {/* Header Bar */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-slate-900/40 p-6 rounded-2xl border border-slate-800/80 backdrop-blur-xl">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold font-mono tracking-wider bg-cyan-500/20 text-cyan-400 border border-cyan-500/30">
                INDIAN EQUITY & F&O
              </span>
              <span className="text-xs text-slate-400">NSE / BSE Journal</span>
            </div>
            <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight text-white bg-clip-text text-transparent bg-gradient-to-r from-slate-100 via-slate-200 to-slate-400">
              Advanced AI Trading Journal
            </h1>
          </div>

          <div className="flex items-center gap-3 flex-wrap">
            <button
              disabled={clearing}
              onClick={() => setIsUploadOpen(true)}
              className="px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-200 hover:text-white border border-slate-700/80 rounded-xl text-xs font-bold transition-all flex items-center gap-2 shadow-lg"
            >
              <Upload className="w-4 h-4 text-cyan-400" />
              Upload Zerodha CSV
            </button>

            <button
              disabled={clearing}
              onClick={() => setIsManualOpen(true)}
              className="px-4 py-2.5 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white rounded-xl text-xs font-bold transition-all flex items-center gap-2 shadow-lg shadow-cyan-600/20"
            >
              <Plus className="w-4 h-4" />
              Log Manual Trade
            </button>

            <button
              onClick={handleRefresh}
              disabled={loading || clearing}
              className="px-4 py-2.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200 border border-slate-700 rounded-xl text-xs font-bold flex items-center gap-2"
              title="Refresh clears all saved trades and analysis"
            >
              <RefreshCw className={`w-4 h-4 ${clearing ? 'animate-spin' : ''}`} />
              {clearing ? 'Clearing…' : 'Refresh'}
            </button>
            <span className="text-xs text-slate-400">Refresh clears all previous trades.</span>
          </div>
        </div>

        {/* AI PnL CSV Analyzer Box */}
        <AIPnLAnalyzer key={analysisKey} />
        {error && <p role="alert" className="text-rose-300">{error}</p>}
        {loading && <p role="status" className="text-slate-400">Loading trades…</p>}

        {/* Metrics Summary Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {/* Net PnL */}
          <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-4 backdrop-blur-md">
            <div className="text-xs text-slate-400 font-medium mb-1">P&L</div>
            <div className={`text-xl font-bold font-mono ${pnlTextClass(grossPnL)}`}>
              {formatSignedPnl(grossPnL)}
            </div>
            <div className="text-[11px] text-slate-500 mt-1 flex items-center gap-1">
              {grossPnL > 0 && <TrendingUp className="w-3.5 h-3.5 text-emerald-300" />}
              {grossPnL < 0 && <TrendingDown className="w-3.5 h-3.5 text-rose-300" />}
              Realized trading result
            </div>
          </div>

          {/* Win Rate */}
          <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-4 backdrop-blur-md">
            <div className="text-xs text-slate-400 font-medium mb-1">Win Rate</div>
            <div className="text-xl font-bold font-mono text-cyan-400">{winRate}%</div>
            <div className="text-[11px] text-slate-500 mt-1">{winningTrades} win(s) of {closedTrades.length} closed</div>
          </div>

          {/* Total Trades */}
          <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-4 backdrop-blur-md">
            <div className="text-xs text-slate-400 font-medium mb-1">Total Executed Trades</div>
            <div className="text-xl font-bold font-mono text-slate-200">{totalTrades}</div>
            <div className="text-[11px] text-slate-500 mt-1">Ingested or manual</div>
          </div>
        </div>

        {/* Filter Toolbar */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 bg-slate-900/40 p-4 rounded-2xl border border-slate-800/80 backdrop-blur-xl">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-300">
            <SlidersHorizontal className="w-4 h-4 text-cyan-400" />
            Filter Trade Log:
          </div>

          <div className="flex items-center gap-3 w-full sm:w-auto">
            {/* Segment Selector */}
            <select
              value={segmentFilter}
              onChange={(e) => { requestVersion.current += 1; setLoading(true); setSegmentFilter(e.target.value); }}
              className="bg-slate-950 border border-slate-700/80 rounded-xl px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
            >
              <option value="">All Segments</option>
              <option value="Equity">Equity</option>
              <option value="CE">CE (Call Options)</option>
              <option value="PE">PE (Put Options)</option>
              <option value="Futures">Futures</option>
            </select>

            {/* Emotion Selector */}
            <select
              value={emotionFilter}
              onChange={(e) => { requestVersion.current += 1; setLoading(true); setEmotionFilter(e.target.value); }}
              className="bg-slate-950 border border-slate-700/80 rounded-xl px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
            >
              <option value="">All Emotions</option>
              <option value="Neutral">Neutral</option>
              <option value="Disciplined">Disciplined</option>
              <option value="Confident">Confident</option>
              <option value="FOMO">FOMO</option>
              <option value="Revenge">Revenge</option>
              <option value="Anxious">Anxious</option>
            </select>
          </div>
        </div>

        {/* Core Trade Log Table */}
        <TradeTable trades={trades} onRefresh={loadData} />
      </main>

      {/* Modals */}
      <TradeUploadModal
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        onSuccess={loadData}
      />
      <ManualTradeModal
        isOpen={isManualOpen}
        onClose={() => setIsManualOpen(false)}
        onSuccess={loadData}
      />
    </div>
  );
}
