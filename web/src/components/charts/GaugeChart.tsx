import React from 'react';
import { EChartBase } from './EChartBase';
import type { EChartsOption } from 'echarts';

interface GaugeChartProps {
  score: number; // 0.0 to 1.0
  title?: string;
  height?: string | number;
}

export const GaugeChart: React.FC<GaugeChartProps> = ({
  score,
  title = 'FRAUD PROBABILITY',
  height = '240px',
}) => {
  const percentage = Math.round(score * 1000) / 10;

  const option: EChartsOption = {
    series: [
      {
        type: 'gauge',
        startAngle: 180,
        endAngle: 0,
        center: ['50%', '75%'],
        radius: '95%',
        min: 0,
        max: 100,
        splitNumber: 5,
        axisLine: {
          lineStyle: {
            width: 14,
            color: [
              [0.2, '#10B981'], // Approve (Green)
              [0.8, '#F59E0B'], // Review (Amber)
              [1.0, '#F43F5E'], // Decline (Crimson)
            ],
          },
        },
        pointer: {
          icon: 'path://M12.8,0.7l12,40.1H0.7L12.8,0.7z',
          length: '12%',
          width: 14,
          offsetCenter: [0, '-55%'],
          itemStyle: {
            color: 'inherit',
          },
        },
        axisTick: {
          length: 6,
          lineStyle: {
            color: 'inherit',
            width: 1.5,
          },
        },
        splitLine: {
          length: 12,
          lineStyle: {
            color: 'inherit',
            width: 2,
          },
        },
        axisLabel: {
          color: '#9CA3AF',
          fontSize: 10,
          fontFamily: 'JetBrains Mono',
          distance: -40,
          formatter: (value: number) => {
            if (value === 0) return '0%';
            if (value === 50) return '50%';
            if (value === 100) return '100%';
            return '';
          },
        },
        title: {
          offsetCenter: [0, '-15%'],
          fontSize: 11,
          fontFamily: 'JetBrains Mono',
          color: '#9CA3AF',
        },
        detail: {
          fontSize: 24,
          offsetCenter: [0, '15%'],
          valueAnimation: true,
          formatter: () => `${percentage.toFixed(1)}%`,
          color: score > 0.8 ? '#F43F5E' : score > 0.2 ? '#F59E0B' : '#10B981',
          fontFamily: 'JetBrains Mono',
          fontWeight: 'bold',
        },
        data: [
          {
            value: percentage,
            name: title,
          },
        ],
      },
    ],
  };

  return <EChartBase option={option} height={height} />;
};
