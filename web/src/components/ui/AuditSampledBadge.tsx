import React from 'react';
import { Scale } from 'lucide-react';

interface AuditSampledBadgeProps {
  className?: string;
}

export const AuditSampledBadge: React.FC<AuditSampledBadgeProps> = ({ className = '' }) => {
  return (
    <span
      className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded-[2px] bg-surface-2 border border-border-subtle text-text-secondary text-[10px] font-mono font-medium ${className}`}
      title="Bias-check random audit sample on auto-actioned policy"
    >
      <Scale className="w-3 h-3 text-text-muted" />
      <span>Audit sample</span>
    </span>
  );
};
