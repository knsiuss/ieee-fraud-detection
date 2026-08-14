import React from 'react';
import type { DecisionType } from '../../lib/types';
import { CheckCircle2, AlertTriangle, XCircle, Clock } from 'lucide-react';

interface StatusBadgeProps {
  status: DecisionType | 'PENDING' | string;
  size?: 'sm' | 'md' | 'lg';
  showIcon?: boolean;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  size = 'md',
  showIcon = true,
}) => {
  const norm = status?.toUpperCase();

  let colorClasses = 'bg-status-review/10 text-status-review border-status-review/25';
  let Icon = AlertTriangle;
  let label = status;

  if (norm === 'APPROVE' || norm === 'APPROVED') {
    colorClasses = 'bg-status-approve/12 text-status-approve border-status-approve/25';
    Icon = CheckCircle2;
    label = 'APPROVED';
  } else if (norm === 'DECLINE' || norm === 'DECLINED' || norm === 'BLOCKED') {
    colorClasses = 'bg-status-block/12 text-status-block border-status-block/25';
    Icon = XCircle;
    label = 'DECLINED';
  } else if (norm === 'MANUAL_REVIEW' || norm === 'REVIEW') {
    colorClasses = 'bg-status-review/12 text-status-review border-status-review/25';
    Icon = AlertTriangle;
    label = 'REVIEW';
  } else if (norm === 'PENDING') {
    colorClasses = 'bg-text-muted/12 text-text-secondary border-text-muted/20';
    Icon = Clock;
    label = 'PENDING';
  }

  const sizeClasses =
    size === 'sm'
      ? 'px-1.5 py-0.5 text-[10px] gap-1'
      : size === 'lg'
      ? 'px-3 py-1.5 text-xs gap-1.5'
      : 'px-2.5 py-1 text-xs gap-1.5';

  return (
    <span
      className={`inline-flex items-center font-medium font-mono rounded border ${sizeClasses} ${colorClasses} tracking-wider`}
    >
      {showIcon && <Icon className={size === 'sm' ? 'w-3 h-3' : 'w-3.5 h-3.5'} />}
      <span>{label}</span>
    </span>
  );
};
