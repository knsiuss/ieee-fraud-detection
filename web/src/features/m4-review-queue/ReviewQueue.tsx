import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../lib/api';
import type { DecisionItem } from '../../lib/types';
import { useSelectedTxStore } from '../../stores/useSelectedTxStore';
import { StatusBadge } from '../../components/ui/StatusBadge';
import { DataTable } from '../../components/ui/DataTable';
import { InsightCallout } from '../../components/ui/InsightCallout';
import { Check, X, ShieldAlert, Clock, RefreshCw, AlertTriangle } from 'lucide-react';
import type { ColumnDef } from '@tanstack/react-table';

export const ReviewQueue: React.FC = () => {
  const queryClient = useQueryClient();
  const openDrawer = useSelectedTxStore((s) => s.openDrawer);
  const [selectedStatus, setSelectedStatus] = useState<string>('NEW');
  const [feedbackNote, setFeedbackNote] = useState<string>('');

  const { data: queue = [], isLoading, refetch } = useQuery({
    queryKey: ['review-queue', selectedStatus],
    queryFn: () => api.getReviewQueue(selectedStatus),
    refetchInterval: 10000,
  });

  const outcomeMutation = useMutation({
    mutationFn: ({ id, verdict, note }: { id: string; verdict: 'safe' | 'fraud'; note?: string }) =>
      api.submitReviewOutcome(id, verdict, note),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['review-queue'] });
      queryClient.invalidateQueries({ queryKey: ['metrics-summary'] });
      queryClient.invalidateQueries({ queryKey: ['metrics-dispositions'] });
    },
  });

  const handleAction = (id: string, verdict: 'safe' | 'fraud') => {
    outcomeMutation.mutate({ id, verdict, note: feedbackNote || `Analyst verdict: ${verdict}` });
  };

  const columns: ColumnDef<DecisionItem, any>[] = [
    {
      accessorKey: 'status',
      header: 'Queue Status',
      cell: ({ row }) => (
        <span className="px-2 py-0.5 rounded bg-surface-2 border border-border-subtle text-[11px] font-mono font-medium">
          {row.original.status || 'NEW'}
        </span>
      ),
    },
    {
      accessorKey: 'transaction_id',
      header: 'Transaction ID',
      cell: ({ row }) => (
        <span className="font-bold text-text-primary hover:text-accent-teal cursor-pointer">
          #{row.original.transaction_id.slice(-8)}
        </span>
      ),
    },
    {
      accessorKey: 'score',
      header: 'Fraud Probability',
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <span className="font-bold text-status-review">
            {(row.original.score * 100).toFixed(1)}%
          </span>
          <StatusBadge status={row.original.decision} size="sm" showIcon={false} />
        </div>
      ),
    },
    {
      accessorKey: 'timestamp',
      header: 'Queued At',
      cell: ({ row }) => {
        try {
          return new Date(row.original.timestamp).toLocaleString();
        } catch {
          return row.original.timestamp;
        }
      },
    },
    {
      id: 'actions',
      header: 'Analyst Disposition',
      cell: ({ row }) => (
        <div className="flex items-center gap-1.5" onClick={(e) => e.stopPropagation()}>
          <button
            onClick={() => handleAction(row.original.transaction_id, 'safe')}
            disabled={outcomeMutation.isPending}
            className="px-2.5 py-1 bg-status-approve/12 hover:bg-status-approve/25 border border-status-approve/30 text-status-approve rounded text-[11px] font-semibold flex items-center gap-1 transition-colors"
          >
            <Check className="w-3.5 h-3.5" />
            <span>Approve (Safe)</span>
          </button>
          <button
            onClick={() => handleAction(row.original.transaction_id, 'fraud')}
            disabled={outcomeMutation.isPending}
            className="px-2.5 py-1 bg-status-block/12 hover:bg-status-block/25 border border-status-block/30 text-status-block rounded text-[11px] font-semibold flex items-center gap-1 transition-colors"
          >
            <X className="w-3.5 h-3.5" />
            <span>Confirm Fraud</span>
          </button>
          <button
            onClick={() => openDrawer(row.original)}
            className="px-2 py-1 bg-surface-2 hover:bg-surface-hover border border-border-subtle text-text-muted hover:text-text-primary rounded text-[11px] transition-colors"
          >
            Details
          </button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header & SLA Badges */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-surface-1 border border-border-subtle p-4 rounded-lg">
        <div>
          <h2 className="text-base font-bold text-text-primary tracking-tight">
            MANUAL REVIEW &amp; CASE RESOLUTION QUEUE
          </h2>
          <p className="text-xs font-mono text-text-muted">
            Human-in-the-loop analyst triage queue. Outcomes automatically fold into the continuous retraining pool.
          </p>
        </div>

        <div className="flex items-center gap-2 font-mono text-xs">
          <div className="flex items-center gap-1.5 px-3 py-1.5 bg-surface-2 rounded-md border border-border-subtle">
            <Clock className="w-3.5 h-3.5 text-accent-teal" />
            <span>SLA Target: &lt; 2 Hours</span>
          </div>
          <button
            onClick={() => refetch()}
            className="p-1.5 bg-surface-2 hover:bg-surface-hover rounded-md border border-border-subtle text-text-secondary hover:text-text-primary transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Queue Filter Bar */}
      <div className="flex items-center justify-between gap-3 bg-surface-1 border border-border-subtle p-3 rounded-lg">
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono text-text-muted">Status:</span>
          {['NEW', 'REVIEWED', 'ALL'].map((st) => (
            <button
              key={st}
              onClick={() => setSelectedStatus(st)}
              className={`px-3 py-1 text-xs font-mono rounded border transition-colors ${
                selectedStatus === st
                  ? 'bg-accent-teal/15 text-accent-teal border-accent-teal/40 font-bold'
                  : 'bg-surface-2 text-text-secondary border-border-subtle hover:text-text-primary'
              }`}
            >
              {st}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <input
            type="text"
            placeholder="Optional disposition note (e.g. Cardholder verified via SMS)..."
            value={feedbackNote}
            onChange={(e) => setFeedbackNote(e.target.value)}
            className="bg-surface-2 border border-border-subtle text-text-primary text-xs font-mono px-3 py-1.5 rounded w-80 placeholder:text-text-muted focus:outline-none focus:border-accent-teal"
          />
        </div>
      </div>

      {/* Table List */}
      <div className="bg-surface-1 border border-border-subtle rounded-lg p-4 space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-text-primary">
            Active Review Cases ({queue.length})
          </h3>
          <span className="text-[11px] font-mono text-text-muted">
            Sorted by Risk Priority (Descending)
          </span>
        </div>

        <DataTable
          columns={columns}
          data={queue}
          onRowClick={(row) => openDrawer(row)}
          idAccessor={(row) => row.transaction_id}
          emptyMessage="Review queue is currently empty. No transactions require analyst intervention."
        />
      </div>

      <InsightCallout title="Feedback Loop Gating" variant="tip">
        Every reviewer outcome recorded here is cryptographically audited and automatically synced to{' '}
        <code className="text-accent-teal font-mono">data/feedback/feedback.jsonl</code>. During candidate model retraining, this ground truth is ingested into training folds while held-out validation stays pristine to guard against regression.
      </InsightCallout>
    </div>
  );
};
