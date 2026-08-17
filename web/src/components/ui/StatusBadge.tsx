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

  let colorClasses = 'text-status-review bg-status-review-soft border-status-review/20';
  let label = status;

  if (norm === 'APPROVE' || norm === 'APPROVED') {
    colorClasses = 'text-status-approve bg-status-approve-soft border-status-approve/20';
    label = 'APPROVE';
  } else if (norm === 'DECLINE' || norm === 'DECLINED' || norm === 'BLOCKED') {
    colorClasses = 'text-status-block bg-status-block-soft border-status-block/20';
    label = 'DECLINE';
  } else if (norm === 'MANUAL_REVIEW' || norm === 'REVIEW') {
    colorClasses = 'text-status-review bg-status-review-soft border-status-review/20';
    label = 'REVIEW';
  } else if (norm === 'PENDING') {
    colorClasses = 'text-text-muted bg-surface-2 border-border-subtle';
    label = 'PENDING';
  }

  const sizeClasses =
    size === 'sm'
      ? 'px-1.5 py-0.5 text-[10px]'
      : size === 'lg'
      ? 'px-2.5 py-1 text-xs'
      : 'px-2 py-0.5 text-[11px]';

  return (
    <span
      className={`inline-flex items-center font-mono font-semibold rounded-full border ${sizeClasses} ${colorClasses} tracking-wider`}
    >
      {label}
    </span>
  );
};
