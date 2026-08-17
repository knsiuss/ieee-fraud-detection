import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../lib/api';
import type { DecisionItem } from '../../lib/types';
import { useSelectedTxStore } from '../../stores/useSelectedTxStore';
import { StatusBadge } from '../../components/ui/StatusBadge';
import { AuditSampledBadge } from '../../components/ui/AuditSampledBadge';
import { ScoreBar } from '../../components/ui/ScoreBar';
import { DataTable } from '../../components/ui/DataTable';
import { InsightCallout } from '../../components/ui/InsightCallout';
import { Check, X, Clock, RefreshCw } from 'lucide-react';
import type { ColumnDef } from '@tanstack/react-table';

export const ReviewQueue: React.FC = () => {
  const queryClient = useQueryClient();
  const openDrawer = useSelectedTxStore((s) => s.openDrawer);
  const [selectedStatus, setSelectedStatus] = useState<string>('NEW');
  const [feedbackNote, setFeedbackNote] = useState<string>('');

  const { data: queue = [], refetch } = useQuery({
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
      header: 'Queue State',
      cell: ({ row }) => (
        <div className="flex items-center gap-1.5">
          <span className="px-1.5 py-0.5 rounded-[6px] bg-surface-2 border border-border-subtle text-[11px] font-mono font-medium">
            {row.original.status || 'NEW'}
          </span>
          {row.original.audit_sampled && <AuditSampledBadge />}
        </div>
      ),
    },
    {
      accessorKey: 'transaction_id',
      header: 'Transaction ID',
      cell: ({ row }) => (
        <span className="font-bold text-text-primary">
          #{row.original.transaction_id.slice(-8)}
        </span>
      ),
    },
    {
      accessorKey: 'score',
      header: 'Risk Probability Track',
      cell: ({ row }) => (
        <div className="w-48">
          <ScoreBar probability={row.original.score} compact={true} />
        </div>
      ),
    },
    {
      accessorKey: 'timestamp',
      header: 'Queued At (UTC)',
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
            className="btn-interactive px-2 py-0.5 bg-status-approve-soft text-status-approve border border-status-approve/30 rounded-[6px] text-[11px] font-mono font-semibold flex items-center gap-1"
          >
            <Check className="w-3 h-3" />
            <span>Approve (Safe)</span>
          </button>
          <button
            onClick={() => handleAction(row.original.transaction_id, 'fraud')}
            disabled={outcomeMutation.isPending}
            className="btn-interactive px-2 py-0.5 bg-status-block-soft text-status-block border border-status-block/30 rounded-[6px] text-[11px] font-mono font-semibold flex items-center gap-1"
          >
            <X className="w-3 h-3" />
            <span>Confirm Fraud</span>
          </button>
          <button
            onClick={() => openDrawer(row.original)}
            className="btn-interactive px-2 py-0.5 bg-surface-2 hover:bg-surface-hover border border-border-subtle text-text-secondary hover:text-text-primary rounded-[6px] text-[11px] font-mono"
          >
            Details
          </button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-4">
      {/* Header & SLA Badges */}
      <div className="flex flex-wrap items-center justify-between gap-3 panel p-3.5">
        <div>
          <h2 className="text-sm font-mono font-bold text-text-primary tracking-tight">
            MANUAL REVIEW &amp; CASE RESOLUTION QUEUE
          </h2>
          <p className="text-xs font-mono text-text-muted">
            Human-in-the-loop analyst triage ledger. Confirmed outcomes feed bandit policy rewards.
          </p>
        </div>

        <div className="flex items-center gap-2 font-mono text-xs">
          <div className="flex items-center gap-1.5 px-2.5 py-1 bg-surface-2 rounded-[6px] border border-border-subtle text-text-secondary">
            <Clock className="w-3 h-3 text-text-muted" />
            <span>SLA: &lt; 2 Hours</span>
          </div>
          <button
            onClick={() => refetch()}
            className="btn-interactive p-1 bg-surface-2 hover:bg-surface-hover rounded-[6px] border border-border-subtle text-text-secondary hover:text-text-primary"
            title="Refresh review queue"
            aria-label="Refresh review queue"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Queue Filter Bar */}
      <div className="flex items-center justify-between gap-3 panel p-3">
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono text-text-secondary">Filter Queue:</span>
          {['NEW', 'IN_PROGRESS', 'RESOLVED'].map((s) => (
            <button
              key={s}
              onClick={() => setSelectedStatus(s)}
              className={`btn-interactive px-2.5 py-1 rounded-[6px] text-xs font-mono border ${
                selectedStatus === s
                  ? 'bg-surface-hover text-text-primary border-border-muted font-bold'
                  : 'bg-surface-2 text-text-secondary border-border-subtle hover:bg-surface-hover'
              }`}
            >
              {s}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <input
            type="text"
            placeholder="Disposition note (optional)..."
            value={feedbackNote}
            onChange={(e) => setFeedbackNote(e.target.value)}
            className="bg-surface-2 border border-border-subtle text-text-primary text-xs font-mono px-2.5 py-1 rounded-[6px] w-64 placeholder:text-text-muted focus:outline-none"
          />
        </div>
      </div>

      {/* Queue Table */}
      <DataTable
        columns={columns}
        data={queue}
        onRowClick={(row) => openDrawer(row)}
        idAccessor={(row) => row.transaction_id}
        emptyMessage={`No cases currently in ${selectedStatus} status.`}
      />

      <InsightCallout title="Human-in-the-Loop Policy Feedback">
        Dispositions recorded here automatically emit reward signals to the LinUCB contextual bandit policy (`bandit_policy.py`) to reduce false positive friction over time.
      </InsightCallout>
    </div>
  );
};
