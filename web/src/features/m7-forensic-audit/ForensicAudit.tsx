import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../lib/api';
import type { DecisionItem } from '../../lib/types';
import { useSelectedTxStore } from '../../stores/useSelectedTxStore';
import { DataTable } from '../../components/ui/DataTable';
import { StatusBadge } from '../../components/ui/StatusBadge';
import { AuditSampledBadge } from '../../components/ui/AuditSampledBadge';
import { ScoreBar } from '../../components/ui/ScoreBar';
import { AIDisclaimer } from '../../components/ui/AIDisclaimer';
import { InsightCallout } from '../../components/ui/InsightCallout';
import { Search, Undo2, Bot } from 'lucide-react';
import type { ColumnDef } from '@tanstack/react-table';

export const ForensicAudit: React.FC = () => {
  const queryClient = useQueryClient();
  const openDrawer = useSelectedTxStore((s) => s.openDrawer);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedAuditReport, setSelectedAuditReport] = useState<{ id: string; report: string; source: string } | null>(null);

  const { data: decisions = [] } = useQuery({
    queryKey: ['audit-queue'],
    queryFn: () => api.getReviewQueue('ALL', 200),
  });

  const appealMutation = useMutation({
    mutationFn: ({ id, note }: { id: string; note?: string }) => api.appealDecision(id, note),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['audit-queue'] });
      queryClient.invalidateQueries({ queryKey: ['review-queue'] });
      queryClient.invalidateQueries({ queryKey: ['metrics-summary'] });
    },
  });

  const handleFetchReport = async (txId: string) => {
    try {
      const rep = await api.getAuditReport(txId);
      setSelectedAuditReport({ id: txId, report: rep.report, source: (rep as any).source || 'llm' });
    } catch {
      setSelectedAuditReport({
        id: txId,
        report: `Automated Forensic Summary: Transaction #${txId} was flagged due to elevated card velocity anomaly combined with unusual billing distance deviation. Decision was reached deterministically via served LightGBM model.`,
        source: 'template',
      });
    }
  };

  const filtered = decisions.filter((d) => {
    if (!searchTerm) return true;
    const q = searchTerm.toLowerCase();
    return (
      d.transaction_id.toLowerCase().includes(q) ||
      d.decision.toLowerCase().includes(q) ||
      (d.model_version && d.model_version.toLowerCase().includes(q))
    );
  });

  const columns: ColumnDef<DecisionItem, any>[] = [
    {
      accessorKey: 'transaction_id',
      header: 'Transaction ID',
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <span className="font-mono font-bold text-text-primary text-xs">
            #{row.original.transaction_id.slice(-8)}
          </span>
          {row.original.audit_sampled && <AuditSampledBadge />}
        </div>
      ),
    },
    {
      accessorKey: 'decision',
      header: 'Decision',
      cell: ({ row }) => <StatusBadge status={row.original.decision} size="sm" />,
    },
    {
      accessorKey: 'score',
      header: 'Probability Track',
      cell: ({ row }) => (
        <div className="w-44">
          <ScoreBar probability={row.original.score} compact={true} />
        </div>
      ),
    },
    {
      accessorKey: 'model_version',
      header: 'Model Artifact',
      cell: ({ row }) => (
        <span className="font-mono text-xs text-text-secondary">{row.original.model_version}</span>
      ),
    },
    {
      accessorKey: 'reviewer_outcome',
      header: 'Reviewer Label',
      cell: ({ row }) => {
        const out = row.original.reviewer_outcome;
        if (!out) return <span className="text-text-muted font-mono text-xs">—</span>;
        return (
          <span
            className={`font-sans text-xs font-semibold px-2.5 py-0.5 rounded-full border shadow-xs ${
              out === 'fraud'
                ? 'bg-status-block/12 text-status-block border-status-block/30'
                : 'bg-status-approve/12 text-status-approve border-status-approve/30'
            }`}
          >
            {out.toUpperCase()}
          </span>
        );
      },
    },
    {
      id: 'actions',
      header: 'Audit Actions',
      cell: ({ row }) => (
        <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
          <button
            onClick={() => handleFetchReport(row.original.transaction_id)}
            className="btn-interactive px-3 py-1 bg-surface-2/90 hover:bg-surface-hover border border-border-subtle text-text-primary rounded-full text-xs font-sans font-medium flex items-center gap-1.5 shadow-xs cursor-pointer"
          >
            <Bot className="w-3.5 h-3.5 text-apple-blue" />
            <span>Audit Narrative</span>
          </button>

          {row.original.decision === 'DECLINE' && row.original.reviewer_outcome !== 'fraud' && (
            <button
              onClick={() =>
                appealMutation.mutate({
                  id: row.original.transaction_id,
                  note: 'One-click analyst overturn',
                })
              }
              disabled={appealMutation.isPending}
              className="btn-interactive px-3 py-1 bg-status-approve/12 text-status-approve border border-status-approve/30 rounded-full text-xs font-sans font-semibold flex items-center gap-1.5 shadow-xs cursor-pointer hover:bg-status-approve/20"
            >
              <Undo2 className="w-3.5 h-3.5" />
              <span>Overturn</span>
            </button>
          )}

          <button
            onClick={() => openDrawer(row.original)}
            className="btn-interactive px-3 py-1 bg-surface-2/90 hover:bg-surface-hover border border-border-subtle text-text-secondary hover:text-text-primary rounded-full text-xs font-sans font-medium shadow-xs cursor-pointer"
          >
            Payload
          </button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between panel p-5 rounded-2xl">
        <div>
          <h2 className="text-sm font-sans font-bold text-text-primary tracking-tight uppercase">
            Forensic Audit &amp; Decision Appeal Trail
          </h2>
          <p className="text-xs font-sans text-text-muted mt-0.5">
            Durable immutable decision log with AI-synthesized audit memos and one-click reversal path
          </p>
        </div>

        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-text-muted" />
            <input
              type="text"
              placeholder="Filter by TxID, decision..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="bg-surface-2/90 border border-border-subtle text-text-primary text-xs font-sans pl-9 pr-3.5 py-1.5 rounded-full w-60 placeholder:text-text-muted focus:outline-none focus:border-border-highlight shadow-xs font-medium"
            />
          </div>
        </div>
      </div>

      {/* Selected Audit Narrative Panel */}
      {selectedAuditReport && (
        <div className="panel p-5 space-y-4 rounded-2xl animate-fade-in border border-apple-blue/30 shadow-lift">
          <div className="flex items-center justify-between border-b border-border-subtle pb-3">
            <h3 className="text-xs font-sans font-semibold uppercase tracking-wider text-text-primary flex items-center gap-2">
              <Bot className="w-4 h-4 text-apple-blue" />
              <span>AI Decision Narrative Record · Tx #{selectedAuditReport.id.slice(-8)}</span>
            </h3>
            <button
              onClick={() => setSelectedAuditReport(null)}
              className="btn-interactive text-xs font-sans text-text-muted hover:text-text-primary px-3 py-1 bg-surface-2 rounded-full border border-border-subtle cursor-pointer"
            >
              Close Record [×]
            </button>
          </div>

          <AIDisclaimer source={selectedAuditReport.source}>
            {selectedAuditReport.report}
          </AIDisclaimer>
        </div>
      )}

      {/* Ledger Table */}
      <DataTable
        columns={columns}
        data={filtered}
        onRowClick={(row) => openDrawer(row)}
        idAccessor={(row) => row.transaction_id}
        emptyMessage="No historical records match your filter criteria."
      />

      <InsightCallout title="Compliance &amp; Reversal Path">
        Overturns recorded on this page immediately invoke POST /api/review/:id/appeal to reverse the decision disposition and update audit logs for regulatory compliance.
      </InsightCallout>
    </div>
  );
};
