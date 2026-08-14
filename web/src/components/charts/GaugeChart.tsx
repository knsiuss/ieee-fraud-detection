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

  // Determine dynamic accent colors based on risk tier
  let activeColor = '#10B981';
  let tierLabel = 'LOW RISK';
  let tierSub = 'Auto-Approve Zone';

  if (score > 0.8) {
    activeColor = '#F43F5E';
    tierLabel = 'CRITICAL FRAUD';
    tierSub = 'Immediate Block';
  } else if (score > 0.2) {
    activeColor = '#F59E0B';
    tierLabel = 'ELEVATED RISK';
    tierSub = 'Review Required';
  }

  const option: EChartsOption = {
    animationDuration: 1000,
    animationEasing: 'cubicOut',
    series: [
      {
        type: 'gauge',
        startAngle: 210,
        endAngle: -30,
        min: 0,
        max: 100,
        splitNumber: 10,
        radius: '88%',
        center: ['50%', '55%'],
        itemStyle: {
          color: activeColor,
          shadowColor: activeColor,
          shadowBlur: 10,
        },
        progress: {
          show: true,
          roundCap: true,
          width: 14,
        },
        pointer: {
          show: false,
        },
        axisLine: {
          roundCap: true,
          lineStyle: {
            width: 14,
            color: [[1, 'rgba(148, 163, 184, 0.1)']],
          },
        },
        axisTick: {
          show: false,
        },
        splitLine: {
          show: false,
        },
        axisLabel: {
          show: false,
        },
        title: {
          offsetCenter: [0, '36%'],
          fontSize: 10,
          fontFamily: 'JetBrains Mono',
          color: '#94A3B8',
          fontWeight: 600,
        },
        detail: {
          valueAnimation: true,
          offsetCenter: [0, '-4%'],
          fontSize: 32,
          fontWeight: 'bold',
          fontFamily: 'JetBrains Mono',
          formatter: () => `${percentage.toFixed(1)}%`,
          color: activeColor,
        },
        data: [
          {
            value: percentage,
            name: `${tierLabel} • ${tierSub}`,
          },
        ],
      },
    ],
  };

  return <EChartBase option={option} height={height} />;
};
