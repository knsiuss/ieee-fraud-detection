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
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross', lineStyle: { color: '#06B6D4', width: 1, type: 'dashed' } },
      formatter: (params: any) => {
        if (!params || !params.length) return '';
        const idx = params[0].dataIndex;
        const bucket = data[idx];
        return `<div class="font-mono text-xs p-1">
          <div class="font-bold text-text-primary mb-1 border-b border-border-subtle pb-1">${timestamps[idx]} (Epoch)</div>
          <div class="flex justify-between gap-4 text-accent-cyan"><span>Volume:</span> <b>${bucket.total} tx</b></div>
          <div class="flex justify-between gap-4 text-status-approve"><span>Approved:</span> <b>${bucket.approved}</b></div>
          <div class="flex justify-between gap-4 text-status-review"><span>Review Queue:</span> <b>${bucket.reviewed}</b></div>
          <div class="flex justify-between gap-4 text-status-block"><span>Declined:</span> <b>${bucket.declined}</b></div>
          <div class="flex justify-between gap-4 text-text-primary mt-1 pt-1 border-t border-border-subtle">
            <span>Evaluated GMV:</span> <b>$${bucket.amount_sum.toLocaleString()}</b>
          </div>
        </div>`;
      },
    },
    legend: {
      data: showAmount
        ? ['Transaction Volume', 'Evaluated GMV ($)', 'Declined (Fraud)']
        : ['Total Volume', 'Approved', 'Review', 'Declined'],
      textStyle: { color: '#9CA3AF', fontSize: 11, fontFamily: 'JetBrains Mono' },
      top: 0,
      right: 10,
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
      axisLabel: { color: '#9CA3AF', fontSize: 10, fontFamily: 'JetBrains Mono' },
      axisLine: { lineStyle: { color: '#222634' } },
    },
    yAxis: [
      {
        type: 'value',
        name: 'Tx Count',
        nameTextStyle: { color: '#6B7280', fontSize: 10, fontFamily: 'JetBrains Mono' },
        axisLabel: { color: '#9CA3AF', fontSize: 10, fontFamily: 'JetBrains Mono' },
        splitLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.08)' } },
      },
      ...(showAmount
        ? [
            {
              type: 'value' as const,
              name: 'GMV ($)',
              nameTextStyle: { color: '#6B7280', fontSize: 10, fontFamily: 'JetBrains Mono' },
              axisLabel: {
                color: '#9CA3AF',
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
            smooth: true,
            data: totals,
            itemStyle: { color: '#06B6D4' },
            areaStyle: {
              color: {
                type: 'linear',
                x: 0,
                y: 0,
                x2: 0,
                y2: 1,
                colorStops: [
                  { offset: 0, color: 'rgba(6, 182, 212, 0.25)' },
                  { offset: 1, color: 'rgba(6, 182, 212, 0.0)' },
                ],
              },
            },
          },
          {
            name: 'Evaluated GMV ($)',
            type: 'line',
            yAxisIndex: 1,
            smooth: true,
            data: amounts,
            itemStyle: { color: '#14B8A6' },
          },
          {
            name: 'Declined (Fraud)',
            type: 'bar',
            data: declined,
            itemStyle: { color: '#F43F5E', borderRadius: [2, 2, 0, 0] },
          },
        ]
      : [
          {
            name: 'Total Volume',
            type: 'line',
            smooth: true,
            data: totals,
            itemStyle: { color: '#06B6D4' },
            lineStyle: { width: 2 },
            areaStyle: {
              color: {
                type: 'linear',
                x: 0,
                y: 0,
                x2: 0,
                y2: 1,
                colorStops: [
                  { offset: 0, color: 'rgba(6, 182, 212, 0.20)' },
                  { offset: 1, color: 'rgba(6, 182, 212, 0.0)' },
                ],
              },
            },
          },
          {
            name: 'Approved',
            type: 'line',
            smooth: true,
            data: approved,
            itemStyle: { color: '#10B981' },
            lineStyle: { width: 1.5 },
          },
          {
            name: 'Review',
            type: 'line',
            smooth: true,
            data: reviewed,
            itemStyle: { color: '#F59E0B' },
            lineStyle: { width: 1.5 },
          },
          {
            name: 'Declined',
            type: 'line',
            smooth: true,
            data: declined,
            itemStyle: { color: '#F43F5E' },
            lineStyle: { width: 2 },
          },
        ],
  };

  return <EChartBase option={option} height={height} />;
};
