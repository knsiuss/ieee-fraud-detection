import React from 'react';
import { EChartBase } from './EChartBase';
import type { EChartsOption } from 'echarts';
import type { TimeseriesBucket } from '../../lib/types';

interface TimeseriesChartProps {
  data: TimeseriesBucket[];
  height?: string | number;
  showAmount?: boolean;
}

export const TimeseriesChart: React.FC<TimeseriesChartProps> = ({
  data,
  height = '320px',
  showAmount = false,
}) => {
  const timestamps = data.map((d) => {
    try {
      const date = new Date(d.timestamp);
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return d.timestamp;
    }
  });

  const totals = data.map((d) => d.total);
  const approved = data.map((d) => d.approved);
  const reviewed = data.map((d) => d.reviewed);
  const declined = data.map((d) => d.declined);
  const amounts = data.map((d) => d.amount_sum);

  const option: EChartsOption = {
    animationDuration: 800,
    animationEasing: 'cubicOut',
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'line',
        lineStyle: {
          color: 'rgba(6, 182, 212, 0.45)',
          width: 1.5,
          type: 'dashed',
        },
      },
      backgroundColor: 'rgba(18, 20, 28, 0.92)',
      borderColor: 'rgba(148, 163, 184, 0.15)',
      borderWidth: 1,
      padding: [10, 14],
      formatter: (params: any) => {
        if (!params || !params.length) return '';
        const idx = params[0].dataIndex;
        const bucket = data[idx];
        return `<div class="font-mono text-xs space-y-1">
          <div class="font-bold text-text-primary border-b border-border-subtle/60 pb-1.5 mb-1.5 flex items-center justify-between gap-4">
            <span>${timestamps[idx]} (Window)</span>
            <span class="text-accent-cyan font-bold">${bucket.total} tx total</span>
          </div>
          <div class="flex justify-between gap-6 text-status-approve">
            <span>● Auto-Approved:</span>
            <b>${bucket.approved} tx</b>
          </div>
          <div class="flex justify-between gap-6 text-status-review">
            <span>● Review Queue:</span>
            <b>${bucket.reviewed} tx</b>
          </div>
          <div class="flex justify-between gap-6 text-status-block">
            <span>● Declined (Blocked):</span>
            <b>${bucket.declined} tx</b>
          </div>
          <div class="flex justify-between gap-6 text-text-primary pt-1.5 border-t border-border-subtle/60">
            <span>Evaluated GMV:</span>
            <b class="text-accent-teal">$${bucket.amount_sum.toLocaleString()}</b>
          </div>
        </div>`;
      },
    },
    legend: {
      data: showAmount
        ? ['Transaction Volume', 'Evaluated GMV ($)', 'Declined (Fraud)']
        : ['Total Volume', 'Approved', 'Review', 'Declined'],
      textStyle: { color: '#94A3B8', fontSize: 11, fontFamily: 'JetBrains Mono' },
      top: 0,
      right: 10,
      icon: 'roundRect',
      itemWidth: 12,
      itemHeight: 4,
      itemGap: 16,
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '4%',
      top: '16%',
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: timestamps,
      axisLabel: {
        color: '#64748B',
        fontSize: 10,
        fontFamily: 'JetBrains Mono',
        margin: 12,
      },
      axisLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.12)' } },
      axisTick: { show: false },
    },
    yAxis: [
      {
        type: 'value',
        name: 'Volume (tx)',
        nameTextStyle: { color: '#64748B', fontSize: 10, fontFamily: 'JetBrains Mono', padding: [0, 0, 4, 0] },
        axisLabel: { color: '#64748B', fontSize: 10, fontFamily: 'JetBrains Mono' },
        splitLine: {
          lineStyle: {
            color: 'rgba(148, 163, 184, 0.06)',
            type: 'dashed',
          },
        },
      },
      ...(showAmount
        ? [
            {
              type: 'value' as const,
              name: 'GMV ($)',
              nameTextStyle: { color: '#64748B', fontSize: 10, fontFamily: 'JetBrains Mono', padding: [0, 0, 4, 0] },
              axisLabel: {
                color: '#64748B',
                fontSize: 10,
                fontFamily: 'JetBrains Mono',
                formatter: '${value}',
              },
              splitLine: { show: false },
            },
          ]
        : []),
    ],
    series: showAmount
      ? [
          {
            name: 'Transaction Volume',
            type: 'line',
            smooth: 0.4,
            showSymbol: false,
            symbol: 'circle',
            symbolSize: 6,
            data: totals,
            itemStyle: { color: '#06B6D4' },
            lineStyle: { width: 2.5, color: '#06B6D4' },
            areaStyle: {
              color: {
                type: 'linear',
                x: 0,
                y: 0,
                x2: 0,
                y2: 1,
                colorStops: [
                  { offset: 0, color: 'rgba(6, 182, 212, 0.28)' },
                  { offset: 0.8, color: 'rgba(6, 182, 212, 0.04)' },
                  { offset: 1, color: 'rgba(6, 182, 212, 0.0)' },
                ],
              },
            },
          },
          {
            name: 'Evaluated GMV ($)',
            type: 'line',
            yAxisIndex: 1,
            smooth: 0.4,
            showSymbol: false,
            symbol: 'circle',
            symbolSize: 6,
            data: amounts,
            itemStyle: { color: '#14B8A6' },
            lineStyle: { width: 2, color: '#14B8A6' },
          },
          {
            name: 'Declined (Fraud)',
            type: 'bar',
            data: declined,
            itemStyle: {
              color: '#F43F5E',
              borderRadius: [4, 4, 0, 0],
            },
            barWidth: '35%',
          },
        ]
      : [
          {
            name: 'Total Volume',
            type: 'line',
            smooth: 0.4,
            showSymbol: false,
            symbol: 'circle',
            symbolSize: 7,
            data: totals,
            itemStyle: { color: '#06B6D4' },
            lineStyle: { width: 2.5, color: '#06B6D4' },
            areaStyle: {
              color: {
                type: 'linear',
                x: 0,
                y: 0,
                x2: 0,
                y2: 1,
                colorStops: [
                  { offset: 0, color: 'rgba(6, 182, 212, 0.25)' },
                  { offset: 0.8, color: 'rgba(6, 182, 212, 0.03)' },
                  { offset: 1, color: 'rgba(6, 182, 212, 0.0)' },
                ],
              },
            },
          },
          {
            name: 'Approved',
            type: 'line',
            smooth: 0.4,
            showSymbol: false,
            symbol: 'circle',
            symbolSize: 6,
            data: approved,
            itemStyle: { color: '#10B981' },
            lineStyle: { width: 1.8, color: '#10B981' },
          },
          {
            name: 'Review',
            type: 'line',
            smooth: 0.4,
            showSymbol: false,
            symbol: 'circle',
            symbolSize: 6,
            data: reviewed,
            itemStyle: { color: '#F59E0B' },
            lineStyle: { width: 1.8, color: '#F59E0B' },
          },
          {
            name: 'Declined',
            type: 'line',
            smooth: 0.4,
            showSymbol: false,
            symbol: 'circle',
            symbolSize: 6,
            data: declined,
            itemStyle: { color: '#F43F5E' },
            lineStyle: {
              width: 2.2,
              color: '#F43F5E',
              shadowBlur: 8,
              shadowColor: 'rgba(244, 63, 94, 0.4)',
            },
          },
        ],
  };

  return <EChartBase option={option} height={height} />;
};
