import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../lib/api';
import type { DecisionItem } from '../../lib/types';
import { useSelectedTxStore } from '../../stores/useSelectedTxStore';
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
        <div className="flex items-center gap-2">
          <span className="px-2.5 py-0.5 rounded-full bg-surface-2/90 border border-border-subtle text-xs font-sans font-semibold text-text-primary">
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
        <span className="font-bold font-mono text-text-primary text-xs">
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
        <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
          <button
            onClick={() => handleAction(row.original.transaction_id, 'safe')}
            disabled={outcomeMutation.isPending}
            className="btn-interactive px-3 py-1 bg-status-approve/12 text-status-approve border border-status-approve/30 rounded-full text-xs font-sans font-semibold flex items-center gap-1.5 shadow-xs hover:bg-status-approve/20 cursor-pointer"
          >
            <Check className="w-3.5 h-3.5" />
            <span>Approve (Safe)</span>
          </button>
          <button
            onClick={() => handleAction(row.original.transaction_id, 'fraud')}
            disabled={outcomeMutation.isPending}
            className="btn-interactive px-3 py-1 bg-status-block/12 text-status-block border border-status-block/30 rounded-full text-xs font-sans font-semibold flex items-center gap-1.5 shadow-xs hover:bg-status-block/20 cursor-pointer"
          >
            <X className="w-3.5 h-3.5" />
            <span>Confirm Fraud</span>
          </button>
          <button
            onClick={() => openDrawer(row.original)}
            className="btn-interactive px-3 py-1 bg-surface-2/90 hover:bg-surface-hover border border-border-subtle text-text-secondary hover:text-text-primary rounded-full text-xs font-sans font-medium shadow-xs cursor-pointer"
          >
            Details
          </button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-5">
      {/* Header & SLA Badges */}
      <div className="flex flex-wrap items-center justify-between gap-3 panel p-5 rounded-2xl">
        <div>
          <h2 className="text-sm font-sans font-bold text-text-primary tracking-tight uppercase">
            Manual Review &amp; Case Resolution Queue
          </h2>
          <p className="text-xs font-sans text-text-muted mt-0.5">
            Human-in-the-loop analyst triage ledger. Confirmed outcomes feed bandit policy rewards.
          </p>
        </div>

        <div className="flex items-center gap-2.5 font-sans text-xs">
          <div className="flex items-center gap-1.5 px-3 py-1.5 bg-surface-2/90 rounded-full border border-border-subtle text-text-secondary shadow-xs">
            <Clock className="w-3.5 h-3.5 text-apple-blue" />
            <span className="font-medium">SLA: &lt; 2 Hours</span>
          </div>
          <button
            onClick={() => refetch()}
            className="btn-interactive p-2 bg-surface-2/90 hover:bg-surface-hover rounded-full border border-border-subtle text-text-secondary hover:text-text-primary shadow-xs cursor-pointer"
            title="Refresh review queue"
            aria-label="Refresh review queue"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Queue Filter Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 panel p-4 rounded-2xl">
        <div className="flex items-center gap-1.5 bg-surface-2/80 p-1 rounded-full border border-border-subtle shadow-inner">
          {['NEW', 'IN_PROGRESS', 'RESOLVED'].map((s) => (
            <button
              key={s}
              onClick={() => setSelectedStatus(s)}
              className={`btn-interactive px-4 py-1 rounded-full text-xs font-sans transition-all ${
                selectedStatus === s
                  ? 'bg-surface-1 text-text-primary font-semibold shadow-sm border border-border-highlight scale-[1.02]'
                  : 'text-text-secondary hover:text-text-primary hover:bg-surface-hover/50 font-medium'
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
            className="bg-surface-2/90 border border-border-subtle text-text-primary text-xs font-sans px-3.5 py-1.5 rounded-full w-64 placeholder:text-text-muted focus:outline-none focus:border-border-highlight shadow-xs"
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
