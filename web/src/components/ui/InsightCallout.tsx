import React from 'react';
import { Lightbulb, Info, AlertOctagon, CheckCircle } from 'lucide-react';

interface InsightCalloutProps {
  title?: string;
  children: React.ReactNode;
  variant?: 'info' | 'tip' | 'warning' | 'success';
}

export const InsightCallout: React.FC<InsightCalloutProps> = ({
  title = 'Analyst Insight',
  children,
  variant = 'info',
}) => {
  const styles = {
    info: {
      bg: 'bg-surface-2 border-border-subtle text-text-primary',
      icon: Info,
      iconColor: 'text-accent-sky',
    },
    tip: {
      bg: 'bg-accent-teal/8 border-accent-teal/20 text-text-primary',
      icon: Lightbulb,
      iconColor: 'text-accent-teal',
    },
    warning: {
      bg: 'bg-status-review/8 border-status-review/20 text-text-primary',
      icon: AlertOctagon,
      iconColor: 'text-status-review',
    },
    success: {
      bg: 'bg-status-approve/8 border-status-approve/20 text-text-primary',
      icon: CheckCircle,
      iconColor: 'text-status-approve',
    },
  };

  const { bg, icon: Icon, iconColor } = styles[variant];

  return (
    <div className={`border rounded-lg p-3.5 flex items-start gap-3 text-xs leading-relaxed ${bg}`}>
      <Icon className={`w-4 h-4 shrink-0 mt-0.5 ${iconColor}`} />
      <div>
        {title && <span className="font-semibold block mb-0.5">{title}: </span>}
        <div className="text-text-secondary">{children}</div>
      </div>
    </div>
  );
};
