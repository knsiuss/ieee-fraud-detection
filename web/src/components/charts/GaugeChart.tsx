import React from 'react';
import { ScoreBar, type ScoreBarDriver, type ScoreBarThresholds } from '../ui/ScoreBar';

interface GaugeChartProps {
  score: number; // 0.0 to 1.0
  title?: string;
  topDriver?: ScoreBarDriver;
  thresholds?: ScoreBarThresholds;
  height?: string | number;
}

export const GaugeChart: React.FC<GaugeChartProps> = ({
  score,
  title,
  topDriver,
  thresholds = { review_above: 0.2, decline_above: 0.8 },
}) => {
  return (
    <div className="p-3 bg-surface-2 rounded-xl border border-border-subtle space-y-2">
      {title && (
        <div className="text-[11px] font-mono font-medium text-text-secondary uppercase tracking-wider">
          {title}
        </div>
      )}
      <ScoreBar
        probability={score}
        topDriver={topDriver}
        thresholds={thresholds}
        showPercentage={true}
      />
    </div>
  );
};
