import React from 'react';
import { EChartBase } from './EChartBase';
import type { EChartsOption } from 'echarts';
import type { ShapFeature } from '../../lib/types';

interface ShapWaterfallChartProps {
  features: ShapFeature[];
  height?: string | number;
}

export const ShapWaterfallChart: React.FC<ShapWaterfallChartProps> = ({
  features,
  height = '320px',
}) => {
  // Sort features by absolute contribution descending (top 8)
  const sorted = [...features]
    .sort((a, b) => Math.abs(b.contribution) - Math.abs(a.contribution))
    .slice(0, 8)
    .reverse();

  const labels = sorted.map((f) => f.feature);
  const values = sorted.map((f) => Math.round(f.contribution * 1000) / 1000);

  const option: EChartsOption = {
    animationDuration: 800,
    animationEasing: 'cubicOut',
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: 'rgba(18, 20, 28, 0.95)',
      borderColor: 'rgba(148, 163, 184, 0.15)',
      borderWidth: 1,
      padding: [10, 14],
      formatter: (params: any) => {
        const item = params[0];
        const val = item.value;
        const color = val >= 0 ? '#F43F5E' : '#10B981';
        const dir = val >= 0 ? 'Increases Risk (Fraud Driver)' : 'Decreases Risk (Safe Signal)';
        return `<div class="font-mono text-xs">
          <div class="font-bold text-text-primary mb-1 border-b border-border-subtle/60 pb-1">${item.name}</div>
          <div style="color: ${color}" class="font-bold">Contribution: ${val > 0 ? '+' : ''}${val}</div>
          <div class="text-[11px] text-text-muted mt-0.5">${dir}</div>
        </div>`;
      },
    },
    grid: {
      left: '3%',
      right: '8%',
      bottom: '3%',
      top: '5%',
      containLabel: true,
    },
    xAxis: {
      type: 'value',
      axisLabel: {
        fontFamily: 'JetBrains Mono',
        fontSize: 10,
        color: '#64748B',
        formatter: '{value}',
      },
      splitLine: {
        lineStyle: {
          color: 'rgba(148, 163, 184, 0.06)',
          type: 'dashed',
        },
      },
    },
    yAxis: {
      type: 'category',
      data: labels,
      axisLabel: {
        fontFamily: 'JetBrains Mono',
        fontSize: 11,
        color: '#94A3B8',
      },
      axisLine: {
        lineStyle: {
          color: 'rgba(148, 163, 184, 0.12)',
        },
      },
      axisTick: { show: false },
    },
    series: [
      {
        name: 'SHAP Attribution',
        type: 'bar',
        showBackground: true,
        backgroundStyle: {
          color: 'rgba(148, 163, 184, 0.03)',
          borderRadius: 6,
        },
        data: values.map((val) => ({
          value: val,
          itemStyle: {
            color:
              val >= 0
                ? {
                    type: 'linear',
                    x: 0,
                    y: 0,
                    x2: 1,
                    y2: 0,
                    colorStops: [
                      { offset: 0, color: '#F43F5E' },
                      { offset: 1, color: '#FB7185' },
                    ],
                  }
                : {
                    type: 'linear',
                    x: 0,
                    y: 0,
                    x2: 1,
                    y2: 0,
                    colorStops: [
                      { offset: 0, color: '#34D399' },
                      { offset: 1, color: '#10B981' },
                    ],
                  },
            borderRadius: val >= 0 ? [0, 6, 6, 0] : [6, 0, 0, 6],
            shadowBlur: 6,
            shadowColor: val >= 0 ? 'rgba(244, 63, 94, 0.25)' : 'rgba(16, 185, 129, 0.25)',
          },
        })),
        barWidth: '55%',
      },
    ],
  };

  return <EChartBase option={option} height={height} />;
};
