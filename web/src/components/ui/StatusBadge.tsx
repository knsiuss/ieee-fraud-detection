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

  let colorClasses = 'text-status-review bg-status-review-soft border-status-review/25';
  let dotColor = 'bg-status-review';
  let label = status;

  if (norm === 'APPROVE' || norm === 'APPROVED') {
    colorClasses = 'text-status-approve bg-status-approve-soft border-status-approve/25';
    dotColor = 'bg-status-approve';
    label = 'APPROVE';
  } else if (norm === 'DECLINE' || norm === 'DECLINED' || norm === 'BLOCKED') {
    colorClasses = 'text-status-block bg-status-block-soft border-status-block/25';
    dotColor = 'bg-status-block';
    label = 'DECLINE';
  } else if (norm === 'MANUAL_REVIEW' || norm === 'REVIEW') {
    colorClasses = 'text-status-review bg-status-review-soft border-status-review/25';
    dotColor = 'bg-status-review';
    label = 'REVIEW';
  } else if (norm === 'PENDING') {
    colorClasses = 'text-text-muted bg-surface-2 border-border-subtle';
    dotColor = 'bg-text-muted';
    label = 'PENDING';
  }

  const sizeClasses =
    size === 'sm'
      ? 'px-1.5 py-0.5 text-[10px]'
      : size === 'lg'
      ? 'px-2.5 py-1 text-[11.5px]'
      : 'px-2 py-0.5 text-[10.5px]';

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-md border font-medium tracking-wide ${sizeClasses} ${colorClasses}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${dotColor}`} />
      <span>{label}</span>
    </span>
  );
};
