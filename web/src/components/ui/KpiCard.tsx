import React from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface KpiCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: {
    value: string | number;
    direction: 'up' | 'down' | 'neutral';
    label?: string;
  };
  accent?: 'teal' | 'cyan' | 'emerald' | 'amber' | 'crimson';
  icon?: React.ReactNode;
  pulse?: boolean;
}

export const KpiCard: React.FC<KpiCardProps> = ({
  title,
  value,
  subtitle,
  trend,
  icon,
}) => {
  return (
    <div className="panel panel-hover p-5 flex flex-col justify-between rounded-2xl relative overflow-hidden group">
      {/* Subtle Apple Ambient Glow on hover */}
      <div className="absolute top-0 right-0 w-24 h-24 bg-apple-blue/5 rounded-full blur-2xl pointer-events-none group-hover:bg-apple-blue/10 transition-all duration-300" />

      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-semibold uppercase tracking-wider text-text-secondary font-sans">
          {title}
        </span>
        {icon && (
          <span className="w-8 h-8 rounded-2xl bg-surface-2/80 flex items-center justify-center text-text-secondary shrink-0 border border-border-subtle shadow-sm group-hover:scale-105 transition-transform">
            {icon}
          </span>
        )}
      </div>

      <div className="mt-3.5 flex items-baseline justify-between gap-2">
        <span className="text-3xl font-bold font-mono tracking-tight text-text-primary tabular-nums leading-none">
          {value}
        </span>

        {trend && (
          <div
            className={`inline-flex items-center gap-1 text-[11px] font-sans font-semibold px-2.5 py-1 rounded-full border shadow-xs ${
              trend.direction === 'up'
                ? 'text-status-approve bg-status-approve/10 border-status-approve/25'
                : trend.direction === 'down'
                ? 'text-status-block bg-status-block/10 border-status-block/25'
                : 'text-text-muted bg-surface-2 border-border-subtle'
            }`}
          >
            {trend.direction === 'up' && <TrendingUp className="w-3 h-3" />}
            {trend.direction === 'down' && <TrendingDown className="w-3 h-3" />}
            {trend.direction === 'neutral' && <Minus className="w-3 h-3" />}
            <span>{trend.value}</span>
          </div>
        )}
      </div>

      {(subtitle || trend?.label) && (
        <div className="mt-2 text-xs font-normal text-text-muted truncate font-sans">
          {subtitle || trend?.label}
        </div>
      )}
    </div>
  );
};
