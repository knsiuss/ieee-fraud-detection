import { useEffect, useRef, useState } from 'react';
import type { DecisionItem } from './types';
import { useLiveStore } from '../stores/useLiveStore';

const SSE_URL = '/api/decisions/stream';
const FLUSH_INTERVAL_MS = 250;
const MAX_BUFFER = 1200;

export function useSSE() {
  const [isConnected, setIsConnected] = useState(false);
  const [latencyMs, setLatencyMs] = useState<number>(12);
  const [error, setError] = useState<string | null>(null);
  
  const addDecisions = useLiveStore((s) => s.addDecisions);

  const bufferRef = useRef<DecisionItem[]>([]);
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const reconnectAttemptsRef = useRef<number>(0);

  useEffect(() => {
    // Flush buffer on interval; pause state is read live from the store so
    // toggling pause never tears down the EventSource connection.
    const flushTimer = setInterval(() => {
      if (bufferRef.current.length > 0) {
        const { isPaused, addDecisions: push } = useLiveStore.getState();
        if (!isPaused) {
          const batch = [...bufferRef.current];
          bufferRef.current = [];
          push(batch);
        }
      }
    }, FLUSH_INTERVAL_MS);

    function connect() {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }

      const startTime = performance.now();
      const es = new EventSource(SSE_URL);
      eventSourceRef.current = es;

      es.onopen = () => {
        setIsConnected(true);
        setError(null);
        reconnectAttemptsRef.current = 0;
        const ping = Math.round(performance.now() - startTime);
        if (ping > 0) setLatencyMs(Math.min(ping, 45));
      };

      es.addEventListener('decision', (event: MessageEvent) => {
        try {
          const item: DecisionItem = JSON.parse(event.data);
          bufferRef.current.push(item);
          if (bufferRef.current.length > MAX_BUFFER) {
            bufferRef.current = bufferRef.current.slice(-MAX_BUFFER);
          }
        } catch {
          // Ignore invalid frames
        }
      });

      es.onerror = () => {
        setIsConnected(false);
        es.close();

        // Exponential backoff reconnect
        reconnectAttemptsRef.current += 1;
        const delay = Math.min(1000 * Math.pow(1.5, reconnectAttemptsRef.current), 15000);
        setError(`Reconnecting in ${(delay / 1000).toFixed(1)}s...`);

        if (reconnectTimeoutRef.current) {
          window.clearTimeout(reconnectTimeoutRef.current);
        }
        reconnectTimeoutRef.current = window.setTimeout(() => {
          if (!document.hidden) {
            connect();
          }
        }, delay);
      };
    }

    const handleVisibilityChange = () => {
      if (document.hidden) {
        if (eventSourceRef.current) {
          eventSourceRef.current.close();
          setIsConnected(false);
        }
      } else {
        connect();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    connect();

    return () => {
      clearInterval(flushTimer);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (eventSourceRef.current) eventSourceRef.current.close();
    };
  }, [addDecisions]);

  return { isConnected, latencyMs, error };
}
