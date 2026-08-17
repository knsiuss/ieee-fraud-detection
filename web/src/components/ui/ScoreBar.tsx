import React from 'react';

export interface ScoreBarDriver {
  label: string;
  direction: 'fraud' | 'safe';
}

export interface ScoreBarThresholds {
  review_above?: number;
  decline_above?: number;
  auto_action_above?: number;
}

interface ScoreBarProps {
  probability: number; // 0.0 to 1.0
  topDriver?: ScoreBarDriver;
  thresholds?: ScoreBarThresholds;
  compact?: boolean;
  showPercentage?: boolean;
  className?: string;
}

export const ScoreBar: React.FC<ScoreBarProps> = ({
  probability,
  topDriver,
  thresholds = { review_above: 0.2, decline_above: 0.8 },
  compact = false,
  showPercentage = false,
  className = '',
}) => {
  const clampProb = Math.max(0, Math.min(1, probability));
  const pct = (clampProb * 100).toFixed(1);
  const rawNum = clampProb.toFixed(3);

  const revThresh = thresholds.review_above ?? 0.2;
  const decThresh = thresholds.decline_above ?? 0.8;

  // Decision zone color
  let barGradient = 'from-status-approve to-emerald-400';
  let textColor = 'text-status-approve';
  if (clampProb >= decThresh) {
    barGradient = 'from-status-block to-rose-500';
    textColor = 'text-status-block';
  } else if (clampProb >= revThresh) {
    barGradient = 'from-status-review to-amber-400';
    textColor = 'text-status-review';
  }

  return (
    <div className={`flex flex-col gap-1.5 font-sans ${className}`}>
      {/* Sleek Pill Track & Markers */}
      <div className="relative w-full bg-surface-2/90 h-2 rounded-full overflow-hidden p-0.5 border border-border-subtle shadow-inner">
        {/* Threshold Markers */}
        <div
          className="absolute top-0 bottom-0 w-[1px] bg-border-highlight z-10"
          style={{ left: `${revThresh * 100}%` }}
          title={`Review threshold: ${revThresh}`}
        />
        <div
          className="absolute top-0 bottom-0 w-[1px] bg-border-highlight z-10"
          style={{ left: `${decThresh * 100}%` }}
          title={`Decline threshold: ${decThresh}`}
        />

        {/* Filled Score Bar Pill */}
        <div
          className={`h-full rounded-full bg-gradient-to-r ${barGradient} transition-all duration-300 shadow-sm`}
          style={{ width: `${Math.max(clampProb * 100, 2)}%` }}
        />
      </div>

      {/* Numerics + Driver Inline */}
      <div className="flex items-center justify-between text-xs leading-none pt-0.5">
        <div className="flex items-center gap-1.5 font-mono">
          <span className={`font-bold tabular-nums tracking-tight ${textColor}`}>
            {showPercentage ? `${pct}%` : rawNum}
          </span>

          {topDriver && (
            <span className="text-text-secondary text-[11px] font-sans truncate flex items-center gap-0.5">
              <span>· {topDriver.label}</span>
              <span className={topDriver.direction === 'fraud' ? 'text-status-block font-bold' : 'text-status-approve font-bold'}>
                {topDriver.direction === 'fraud' ? '↑' : '↓'}
              </span>
            </span>
          )}
        </div>

        {!compact && (
          <span className="text-[10px] font-sans font-semibold tracking-wider uppercase text-text-muted">
            {clampProb >= decThresh ? 'DECLINE' : clampProb >= revThresh ? 'REVIEW' : 'APPROVE'}
          </span>
        )}
      </div>
    </div>
  );
};
