import React from 'react';
import { Info } from 'lucide-react';

interface InsightCalloutProps {
  title?: string;
  children: React.ReactNode;
  variant?: 'info' | 'tip' | 'warning' | 'success';
}

export const InsightCallout: React.FC<InsightCalloutProps> = ({
  title = 'Analyst Note',
  children,
}) => {
  return (
    <div className="panel p-3 flex items-start gap-2.5 text-xs font-mono leading-relaxed bg-surface-1 text-text-primary">
      <Info className="w-3.5 h-3.5 shrink-0 mt-0.5 text-text-muted" />
      <div>
        {title && <span className="font-semibold text-text-primary mr-1.5">{title}:</span>}
        <span className="text-text-secondary">{children}</span>
      </div>
    </div>
  );
};
