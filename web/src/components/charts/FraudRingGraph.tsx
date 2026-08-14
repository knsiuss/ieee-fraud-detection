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
    const textColor = isDark ? '#E6E8EE' : '#111827';
    const edgeColor = isDark ? '#2E3447' : '#D1D5DB';

    const cy = cytoscape({
      container: containerRef.current,
      style: [
        {
          selector: 'node',
          style: {
            label: 'data(label)',
            color: textColor,
            'font-family': 'JetBrains Mono, monospace',
            'font-size': '10px',
            'text-valign': 'bottom',
            'text-margin-y': 6,
            width: 32,
            height: 32,
            'border-width': 2,
            'border-color': 'data(borderColor)',
            'background-color': 'data(bgColor)',
          },
        },
        {
          selector: 'node[type = "transaction"]',
          style: {
            shape: 'round-rectangle',
            width: 38,
            height: 26,
          },
        },
        {
          selector: 'node[type = "card"]',
          style: {
            shape: 'diamond',
            width: 30,
            height: 30,
          },
        },
        {
          selector: 'edge',
          style: {
            width: 1.5,
            'line-color': edgeColor,
            'curve-style': 'bezier',
            'target-arrow-shape': 'none',
            opacity: 0.7,
          },
        },
        {
          selector: 'edge[fraud = "true"]',
          style: {
            'line-color': '#F43F5E',
            width: 2.5,
            'line-style': 'dashed',
            opacity: 0.9,
          },
        },
        {
          selector: ':selected',
          style: {
            'border-color': '#14B8A6',
            'border-width': 4,
          },
        },
      ],
      elements: [
        // Seed cluster 1: Card syndicate
        { data: { id: 'c1', label: 'Card •••• 4912', type: 'card', bgColor: '#1A1E2B', borderColor: '#F43F5E' } },
        { data: { id: 'tx1', label: 'TX-98421 ($1.4k)', type: 'transaction', bgColor: '#F43F5E', borderColor: '#F43F5E' } },
        { data: { id: 'tx2', label: 'TX-98422 ($850)', type: 'transaction', bgColor: '#F43F5E', borderColor: '#F43F5E' } },
        { data: { id: 'ip1', label: 'IP 185.220.101.5 (Tor)', type: 'ip', bgColor: '#1E2230', borderColor: '#F59E0B' } },
        { data: { id: 'em1', label: 'tempmail-99@xyz.org', type: 'email', bgColor: '#1E2230', borderColor: '#F43F5E' } },
        
        // Seed cluster 2: Identity proxy syndicate
        { data: { id: 'c2', label: 'Card •••• 8821', type: 'card', bgColor: '#1A1E2B', borderColor: '#F59E0B' } },
        { data: { id: 'tx3', label: 'TX-98430 ($420)', type: 'transaction', bgColor: '#F59E0B', borderColor: '#F59E0B' } },
        { data: { id: 'dev1', label: 'Device: Linux/Chrome Headless', type: 'device', bgColor: '#171A24', borderColor: '#06B6D4' } },
        { data: { id: 'tx4', label: 'TX-98435 ($310)', type: 'transaction', bgColor: '#10B981', borderColor: '#10B981' } },

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
        padding: 30,
        nodeRepulsion: () => 4500,
        idealEdgeLength: () => 70,
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
    <div className="relative w-full rounded-lg bg-surface-1 border border-border-subtle overflow-hidden">
      <div className="absolute top-3 left-3 z-10 flex items-center gap-2 bg-surface-2/90 backdrop-blur px-3 py-1.5 rounded-md border border-border-subtle text-[11px] font-mono">
        <span className="w-2 h-2 rounded-full bg-status-block"></span>
        <span>High-Risk Syndicate Cluster Detected</span>
      </div>
      <div ref={containerRef} style={{ height, width: '100%' }} />
    </div>
  );
};
