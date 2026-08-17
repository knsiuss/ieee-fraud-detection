import React, { useState } from 'react';
import { api } from '../../lib/api';
import type { BatchScoreResponse, BatchScoreRow } from '../../lib/types';
import { DataTable } from '../../components/ui/DataTable';
import { StatusBadge } from '../../components/ui/StatusBadge';
import { ScoreBar } from '../../components/ui/ScoreBar';
import { InsightCallout } from '../../components/ui/InsightCallout';
import { Upload, Download, FileText } from 'lucide-react';
import type { ColumnDef } from '@tanstack/react-table';

export const BatchScanner: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [response, setResponse] = useState<BatchScoreResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setIsLoading(true);
    setError(null);
    try {
      const res = await api.predictBatch(file);
      setResponse(res);
    } catch (err: any) {
      setError(err.message || 'Batch evaluation failed');
    } finally {
      setIsLoading(false);
    }
  };

  const handleLoadSample = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const sampleCsv = `TransactionID,TransactionDT,TransactionAmt,card1,card2,card3,card4,card6,addr1,dist1,P_emaildomain,C1,C2,D1,D2
1001,86400,45.0,6200,320,150,visa,debit,315,12.0,gmail.com,1,1,2,2
1002,86410,1420.0,15000,555,150,discover,credit,440,450.0,tempmail.org,8,12,0,0
1003,86420,89.5,10200,280,150,mastercard,credit,204,5.0,yahoo.com,1,1,14,14
1004,86430,2250.0,18500,410,150,discover,credit,181,890.0,anonymous.net,16,24,0,0
1005,86440,12.5,6200,111,150,visa,debit,315,2.0,gmail.com,1,1,30,30
1006,86450,550.0,10200,320,150,mastercard,debit,299,65.0,outlook.com,2,3,4,4`;

      const sampleFile = new File([sampleCsv], 'sample_ieee_transactions.csv', {
        type: 'text/csv',
      });
      setFile(sampleFile);
      const res = await api.predictBatch(sampleFile);
      setResponse(res);
    } catch (err: any) {
      setError(err.message || 'Sample evaluation failed');
    } finally {
      setIsLoading(false);
    }
  };

  const handleExportCsv = () => {
    if (!response || !response.rows) return;
    const headers = ['id', 'transaction_id', 'probability', 'risk_tier', 'decision', 'action'];
    const rows = response.rows.map((r) => [
      r.id ?? '',
      r.transaction_id ?? '',
      r.probability,
      r.risk_tier,
      r.decision ?? '',
      r.action ?? '',
    ]);

    const csvContent =
      'data:text/csv;charset=utf-8,' +
      [headers.join(','), ...rows.map((e) => e.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `ledger_batch_scored_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const columns: ColumnDef<BatchScoreRow, any>[] = [
    {
      accessorKey: 'id',
      header: 'Index',
      cell: ({ row }) => <span className="font-mono text-text-muted">#{row.original.id ?? row.index + 1}</span>,
    },
    {
      accessorKey: 'decision',
      header: 'Decision',
      cell: ({ row }) => <StatusBadge status={row.original.decision || 'APPROVE'} size="sm" />,
    },
    {
      accessorKey: 'probability',
      header: 'Risk Probability Track',
      cell: ({ row }) => (
        <div className="w-48">
          <ScoreBar probability={row.original.probability} compact={true} />
        </div>
      ),
    },
    {
      accessorKey: 'risk_tier',
      header: 'Tier',
      cell: ({ row }) => (
        <span className="uppercase font-sans font-semibold text-xs text-text-secondary px-2 py-0.5 rounded-full bg-surface-2">
          {row.original.risk_tier}
        </span>
      ),
    },
    {
      accessorKey: 'action',
      header: 'Policy Action',
      cell: ({ row }) => (
        <span className="font-sans text-xs text-text-primary font-medium">{row.original.action}</span>
      ),
    },
  ];

  // Counts
  const total = response?.rows.length || 0;
  const approved = response?.rows.filter((r) => r.decision === 'APPROVE').length || 0;
  const reviewed = response?.rows.filter((r) => r.decision === 'MANUAL_REVIEW').length || 0;
  const declined = response?.rows.filter((r) => r.decision === 'DECLINE').length || 0;

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between panel p-5 rounded-2xl">
        <div>
          <h2 className="text-sm font-sans font-bold text-text-primary tracking-tight uppercase">
            Batch Dataset Scoring &amp; Scanner
          </h2>
          <p className="text-xs font-sans text-text-muted mt-0.5">
            Upload CSV datasets of transactions for high-speed offline inference and triage
          </p>
        </div>
      </div>

      {/* Upload Box */}
      <div className="panel p-5 space-y-4 rounded-2xl">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <label className="btn-interactive inline-flex items-center gap-2 px-4 py-2 bg-surface-2/90 hover:bg-surface-hover border border-border-subtle rounded-full text-xs font-sans font-medium text-text-primary cursor-pointer shadow-xs">
              <Upload className="w-4 h-4 text-apple-blue" />
              <span>{file ? file.name : 'Select CSV File...'}</span>
              <input type="file" accept=".csv" onChange={handleFileChange} className="hidden" />
            </label>

            <button
              onClick={handleUpload}
              disabled={!file || isLoading}
              className="btn-interactive px-4 py-2 bg-apple-blue hover:bg-apple-blue/90 text-white rounded-full text-xs font-sans font-semibold disabled:opacity-50 shadow-sm cursor-pointer"
            >
              {isLoading ? 'Processing Batch...' : 'Execute Batch Score'}
            </button>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleLoadSample}
              disabled={isLoading}
              className="btn-interactive inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-surface-2/90 hover:bg-surface-hover border border-border-subtle rounded-full text-xs font-sans font-medium text-text-secondary hover:text-text-primary shadow-xs cursor-pointer"
            >
              <FileText className="w-3.5 h-3.5 text-text-muted" />
              <span>Load 6-Row Sample CSV</span>
            </button>

            {response && (
              <button
                onClick={handleExportCsv}
                className="btn-interactive inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-surface-2/90 hover:bg-surface-hover border border-border-subtle rounded-full text-xs font-sans font-semibold text-text-primary shadow-xs cursor-pointer"
              >
                <Download className="w-3.5 h-3.5 text-apple-indigo" />
                <span>Export Scored CSV</span>
              </button>
            )}
          </div>
        </div>

        {error && <div className="text-status-block text-xs font-sans font-medium">{error}</div>}
      </div>

      {/* Batch Summary Counters */}
      {response && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3.5 font-sans text-xs">
          <div className="panel p-4 rounded-2xl">
            <span className="text-text-muted uppercase text-[11px] font-semibold block">Total Processed</span>
            <span className="text-2xl font-bold font-mono text-text-primary tabular-nums mt-1">{total}</span>
          </div>
          <div className="panel p-4 rounded-2xl">
            <span className="text-text-muted uppercase text-[11px] font-semibold block">Auto-Approved</span>
            <span className="text-2xl font-bold font-mono text-status-approve tabular-nums mt-1">{approved}</span>
          </div>
          <div className="panel p-4 rounded-2xl">
            <span className="text-text-muted uppercase text-[11px] font-semibold block">Flagged for Review</span>
            <span className="text-2xl font-bold font-mono text-status-review tabular-nums mt-1">{reviewed}</span>
          </div>
          <div className="panel p-4 rounded-2xl">
            <span className="text-text-muted uppercase text-[11px] font-semibold block">Auto-Declined</span>
            <span className="text-2xl font-bold font-mono text-status-block tabular-nums mt-1">{declined}</span>
          </div>
        </div>
      )}

      {/* Batch Table */}
      {response && (
        <DataTable
          columns={columns}
          data={response.rows}
          emptyMessage="No rows evaluated in batch."
        />
      )}

      <InsightCallout title="High-Throughput Batch Inference">
        Batch requests run through LightGBM optimized matrix scoring with auto-imputation across all 400 IEEE-CIS features.
      </InsightCallout>
    </div>
  );
};
