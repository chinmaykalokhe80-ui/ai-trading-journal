'use client';

import React, { useState } from 'react';
import { uploadTradebookCSV } from '@/lib/api';
import { UploadCloud, FileText, CheckCircle2, AlertCircle, X, Loader2 } from 'lucide-react';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const TradeUploadModal: React.FC<Props> = ({ isOpen, onClose, onSuccess }) => {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError(null);
      setSuccessMsg(null);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a valid Zerodha Tradebook CSV file.');
      return;
    }

    setUploading(true);
    setError(null);

    try {
      const res = await uploadTradebookCSV(file);
      setSuccessMsg(`Successfully ingested ${res.trades_ingested} trade(s).`);
      setTimeout(() => {
        onSuccess();
        onClose();
      }, 1500);
    } catch (err: unknown) {
      setError((err instanceof Error ? err.message : '') || 'Failed to upload CSV file.');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-md p-4">
      <div className="bg-slate-900 border border-slate-800 w-full max-w-md rounded-2xl p-6 shadow-2xl relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-slate-400 hover:text-slate-200 p-1 rounded-lg hover:bg-slate-800"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-3 mb-4">
          <div className="p-2.5 bg-cyan-500/20 text-cyan-400 rounded-xl">
            <UploadCloud className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-slate-100">Upload Zerodha Tradebook CSV</h3>
            <p className="text-xs text-slate-400">Ingest executed trades and track P&L</p>
          </div>
        </div>

        <div className="mt-4">
          <label className="border-2 border-dashed border-slate-700 hover:border-cyan-500/60 transition-colors rounded-xl p-6 flex flex-col items-center justify-center cursor-pointer bg-slate-950/40">
            <FileText className="w-10 h-10 text-slate-500 mb-2" />
            <span className="text-xs text-slate-300 font-medium">
              {file ? file.name : 'Click to select or drag & drop Zerodha Console CSV'}
            </span>
            <span className="text-[10px] text-slate-500 mt-1">Supports Tradebook exports (.csv)</span>
            <input type="file" accept=".csv" onChange={handleFileChange} className="hidden" />
          </label>
        </div>

        {error && (
          <div className="mt-4 p-3 bg-rose-950/60 border border-rose-800/60 rounded-xl text-rose-300 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            {error}
          </div>
        )}

        {successMsg && (
          <div className="mt-4 p-3 bg-emerald-950/60 border border-emerald-800/60 rounded-xl text-emerald-300 text-xs flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            {successMsg}
          </div>
        )}

        <div className="mt-6 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-xs font-semibold text-slate-400 hover:text-slate-200 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleUpload}
            disabled={uploading || !file}
            className="px-5 py-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 disabled:opacity-50 text-white text-xs font-bold rounded-xl shadow-lg transition-all flex items-center gap-2"
          >
            {uploading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" /> Ingesting...
              </>
            ) : (
              'Ingest Tradebook'
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
