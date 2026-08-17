import React from 'react';

export const Skeleton: React.FC<{ className?: string }> = ({ className = 'h-4 w-full' }) => (
  <div className={`animate-pulse bg-surface-2/90 rounded-xl ${className}`} />
);

export const EmptyState: React.FC<{
  title: string;
  description?: string;
  action?: React.ReactNode;
  icon?: React.ReactNode;
}> = ({ title, description, action, icon }) => (
  <div className="py-12 px-6 text-center panel rounded-2xl border-dashed flex flex-col items-center justify-center">
    {icon && <div className="text-text-muted mb-3">{icon}</div>}
    <h3 className="text-sm font-sans font-semibold text-text-primary mb-1">{title}</h3>
    {description && <p className="text-xs font-sans text-text-muted max-w-sm mb-4 leading-relaxed">{description}</p>}
    {action}
  </div>
);

export const ErrorState: React.FC<{
  message: string;
  onRetry?: () => void;
}> = ({ message, onRetry }) => (
  <div className="p-6 border border-status-block/30 rounded-2xl bg-status-block/10 text-center flex flex-col items-center justify-center gap-3 backdrop-blur-md">
    <div className="text-status-block font-sans font-semibold text-sm">Failed to load data</div>
    <p className="text-xs text-text-secondary font-mono max-w-md">{message}</p>
    {onRetry && (
      <button
        onClick={onRetry}
        className="btn-interactive px-4 py-1.5 bg-surface-2 hover:bg-surface-hover text-text-primary text-xs font-sans font-semibold rounded-full border border-border-subtle shadow-sm"
      >
        Retry Request
      </button>
    )}
  </div>
);
