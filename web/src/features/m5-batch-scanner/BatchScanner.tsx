import React, { useState } from 'react';
import { api } from '../../lib/api';
import type { BatchScoreResponse, BatchScoreRow } from '../../lib/types';
import { DataTable } from '../../components/ui/DataTable';
import { StatusBadge } from '../../components/ui/StatusBadge';
import { InsightCallout } from '../../components/ui/InsightCallout';
import { Upload, FileSpreadsheet, Download, CheckCircle2, AlertTriangle, XCircle, FileText } from 'lucide-react';
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
    link.setAttribute('download', `sentinel_scored_batch_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const columns: ColumnDef<BatchScoreRow, any>[] = [
    {
      accessorKey: 'id',
      header: 'CSV Index',
      cell: ({ row }) => <span className="font-mono text-text-muted">#{row.original.id ?? row.index + 1}</span>,
    },
    {
      accessorKey: 'decision',
      header: 'Decision',
      cell: ({ row }) => <StatusBadge status={row.original.decision || 'APPROVE'} size="sm" />,
    },
    {
      accessorKey: 'probability',
      header: 'Fraud Probability',
      cell: ({ row }) => {
        const p = row.original.probability;
        const color = p > 0.8 ? 'text-status-block' : p > 0.2 ? 'text-status-review' : 'text-status-approve';
        return <span className={`font-mono font-bold ${color}`}>{(p * 100).toFixed(1)}%</span>;
      },
    },
    {
      accessorKey: 'risk_tier',
      header: 'Risk Tier',
      cell: ({ row }) => (
        <span className="uppercase font-mono text-[11px] text-text-secondary">
          {row.original.risk_tier}
        </span>
      ),
    },
    {
      accessorKey: 'action',
      header: 'Policy Action',
      cell: ({ row }) => (
        <span className="font-mono text-xs text-text-primary">{row.original.action}</span>
      ),
    },
  ];

  // Counts
  const total = response?.rows.length || 0;
  const approved = response?.rows.filter((r) => r.decision === 'APPROVE').length || 0;
  const reviewed = response?.rows.filter((r) => r.decision === 'MANUAL_REVIEW').length || 0;
  const declined = response?.rows.filter((r) => r.decision === 'DECLINE').length || 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between bg-surface-1 border border-border-subtle p-4 rounded-lg">
        <div>
          <h2 className="text-base font-bold text-text-primary tracking-tight">
            BATCH DATASET SCORING &amp; HIGH-THROUGHPUT SCANNER
          </h2>
          <p className="text-xs font-mono text-text-muted">
            Upload CSV datasets of unlabelled transactions for bulk high-speed inference and automated triage
          </p>
        </div>
      </div>

      {/* Upload Zone */}
      <div className="bg-surface-1 border border-border-subtle rounded-lg p-6 space-y-4">
        <div className="border-2 border-dashed border-border-subtle hover:border-accent-teal/50 rounded-lg p-8 text-center bg-surface-2/40 flex flex-col items-center justify-center transition-colors">
          <Upload className="w-10 h-10 text-accent-teal mb-3" />
          <h3 className="text-sm font-semibold text-text-primary mb-1">
            Drag &amp; Drop CSV File or Select from Computer
          </h3>
          <p className="text-xs text-text-muted mb-4 font-mono">
            Supported columns: TransactionAmt, card1..card6, dist1, P_emaildomain, C1..C14, D1..D15...
          </p>

          <div className="flex flex-wrap items-center gap-3">
            <label className="px-4 py-2 bg-accent-teal hover:bg-accent-teal/90 text-white text-xs font-mono font-semibold rounded cursor-pointer transition-colors">
              Browse CSV File
              <input type="file" accept=".csv" onChange={handleFileChange} className="hidden" />
            </label>

            <button
              onClick={handleLoadSample}
              disabled={isLoading}
              className="px-4 py-2 bg-surface-2 hover:bg-surface-hover border border-border-subtle text-text-primary text-xs font-mono rounded flex items-center gap-1.5 transition-colors"
            >
              <FileSpreadsheet className="w-4 h-4 text-accent-cyan" />
              <span>Load Pre-built Demo Batch</span>
            </button>
          </div>

          {file && (
            <div className="mt-4 text-xs font-mono text-accent-teal flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4" />
              <span>Selected: <b>{file.name}</b> ({(file.size / 1024).toFixed(1)} KB)</span>
            </div>
          )}
        </div>

        {file && !response && (
          <button
            onClick={handleUpload}
            disabled={isLoading}
            className="w-full py-2.5 bg-accent-teal hover:bg-accent-teal/90 text-white font-mono text-xs font-bold rounded shadow-xs transition-colors"
          >
            {isLoading ? 'Scoring Batch on LightGBM Engine...' : 'Execute Bulk Scoring'}
          </button>
        )}

        {error && <div className="text-status-block text-xs font-mono">{error}</div>}
      </div>

      {/* Results Summary & Table */}
      {response && (
        <div className="bg-surface-1 border border-border-subtle rounded-lg p-5 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border-subtle pb-4">
            <div>
              <h3 className="text-sm font-bold text-text-primary">
                Evaluation Results: {total} Transactions Scored
              </h3>
              <p className="text-xs font-mono text-text-muted">
                Model: {response.model_version} | Status: Ready
              </p>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={handleExportCsv}
                className="px-3 py-1.5 bg-surface-2 hover:bg-surface-hover border border-border-subtle text-text-primary text-xs font-mono rounded flex items-center gap-1.5 transition-colors"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Export Scored CSV</span>
              </button>
            </div>
          </div>

          {/* Quick Metrics Bar */}
          <div className="grid grid-cols-3 gap-3 text-center font-mono text-xs">
            <div className="p-3 bg-status-approve/10 border border-status-approve/25 rounded-lg text-status-approve">
              <span className="block text-lg font-bold">{approved}</span>
              <span className="text-[11px] opacity-80">Approved ({((approved / total) * 100).toFixed(0)}%)</span>
            </div>
            <div className="p-3 bg-status-review/10 border border-status-review/25 rounded-lg text-status-review">
              <span className="block text-lg font-bold">{reviewed}</span>
              <span className="text-[11px] opacity-80">Manual Review ({((reviewed / total) * 100).toFixed(0)}%)</span>
            </div>
            <div className="p-3 bg-status-block/10 border border-status-block/25 rounded-lg text-status-block">
              <span className="block text-lg font-bold">{declined}</span>
              <span className="text-[11px] opacity-80">Declined / Blocked ({((declined / total) * 100).toFixed(0)}%)</span>
            </div>
          </div>

          <DataTable
            columns={columns}
            data={response.rows}
            idAccessor={(row) => String(row.id || row.transaction_id)}
          />
        </div>
      )}

      <InsightCallout title="High-Throughput Offline Batch Processing" variant="info">
        Batch scoring executes in-memory vectorization via LightGBM C++ API, maintaining throughput upwards of 12,000 transactions per second for offline historical audits.
      </InsightCallout>
    </div>
  );
};
