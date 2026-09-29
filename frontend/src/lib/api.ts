const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

export interface Leg {
  leg_id: string;
  instrument: string;
  segment: 'Equity' | 'Futures' | 'CE' | 'PE' | string;
  side: 'buy' | 'sell';
  price: number;
  quantity: number;
  lot_size: number;
  order_id?: string;
  fill_time?: string;
  is_delivery?: boolean;
}

export interface Trade {
  id: string;
  strategy_id?: string | null;
  strategy_tag?: string | null;
  entry_time: string;
  exit_time?: string | null;
  emotion_tag: 'Neutral' | 'FOMO' | 'Revenge' | 'Confident' | 'Anxious' | 'Disciplined';
  notes?: string;
  planned_stop_loss?: number | null;
  planned_target?: number | null;
  screenshot_url?: string | null;
  status: 'open' | 'closed';
  gross_pnl: number;
  net_pnl: number;
  legs: Leg[];
}

export async function fetchTrades(filters?: { segment?: string; emotion_tag?: string; strategy_tag?: string }): Promise<Trade[]> {
  const params = new URLSearchParams();
  if (filters?.segment) params.append('segment', filters.segment);
  if (filters?.emotion_tag) params.append('emotion_tag', filters.emotion_tag);
  if (filters?.strategy_tag) params.append('strategy_tag', filters.strategy_tag);

  const res = await fetch(`${API_BASE_URL}/trades?${params.toString()}`);
  if (!res.ok) throw new Error('Failed to fetch trades');
  const data = await res.json();
  return data.trades || [];
}

export async function updateTrade(tradeId: string, payload: Partial<Trade>): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/trades/${tradeId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error('Failed to update trade');
}

export async function uploadTradebookCSV(file: File): Promise<{ trades_ingested: number }> {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE_URL}/ingest/csv`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Failed to upload CSV');
  }
  return res.json();
}

export async function createManualTrade(tradeData: {
  strategy_tag?: string;
  emotion_tag?: string;
  notes?: string;
  planned_stop_loss?: number;
  planned_target?: number;
  legs: {
    instrument: string;
    segment: string;
    side: 'buy' | 'sell';
    price: number;
    quantity: number;
    is_delivery?: boolean;
  }[];
}): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/trades`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(tradeData),
  });
  if (!res.ok) throw new Error('Failed to create manual trade');
}

export async function clearTrades(): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/trades`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error('Failed to clear trades');
}
