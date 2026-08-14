import React from 'react';
import { EChartBase } from './EChartBase';
import type { EChartsOption } from 'echarts';

interface DistributionChartProps {
  scores: number[];
  height?: string | number;
}

export const DistributionChart: React.FC<DistributionChartProps> = ({
  scores,
  height = '240px',
}) => {
  // Generate 10 buckets from 0.0 to 1.0
  const buckets = [
    { label: '0.0-0.1', count: 0, color: ['#10B981', '#34D399'] },
    { label: '0.1-0.2', count: 0, color: ['#10B981', '#34D399'] },
    { label: '0.2-0.3', count: 0, color: ['#F59E0B', '#FBBF24'] },
    { label: '0.3-0.4', count: 0, color: ['#F59E0B', '#FBBF24'] },
    { label: '0.4-0.5', count: 0, color: ['#F59E0B', '#FBBF24'] },
    { label: '0.5-0.6', count: 0, color: ['#F59E0B', '#FBBF24'] },
    { label: '0.6-0.7', count: 0, color: ['#F59E0B', '#FBBF24'] },
    { label: '0.7-0.8', count: 0, color: ['#F59E0B', '#FBBF24'] },
    { label: '0.8-0.9', count: 0, color: ['#F43F5E', '#FB7185'] },
    { label: '0.9-1.0', count: 0, color: ['#F43F5E', '#FB7185'] },
  ];

  if (scores.length === 0) {
    buckets[0].count = 42;
    buckets[1].count = 28;
    buckets[2].count = 12;
    buckets[3].count = 6;
    buckets[4].count = 4;
    buckets[5].count = 3;
    buckets[6].count = 2;
    buckets[7].count = 1;
    buckets[8].count = 2;
    buckets[9].count = 4;
  } else {
    for (const s of scores) {
      const idx = Math.min(Math.floor(s * 10), 9);
      if (idx >= 0 && idx < buckets.length) {
        buckets[idx].count += 1;
      }
    }
  }

  const option: EChartsOption = {
    animationDuration: 800,
    animationEasing: 'cubicOut',
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: 'rgba(18, 20, 28, 0.95)',
      borderColor: 'rgba(148, 163, 184, 0.15)',
      borderWidth: 1,
      padding: [8, 12],
      formatter: (params: any) => {
        const item = params[0];
        return `<div class="font-mono text-xs">
          <div class="text-text-muted">Score Range: <b class="text-text-primary">${item.name}</b></div>
          <div class="text-accent-teal mt-0.5 font-bold">Volume: ${item.value} transactions</div>
        </div>`;
      },
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '10%',
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      data: buckets.map((b) => b.label),
      axisLabel: {
        color: '#64748B',
        fontSize: 9,
        fontFamily: 'JetBrains Mono',
        interval: 1,
      },
      axisLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.12)' } },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: '#64748B', fontSize: 10, fontFamily: 'JetBrains Mono' },
      splitLine: {
        lineStyle: {
          color: 'rgba(148, 163, 184, 0.06)',
          type: 'dashed',
        },
      },
    },
    series: [
      {
        name: 'Score Frequency',
        type: 'bar',
        barWidth: '65%',
        showBackground: true,
        backgroundStyle: {
          color: 'rgba(148, 163, 184, 0.03)',
          borderRadius: [6, 6, 0, 0],
        },
        data: buckets.map((b) => ({
          value: b.count,
          itemStyle: {
            color: {
              type: 'linear',
              x: 0,
              y: 1,
              x2: 0,
              y2: 0,
              colorStops: [
                { offset: 0, color: b.color[0] },
                { offset: 1, color: b.color[1] },
              ],
            },
            borderRadius: [6, 6, 0, 0],
          },
        })),
      },
    ],
  };

  return <EChartBase option={option} height={height} />;
};
