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
    <div className="panel flex items-start gap-3 border-l-2 border-l-apple-blue px-4 py-3">
      <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-apple-blue" />
      <div className="text-[12px] leading-relaxed">
        {title && <span className="mr-1.5 font-semibold text-text-primary">{title}:</span>}
        <span className="text-text-secondary">{children}</span>
      </div>
    </div>
  );
};
