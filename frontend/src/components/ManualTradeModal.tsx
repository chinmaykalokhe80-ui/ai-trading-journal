'use client';

import React, { useState } from 'react';
import { createManualTrade } from '@/lib/api';
import { PlusCircle, Trash2, X, Loader2 } from 'lucide-react';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const ManualTradeModal: React.FC<Props> = ({ isOpen, onClose, onSuccess }) => {
  const [strategyTag, setStrategyTag] = useState('Breakout');
  const [emotionTag, setEmotionTag] = useState('Confident');
  const [notes, setNotes] = useState('');
  const [stopLoss, setStopLoss] = useState('');
  const [target, setTarget] = useState('');

  const [legs, setLegs] = useState<
    { instrument: string; segment: string; side: 'buy' | 'sell'; price: string; quantity: string; is_delivery: boolean }[]
  >([
    { instrument: 'NIFTY 24000 CE', segment: 'CE', side: 'buy', price: '120', quantity: '50', is_delivery: false },
    { instrument: 'NIFTY 24000 CE', segment: 'CE', side: 'sell', price: '180', quantity: '50', is_delivery: false },
  ]);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const addLeg = () => {
    setLegs([
      ...legs,
      { instrument: 'RELIANCE', segment: 'Equity', side: 'buy', price: '2500', quantity: '10', is_delivery: true },
    ]);
  };

  const removeLeg = (index: number) => {
    if (legs.length <= 1) return;
    setLegs(legs.filter((_, i) => i !== index));
  };

  const updateLeg = (index: number, field: string, value: string | boolean) => {
    const newLegs = [...legs];
    newLegs[index] = { ...newLegs[index], [field]: value };
    setLegs(newLegs);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const parsedLegs = legs.map((l) => ({
        instrument: l.instrument.trim(),
        segment: l.segment,
        side: l.side,
        price: Number(l.price),
        quantity: Number(l.quantity),
        is_delivery: l.is_delivery,
      }));

      await createManualTrade({
        strategy_tag: strategyTag,
        emotion_tag: emotionTag,
        notes,
        planned_stop_loss: stopLoss ? parseFloat(stopLoss) : undefined,
        planned_target: target ? parseFloat(target) : undefined,
        legs: parsedLegs,
      });

      onSuccess();
      onClose();
    } catch (err: unknown) {
      setError((err instanceof Error ? err.message : '') || 'Failed to record manual trade');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-md p-4">
      <div className="bg-slate-900 border border-slate-800 w-full max-w-2xl rounded-2xl p-6 shadow-2xl relative max-h-[90vh] overflow-y-auto">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-slate-400 hover:text-slate-200 p-1 rounded-lg hover:bg-slate-800"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-3 mb-6">
          <div className="p-2.5 bg-cyan-500/20 text-cyan-400 rounded-xl">
            <PlusCircle className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-slate-100">Manual Trade Entry</h3>
            <p className="text-xs text-slate-400">Log executions and track realized P&L</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1">Strategy Tag</label>
              <input
                type="text"
                value={strategyTag}
                onChange={(e) => setStrategyTag(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
                placeholder="e.g. Iron Condor"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1">Psychological Emotion</label>
              <select
                value={emotionTag}
                onChange={(e) => setEmotionTag(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
              >
                {['Neutral', 'FOMO', 'Revenge', 'Confident', 'Anxious', 'Disciplined'].map((opt) => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1">Planned SL / Target (₹)</label>
              <div className="flex gap-2">
                <input
                  type="number"
                  placeholder="SL"
                  value={stopLoss}
                  onChange={(e) => setStopLoss(e.target.value)}
                  className="w-1/2 bg-slate-950 border border-slate-700 rounded-xl px-2 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
                />
                <input
                  type="number"
                  placeholder="Target"
                  value={target}
                  onChange={(e) => setTarget(e.target.value)}
                  className="w-1/2 bg-slate-950 border border-slate-700 rounded-xl px-2 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
                />
              </div>
            </div>
          </div>

          <div>
            <label className="text-xs font-medium text-slate-300 block mb-1">Trade Notes / Setup Rationale</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full h-16 bg-slate-950 border border-slate-700 rounded-xl p-2.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
              placeholder="Key catalysts, level breakouts, risk management notes..."
            />
          </div>

          {/* Execution Legs */}
          <div className="pt-2">
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Execution Legs</h4>
              <button
                type="button"
                onClick={addLeg}
                className="text-xs text-cyan-400 hover:text-cyan-300 flex items-center gap-1 font-semibold"
              >
                + Add Leg
              </button>
            </div>

            <div className="space-y-2">
              {legs.map((leg, idx) => (
                <div key={idx} className="grid grid-cols-12 gap-2 items-center bg-slate-950/60 p-2.5 rounded-xl border border-slate-800">
                  <input
                    type="text"
                    placeholder="Instrument (e.g. RELIANCE)"
                    required
                    value={leg.instrument}
                    onChange={(e) => updateLeg(idx, 'instrument', e.target.value)}
                    className="col-span-4 bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
                  />
                  <select
                    value={leg.segment}
                    onChange={(e) => updateLeg(idx, 'segment', e.target.value)}
                    className="col-span-2 bg-slate-900 border border-slate-700 rounded-lg px-2 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
                  >
                    <option value="Equity">Equity</option>
                    <option value="CE">CE</option>
                    <option value="PE">PE</option>
                    <option value="Futures">Futures</option>
                  </select>
                  <select
                    value={leg.side}
                    onChange={(e) => updateLeg(idx, 'side', e.target.value)}
                    className="col-span-2 bg-slate-900 border border-slate-700 rounded-lg px-2 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
                  >
                    <option value="buy">BUY</option>
                    <option value="sell">SELL</option>
                  </select>
                  <input
                    type="number"
                    placeholder="Price"
                    min="0.01"
                    step="any"
                    required
                    value={leg.price}
                    onChange={(e) => updateLeg(idx, 'price', e.target.value)}
                    className="col-span-2 bg-slate-900 border border-slate-700 rounded-lg px-2 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
                  />
                  <input
                    type="number"
                    placeholder="Qty"
                    min="1"
                    step="1"
                    required
                    value={leg.quantity}
                    onChange={(e) => updateLeg(idx, 'quantity', e.target.value)}
                    className="col-span-1 bg-slate-900 border border-slate-700 rounded-lg px-1.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
                  />
                  <button
                    type="button"
                    onClick={() => removeLeg(idx)}
                    className="col-span-1 text-slate-500 hover:text-rose-400 flex justify-center p-1"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                  {leg.segment === 'Equity' && (
                    <label className="col-span-12 flex items-center gap-2 text-xs text-slate-400">
                      <input type="checkbox" checked={leg.is_delivery}
                        onChange={(e) => updateLeg(idx, 'is_delivery', e.target.checked)} />
                      Delivery trade (uncheck for intraday)
                    </label>
                  )}
                </div>
              ))}
            </div>
          </div>

          {error && <div className="p-3 bg-rose-950/60 border border-rose-800 text-rose-300 text-xs rounded-xl">{error}</div>}

          <div className="pt-4 flex justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-semibold text-slate-400 hover:text-slate-200"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-5 py-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-xs font-bold rounded-xl shadow-lg transition-all flex items-center gap-2"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Log Trade'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
