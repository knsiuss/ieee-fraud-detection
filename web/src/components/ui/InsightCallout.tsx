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
    <div className="panel p-4 flex items-start gap-3 text-xs font-sans leading-relaxed bg-surface-1/80 backdrop-blur-xl text-text-primary rounded-2xl shadow-sm border border-border-subtle">
      <Info className="w-4 h-4 shrink-0 mt-0.5 text-apple-blue" />
      <div>
        {title && <span className="font-semibold text-text-primary mr-1.5 font-sans">{title}:</span>}
        <span className="text-text-secondary">{children}</span>
      </div>
    </div>
  );
};
