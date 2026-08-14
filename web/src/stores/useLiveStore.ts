import { create } from 'zustand';
import type { DecisionItem, DecisionType } from '../lib/types';

const MAX_RING_BUFFER = 500;

interface LiveState {
  decisions: DecisionItem[];
  seenIds: Set<string>;
  isPaused: boolean;
  filterDecision: DecisionType | 'ALL';
  searchQuery: string;
  rollingTps: number;
  lastEventsCount: number;
  counts: {
    APPROVE: number;
    MANUAL_REVIEW: number;
    DECLINE: number;
  };
  addDecisions: (items: DecisionItem[]) => void;
  togglePause: () => void;
  setFilterDecision: (filter: DecisionType | 'ALL') => void;
  setSearchQuery: (query: string) => void;
  clearDecisions: () => void;
}

export const useLiveStore = create<LiveState>((set, get) => {
  // TPS calculation timer
  let lastTimestamp = Date.now();
  let eventsInInterval = 0;

  setInterval(() => {
    const now = Date.now();
    const elapsedSeconds = (now - lastTimestamp) / 1000;
    if (elapsedSeconds >= 1) {
      const tps = Math.round((eventsInInterval / elapsedSeconds) * 10) / 10;
      set({ rollingTps: tps, lastEventsCount: eventsInInterval });
      eventsInInterval = 0;
      lastTimestamp = now;
    }
  }, 1000);

  return {
    decisions: [],
    seenIds: new Set<string>(),
    isPaused: false,
    filterDecision: 'ALL',
    searchQuery: '',
    rollingTps: 0,
    lastEventsCount: 0,
    counts: {
      APPROVE: 0,
      MANUAL_REVIEW: 0,
      DECLINE: 0,
    },

    addDecisions: (newItems: DecisionItem[]) => {
      const state = get();
      if (state.isPaused || newItems.length === 0) return;

      const seen = new Set(state.seenIds);
      const uniqueNew: DecisionItem[] = [];
      const updatedCounts = { ...state.counts };

      for (const item of newItems) {
        if (!seen.has(item.transaction_id)) {
          seen.add(item.transaction_id);
          uniqueNew.push(item);
          if (item.decision in updatedCounts) {
            updatedCounts[item.decision] += 1;
          }
        }
      }

      if (uniqueNew.length === 0) return;
      eventsInInterval += uniqueNew.length;

      // Prepend newest items first and slice buffer
      const combined = [...uniqueNew.reverse(), ...state.decisions].slice(0, MAX_RING_BUFFER);

      set({
        decisions: combined,
        seenIds: seen,
        counts: updatedCounts,
      });
    },

    togglePause: () => set((s) => ({ isPaused: !s.isPaused })),
    setFilterDecision: (filter) => set({ filterDecision: filter }),
    setSearchQuery: (searchQuery) => set({ searchQuery }),
    clearDecisions: () =>
      set({
        decisions: [],
        seenIds: new Set<string>(),
        counts: { APPROVE: 0, MANUAL_REVIEW: 0, DECLINE: 0 },
        rollingTps: 0,
      }),
  };
});
