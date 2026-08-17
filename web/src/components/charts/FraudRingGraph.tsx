import React, { useEffect, useRef } from 'react';
import cytoscape from 'cytoscape';
import { useThemeStore } from '../../stores/useThemeStore';

interface FraudRingGraphProps {
  height?: string | number;
  onNodeClick?: (nodeId: string, nodeType: string) => void;
}

export const FraudRingGraph: React.FC<FraudRingGraphProps> = ({
  height = '420px',
  onNodeClick,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);
  const theme = useThemeStore((s) => s.theme);

  useEffect(() => {
    if (!containerRef.current) return;

    const isDark = theme === 'dark';
    const textColor = isDark ? '#F6F4EF' : '#17161A';
    const edgeColor = isDark ? 'rgba(230, 227, 218, 0.15)' : '#DCD8CE';
    const blockColor = isDark ? '#B23B2E' : '#A83A2E';
    const reviewColor = isDark ? '#B8863A' : '#A87B34';
    const approveColor = isDark ? '#4F7A5C' : '#3B5A44';
    const surfaceBg = isDark ? '#26252B' : '#EFEDE5';

    const cy = cytoscape({
      container: containerRef.current,
      style: [
        {
          selector: 'node',
          style: {
            label: 'data(label)',
            color: textColor,
            'font-family': 'IBM Plex Mono, JetBrains Mono, monospace',
            'font-size': '10px',
            'text-valign': 'bottom',
            'text-margin-y': 5,
            width: 28,
            height: 28,
            'border-width': 1.5,
            'border-color': 'data(borderColor)',
            'background-color': 'data(bgColor)',
          },
        },
        {
          selector: 'node[type = "transaction"]',
          style: {
            shape: 'round-rectangle',
            width: 36,
            height: 24,
          },
        },
        {
          selector: 'node[type = "card"]',
          style: {
            shape: 'diamond',
            width: 28,
            height: 28,
          },
        },
        {
          selector: 'edge',
          style: {
            width: 1,
            'line-color': edgeColor,
            'curve-style': 'bezier',
            'target-arrow-shape': 'none',
            opacity: 0.8,
          },
        },
        {
          selector: 'edge[fraud = "true"]',
          style: {
            'line-color': blockColor,
            width: 1.5,
            'line-style': 'dashed',
            opacity: 0.9,
          },
        },
        {
          selector: ':selected',
          style: {
            'border-color': textColor,
            'border-width': 2.5,
          },
        },
      ],
      elements: [
        // Seed cluster 1: Card syndicate
        { data: { id: 'c1', label: 'Card •••• 4912', type: 'card', bgColor: surfaceBg, borderColor: blockColor } },
        { data: { id: 'tx1', label: 'TX-98421 ($1.4k)', type: 'transaction', bgColor: surfaceBg, borderColor: blockColor } },
        { data: { id: 'tx2', label: 'TX-98422 ($850)', type: 'transaction', bgColor: surfaceBg, borderColor: blockColor } },
        { data: { id: 'ip1', label: 'IP 185.220.101.5 (Tor)', type: 'ip', bgColor: surfaceBg, borderColor: reviewColor } },
        { data: { id: 'em1', label: 'tempmail-99@xyz.org', type: 'email', bgColor: surfaceBg, borderColor: blockColor } },
        
        // Seed cluster 2: Identity proxy syndicate
        { data: { id: 'c2', label: 'Card •••• 8821', type: 'card', bgColor: surfaceBg, borderColor: reviewColor } },
        { data: { id: 'tx3', label: 'TX-98430 ($420)', type: 'transaction', bgColor: surfaceBg, borderColor: reviewColor } },
        { data: { id: 'dev1', label: 'Device: Linux/Chrome Headless', type: 'device', bgColor: surfaceBg, borderColor: textColor } },
        { data: { id: 'tx4', label: 'TX-98435 ($310)', type: 'transaction', bgColor: surfaceBg, borderColor: approveColor } },

        // Edges
        { data: { id: 'e1', source: 'tx1', target: 'c1', fraud: 'true' } },
        { data: { id: 'e2', source: 'tx2', target: 'c1', fraud: 'true' } },
        { data: { id: 'e3', source: 'tx1', target: 'ip1', fraud: 'true' } },
        { data: { id: 'e4', source: 'tx2', target: 'em1', fraud: 'true' } },
        { data: { id: 'e5', source: 'tx3', target: 'c2' } },
        { data: { id: 'e6', source: 'tx3', target: 'dev1' } },
        { data: { id: 'e7', source: 'tx4', target: 'dev1' } },
        { data: { id: 'e8', source: 'ip1', target: 'tx3', fraud: 'true' } },
      ],
      layout: {
        name: 'cose',
        animate: false,
        padding: 24,
        nodeRepulsion: () => 4000,
        idealEdgeLength: () => 65,
      },
    });

    cy.on('tap', 'node', (evt) => {
      const node = evt.target;
      if (onNodeClick) {
        onNodeClick(node.id(), node.data('type'));
      }
    });

    cyRef.current = cy;

    return () => {
      cy.destroy();
    };
  }, [theme, onNodeClick]);

  return (
    <div className="relative w-full panel overflow-hidden">
      <div className="absolute top-2.5 left-2.5 z-10 flex items-center gap-1.5 bg-surface-2 px-2.5 py-1 rounded-[6px] border border-border-subtle text-[10px] font-mono text-text-secondary">
        <span className="w-1.5 h-1.5 rounded-full bg-status-block"></span>
        <span>Syndicate Cluster Entity Graph</span>
      </div>
      <div ref={containerRef} style={{ height, width: '100%' }} />
    </div>
  );
};
