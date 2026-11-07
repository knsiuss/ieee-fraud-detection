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

  const [isInjecting, setIsInjecting] = useState(false);

  const { data: queue = [], refetch } = useQuery({
    queryKey: ['review-queue', selectedStatus],
    queryFn: () => api.getReviewQueue(selectedStatus, 100, 'MANUAL_REVIEW'),
    refetchInterval: 10000,
  });

  const oldestWaitMin = (() => {
    const times = queue
      .map((d) => Date.parse(d.timestamp))
      .filter((t) => Number.isFinite(t));
    if (times.length === 0) return null;
    return Math.max(0, Math.round((Date.now() - Math.min(...times)) / 60000));
  })();

  const handleInjectSample = async () => {
    setIsInjecting(true);
    try {
      await api.simulate({
        profile: 'fraud',
        amount: 2450.0,
        card_brand: 'discover',
        billing_distance: 4800.0,
        card_match_count: 15,
        purchase_frequency: 35,
        days_since_activity: 0,
      });
      await refetch();
      queryClient.invalidateQueries({ queryKey: ['metrics-summary'] });
    } catch {
      // ignore
    } finally {
      setIsInjecting(false);
    }
  };

  const outcomeMutation = useMutation({
    mutationFn: ({ id, verdict, note }: { id: string; verdict: 'safe' | 'fraud'; note?: string }) =>
      api.submitReviewOutcome(id, verdict, note),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['review-queue'] });
      queryClient.invalidateQueries({ queryKey: ['metrics-summary'] });
      queryClient.invalidateQueries({ queryKey: ['metrics-dispositions'] });
      setOutcomeError(null);
    },
  });
  const [outcomeError, setOutcomeError] = useState<string | null>(null);

  const handleAction = (id: string, verdict: 'safe' | 'fraud') => {
    outcomeMutation.mutate(
      { id, verdict, note: feedbackNote || `Analyst verdict: ${verdict}` },
      { onError: (err: any) => setOutcomeError(err?.message || 'Submission failed') }
    );
  };

  const columns: ColumnDef<DecisionItem, any>[] = [
    {
      accessorKey: 'status',
      header: 'Queue State',
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <span className="px-2.5 py-0.5 rounded-full bg-surface-2 border border-border-subtle text-xs font-sans font-semibold text-text-primary">
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
        const d = new Date(row.original.timestamp);
        return Number.isNaN(d.getTime())
          ? row.original.timestamp
          : d.toLocaleString('en-GB', { timeZone: 'UTC', hour12: false });
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
            className="btn-interactive px-3 py-1 bg-status-approve/12 text-status-approve border border-status-approve/30 rounded-full text-xs font-sans font-semibold flex items-center gap-1.5 hover:bg-status-approve/20 cursor-pointer"
          >
            <Check className="w-3.5 h-3.5" />
            <span>Approve (Safe)</span>
          </button>
          <button
            onClick={() => handleAction(row.original.transaction_id, 'fraud')}
            disabled={outcomeMutation.isPending}
            className="btn-interactive px-3 py-1 bg-status-block/12 text-status-block border border-status-block/30 rounded-full text-xs font-sans font-semibold flex items-center gap-1.5 hover:bg-status-block/20 cursor-pointer"
          >
            <X className="w-3.5 h-3.5" />
            <span>Confirm Fraud</span>
          </button>
          <button
            onClick={() => openDrawer(row.original)}
            className="btn-interactive px-3 py-1 bg-surface-2 hover:bg-surface-hover border border-border-subtle text-text-secondary hover:text-text-primary rounded-full text-xs font-sans font-medium cursor-pointer"
          >
            Details
          </button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-5">
      {outcomeError && (
        <div className="panel p-4 rounded-xl border border-status-decline/30 text-sm text-status-decline">
          Submission failed: {outcomeError}
        </div>
      )}
      {/* Header & SLA Badges */}
      <div className="flex flex-wrap items-center justify-between gap-3 panel p-5 rounded-xl">
        <div>
          <h2 className="text-[15px] font-semibold tracking-tight text-text-primary">
            Manual Review &amp; Case Resolution Queue
          </h2>
          <p className="text-xs font-sans text-text-muted mt-0.5">
            Human-in-the-loop analyst triage ledger. Confirmed outcomes emit reward signals for the
            adaptive policy layer.
          </p>
        </div>

        <div className="flex items-center gap-2.5 font-sans text-xs">
          <div className="flex items-center gap-1.5 rounded-full border border-border-subtle bg-surface-2 px-3 py-1.5 text-text-secondary">
            <Clock className="w-3.5 h-3.5 text-apple-blue" />
            <span className="font-medium">
              {oldestWaitMin != null ? `Oldest open case: ${oldestWaitMin}m` : 'No open cases'}
            </span>
          </div>
          <button
            onClick={handleInjectSample}
            disabled={isInjecting}
            className="btn-interactive px-3 py-1.5 bg-apple-blue/15 hover:bg-apple-blue/25 text-apple-blue border border-apple-blue/30 rounded-full font-semibold cursor-pointer flex items-center gap-1"
            title="Inject a simulated high-risk transaction into the review queue"
          >
            <span>{isInjecting ? 'Injecting...' : '+ Test Review Case'}</span>
          </button>
          <button
            onClick={() => refetch()}
            className="btn-interactive p-2 bg-surface-2 hover:bg-surface-hover rounded-full border border-border-subtle text-text-secondary hover:text-text-primary cursor-pointer"
            title="Refresh review queue"
            aria-label="Refresh review queue"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Queue Filter Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 panel p-4 rounded-xl">
        <div className="flex items-center gap-1.5 bg-surface-2 p-1 rounded-full border border-border-subtle">
          {['NEW', 'IN_PROGRESS', 'RESOLVED'].map((s) => (
            <button
              key={s}
              onClick={() => setSelectedStatus(s)}
              className={`btn-interactive px-4 py-1 rounded-full text-xs font-sans transition-all ${
                selectedStatus === s
                  ? 'bg-surface-1 text-text-primary font-semibold border border-border-highlight scale-[1.02]'
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
            className="bg-surface-2 border border-border-subtle text-text-primary text-xs font-sans px-3.5 py-1.5 rounded-full w-64 placeholder:text-text-muted focus:outline-none focus:border-border-highlight"
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
        Dispositions recorded here emit reward signals consumed by the adaptive policy layer
        (`bandit_policy.py`) when it is enabled, to reduce false-positive friction over time.
      </InsightCallout>
    </div>
  );
};
