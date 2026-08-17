import React from 'react';

export const Skeleton: React.FC<{ className?: string }> = ({ className = 'h-4 w-full' }) => (
  <div className={`animate-pulse bg-surface-2 rounded-[6px] ${className}`} />
);

export const EmptyState: React.FC<{
  title: string;
  description?: string;
  action?: React.ReactNode;
  icon?: React.ReactNode;
}> = ({ title, description, action, icon }) => (
  <div className="py-10 px-4 text-center panel border-dashed flex flex-col items-center justify-center">
    {icon && <div className="text-text-muted mb-2">{icon}</div>}
    <h3 className="text-xs font-mono font-semibold text-text-primary mb-1">{title}</h3>
    {description && <p className="text-[11px] font-mono text-text-muted max-w-sm mb-3">{description}</p>}
    {action}
  </div>
);

export const ErrorState: React.FC<{
  message: string;
  onRetry?: () => void;
}> = ({ message, onRetry }) => (
  <div className="p-4 border border-status-block/30 rounded-[6px] bg-status-block-soft text-center flex flex-col items-center justify-center gap-2">
    <div className="text-status-block font-mono font-semibold text-xs">Failed to load data</div>
    <p className="text-[11px] text-text-secondary font-mono max-w-md">{message}</p>
    {onRetry && (
      <button
        onClick={onRetry}
        className="btn-interactive px-2.5 py-1 bg-surface-2 hover:bg-surface-hover text-text-primary text-xs font-mono rounded-[6px] border border-border-subtle"
      >
        Retry Request
      </button>
    )}
  </div>
);
