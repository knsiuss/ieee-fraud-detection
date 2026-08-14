import React from 'react';

export const Skeleton: React.FC<{ className?: string }> = ({ className = 'h-4 w-full' }) => (
  <div className={`animate-pulse bg-surface-2/80 rounded ${className}`} />
);

export const EmptyState: React.FC<{
  title: string;
  description?: string;
  action?: React.ReactNode;
  icon?: React.ReactNode;
}> = ({ title, description, action, icon }) => (
  <div className="py-12 px-4 text-center border border-dashed border-border-subtle rounded-lg bg-surface-1/50 flex flex-col items-center justify-center">
    {icon && <div className="text-text-muted mb-3">{icon}</div>}
    <h3 className="text-sm font-semibold text-text-primary mb-1">{title}</h3>
    {description && <p className="text-xs text-text-muted max-w-sm mb-4">{description}</p>}
    {action}
  </div>
);

export const ErrorState: React.FC<{
  message: string;
  onRetry?: () => void;
}> = ({ message, onRetry }) => (
  <div className="p-6 border border-status-block/30 rounded-lg bg-status-block/8 text-center flex flex-col items-center justify-center gap-3">
    <div className="text-status-block font-semibold text-sm">Failed to load data</div>
    <p className="text-xs text-text-secondary font-mono max-w-md">{message}</p>
    {onRetry && (
      <button
        onClick={onRetry}
        className="px-3 py-1.5 bg-surface-2 hover:bg-surface-hover text-text-primary text-xs font-mono rounded border border-border-subtle transition-colors"
      >
        Retry Request
      </button>
    )}
  </div>
);
