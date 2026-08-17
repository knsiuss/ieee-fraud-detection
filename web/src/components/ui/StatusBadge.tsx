import React from 'react';
import type { DecisionType } from '../../lib/types';

interface StatusBadgeProps {
  status: DecisionType | 'PENDING' | string;
  size?: 'sm' | 'md' | 'lg';
  showIcon?: boolean;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  size = 'md',
}) => {
  const norm = status?.toUpperCase() || '';

  let colorClasses = 'text-status-review bg-status-review/12 border-status-review/30';
  let dotColor = 'bg-status-review';
  let label = status;

  if (norm === 'APPROVE' || norm === 'APPROVED') {
    colorClasses = 'text-status-approve bg-status-approve/12 border-status-approve/30';
    dotColor = 'bg-status-approve';
    label = 'APPROVE';
  } else if (norm === 'DECLINE' || norm === 'DECLINED' || norm === 'BLOCKED') {
    colorClasses = 'text-status-block bg-status-block/12 border-status-block/30';
    dotColor = 'bg-status-block';
    label = 'DECLINE';
  } else if (norm === 'MANUAL_REVIEW' || norm === 'REVIEW') {
    colorClasses = 'text-status-review bg-status-review/12 border-status-review/30';
    dotColor = 'bg-status-review';
    label = 'REVIEW';
  } else if (norm === 'PENDING') {
    colorClasses = 'text-text-muted bg-surface-2 border-border-subtle';
    dotColor = 'bg-text-muted';
    label = 'PENDING';
  }

  const sizeClasses =
    size === 'sm'
      ? 'px-2 py-0.5 text-[10px]'
      : size === 'lg'
      ? 'px-3 py-1 text-xs'
      : 'px-2.5 py-0.5 text-[11px]';

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-sans font-semibold rounded-full border shadow-xs ${sizeClasses} ${colorClasses} tracking-tight backdrop-blur-md`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${dotColor} shadow-sm`} />
      <span>{label}</span>
    </span>
  );
};
