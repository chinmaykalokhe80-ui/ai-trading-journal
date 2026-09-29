'use client';

import React, { useState } from 'react';
import { Trade, updateTrade } from '@/lib/api';
import { ChevronDown, ChevronUp, Edit3, Tag, Smile, Layers } from 'lucide-react';
import { formatSignedPnl, pnlBadgeClass, pnlRowClass } from '@/lib/pnlDisplay';

interface Props {
  trades: Trade[];
  onRefresh: () => void;
}

const EMOTION_OPTIONS = ['Neutral', 'FOMO', 'Revenge', 'Confident', 'Anxious', 'Disciplined'] as const;
const STRATEGY_OPTIONS = ['CSV Upload', 'Breakout', 'Reversal', 'Trend Following', 'Scalping', 'Swing', 'Unassigned'] as const;

export const TradeTable: React.FC<Props> = ({ trades, onRefresh }) => {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editEmotion, setEditEmotion] = useState<Trade['emotion_tag']>('Neutral');
  const [editStrategy, setEditStrategy] = useState<string>('');
  const [editNotes, setEditNotes] = useState<string>('');
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const [sortField, setSortField] = useState<'entry_time' | 'gross_pnl'>('entry_time');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  const startEdit = (trade: Trade) => {
    setEditingId(trade.id);
    setEditEmotion(trade.emotion_tag || 'Neutral');
    setEditStrategy(trade.strategy_tag || '');
    setEditNotes(trade.notes || '');
  };

  const saveEdit = async (tradeId: string) => {
    try {
      await updateTrade(tradeId, {
        emotion_tag: editEmotion,
        strategy_tag: editStrategy,
        notes: editNotes,
      });
      setEditingId(null);
      onRefresh();
    } catch {
      alert('Error updating trade');
    }
  };

  const handleSort = (field: 'entry_time' | 'gross_pnl') => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('desc');
    }
  };

  const sortedTrades = [...trades].sort((a, b) => {
    let aVal: string | number = a[sortField];
    let bVal: string | number = b[sortField];
    if (sortField === 'entry_time') {
      aVal = new Date(a.entry_time).getTime();
      bVal = new Date(b.entry_time).getTime();
    }
    if (aVal === bVal) return 0;
    if (sortOrder === 'asc') return aVal > bVal ? 1 : -1;
    return aVal < bVal ? 1 : -1;
  });

  return (
    <div className="w-full bg-slate-900/60 border border-slate-800/80 backdrop-blur-xl rounded-2xl shadow-2xl overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm text-slate-300">
          <thead className="bg-slate-950/80 text-xs uppercase tracking-wider text-slate-400 border-b border-slate-800">
            <tr>
              <th className="py-4 px-4 font-semibold cursor-pointer hover:text-slate-200" onClick={() => handleSort('entry_time')}>
                <div className="flex items-center gap-1">
                  Date / Time
                  {sortField === 'entry_time' && (sortOrder === 'asc' ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />)}
                </div>
              </th>
              <th className="py-4 px-4 font-semibold">Instrument & Segment</th>
              <th className="py-4 px-4 font-semibold">Strategy Tag</th>
              <th className="py-4 px-4 font-semibold">Emotion</th>
              <th className="py-4 px-4 font-semibold text-right cursor-pointer hover:text-slate-200" onClick={() => handleSort('gross_pnl')}>
                <div className="flex items-center justify-end gap-1">
                  P&L
                  {sortField === 'gross_pnl' && (sortOrder === 'asc' ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />)}
                </div>
              </th>
              <th className="py-4 px-4 font-semibold text-center">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {sortedTrades.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-12 text-center text-slate-500 font-medium">
                  No trades found. Upload a Zerodha Tradebook CSV or add a trade manually.
                </td>
              </tr>
            ) : (
              sortedTrades.map((t) => {
                const isEditing = editingId === t.id;
                const isExpanded = expandedId === t.id;
                const pnl = t.gross_pnl ?? 0;
                const instName = t.legs?.[0]?.instrument || 'Instrument';

                return (
                  <React.Fragment key={t.id}>
                    <tr className={`${pnlRowClass(pnl)} transition-colors group`}>
                      {/* Date / Time */}
                      <td className="py-4 px-4 whitespace-nowrap">
                        <div className="font-medium text-slate-200">
                          {new Date(t.entry_time).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })}
                        </div>
                        <div className="text-xs text-slate-400 font-mono">
                          {new Date(t.entry_time).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}
                        </div>
                      </td>

                      {/* Instrument & Segment */}
                      <td className="py-4 px-4">
                        <div className="font-semibold text-slate-100 flex items-center gap-2">
                          {instName}
                          <span
                            className={`text-[10px] px-2 py-0.5 rounded-full font-mono font-bold tracking-wide uppercase ${t.legs?.[0]?.segment === 'CE'
                                ? 'bg-sky-500/20 text-sky-300 border border-sky-500/30'
                                : t.legs?.[0]?.segment === 'PE'
                                  ? 'bg-violet-500/20 text-violet-300 border border-violet-500/30'
                                  : t.legs?.[0]?.segment === 'Futures'
                                    ? 'bg-purple-500/20 text-purple-400 border border-purple-500/30'
                                    : 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                              }`}
                          >
                            {t.legs?.[0]?.segment || 'Equity'}
                          </span>
                        </div>
                        <div className="text-xs text-slate-400 mt-0.5">
                          {t.legs?.length || 1} leg(s) executed · {t.status}
                        </div>
                      </td>

                      {/* Strategy Tag */}
                      <td className="py-4 px-4">
                        {isEditing ? (
                          <select
                            value={editStrategy}
                            onChange={(e) => setEditStrategy(e.target.value)}
                            className="bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1 text-xs text-slate-200 focus:outline-none focus:border-cyan-500 w-32"
                          >
                            <option value="">-- Select Strategy --</option>
                            {STRATEGY_OPTIONS.map((opt) => (
                              <option key={opt} value={opt}>
                                {opt}
                              </option>
                            ))}
                          </select>
                        ) : (
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-800/80 border border-slate-700/60 text-slate-300 text-xs font-medium">
                            <Tag className="w-3 h-3 text-cyan-400" />
                            {t.strategy_tag || 'Unassigned'}
                          </span>
                        )}
                      </td>

                      {/* Emotion Tag */}
                      <td className="py-4 px-4">
                        {isEditing ? (
                          <select
                            value={editEmotion}
                            onChange={(e) => setEditEmotion(e.target.value as Trade['emotion_tag'])}
                            className="bg-slate-950 border border-slate-700 rounded-lg px-2 py-1 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
                          >
                            {EMOTION_OPTIONS.map((opt) => (
                              <option key={opt} value={opt}>
                                {opt}
                              </option>
                            ))}
                          </select>
                        ) : (
                          <span
                            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium border ${t.emotion_tag === 'Disciplined'
                                ? 'bg-cyan-950/60 text-cyan-300 border-cyan-800/60'
                                : t.emotion_tag === 'Confident'
                                  ? 'bg-indigo-950/60 text-indigo-300 border-indigo-800/60'
                                  : t.emotion_tag === 'FOMO' || t.emotion_tag === 'Revenge'
                                    ? 'bg-amber-950/60 text-amber-300 border-amber-800/60'
                                    : 'bg-slate-800/60 text-slate-300 border-slate-700/60'
                              }`}
                          >
                            <Smile className="w-3 h-3" />
                            {t.emotion_tag || 'Neutral'}
                          </span>
                        )}
                      </td>

                      {/* P&L */}
                      <td className="py-4 px-4 text-right">
                        <span
                          className={`font-mono font-bold text-sm px-2.5 py-1 rounded-lg ${pnlBadgeClass(pnl)}`}
                        >
                          {formatSignedPnl(pnl)}
                        </span>
                      </td>

                      {/* Actions */}
                      <td className="py-4 px-4 text-center">
                        <div className="flex items-center justify-center gap-2">
                          {isEditing ? (
                            <button
                              onClick={() => saveEdit(t.id)}
                              className="bg-cyan-600 hover:bg-cyan-500 text-white px-2.5 py-1 rounded-lg text-xs font-semibold shadow-md transition-colors"
                            >
                              Save
                            </button>
                          ) : (
                            <button
                              onClick={() => startEdit(t)}
                              className="text-slate-400 hover:text-slate-200 p-1.5 rounded-lg hover:bg-slate-800 transition-colors"
                              title="Edit Emotion & Strategy"
                            >
                              <Edit3 className="w-4 h-4" />
                            </button>
                          )}
                          <button
                            onClick={() => setExpandedId(isExpanded ? null : t.id)}
                            className="text-slate-400 hover:text-slate-200 p-1.5 rounded-lg hover:bg-slate-800 transition-colors"
                            title="View Leg Breakdown"
                          >
                            <Layers className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>

                    {/* Expanded Drawer for Leg Breakdown & Notes */}
                    {isExpanded && (
                      <tr className="bg-slate-950/90 border-b border-slate-800">
                        <td colSpan={6} className="p-4">
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                            <div className="bg-slate-900/80 p-3 rounded-xl border border-slate-800">
                              <h5 className="font-semibold text-slate-300 mb-2 flex items-center gap-1.5">
                                <Layers className="w-3.5 h-3.5 text-cyan-400" />
                                Execution Legs ({t.legs?.length || 0})
                              </h5>
                              <div className="space-y-1.5">
                                {t.legs?.map((leg, idx) => (
                                  <div key={idx} className="flex items-center justify-between text-slate-300 bg-slate-950/60 p-2 rounded-lg font-mono">
                                    <span className={leg.side === 'buy' ? 'text-sky-300 font-bold' : 'text-violet-300 font-bold'}>
                                      {leg.side.toUpperCase()} {leg.quantity} @ ₹{leg.price}
                                    </span>
                                    <span className="text-slate-400 text-[11px]">{leg.instrument} ({leg.segment})</span>
                                  </div>
                                ))}
                              </div>
                            </div>
                            <div className="bg-slate-900/80 p-3 rounded-xl border border-slate-800 flex flex-col justify-between">
                              <div>
                                <h5 className="font-semibold text-slate-300 mb-1">Trade Notes & Reflections</h5>
                                {isEditing ? (
                                  <textarea
                                    value={editNotes}
                                    onChange={(e) => setEditNotes(e.target.value)}
                                    className="w-full h-20 bg-slate-950 border border-slate-700 rounded-lg p-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
                                    placeholder="Log entry setup, mental state, SL execution..."
                                  />
                                ) : (
                                  <p className="text-slate-400 italic">
                                    {t.notes ? `"${t.notes}"` : 'No notes logged for this trade.'}
                                  </p>
                                )}
                              </div>
                              <div className="mt-2 pt-2 border-t border-slate-800 text-[11px] text-slate-400 flex justify-between">
                                <span>Planned SL: {t.planned_stop_loss ? `₹${t.planned_stop_loss}` : 'N/A'}</span>
                                <span>Planned Target: {t.planned_target ? `₹${t.planned_target}` : 'N/A'}</span>
                              </div>
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
