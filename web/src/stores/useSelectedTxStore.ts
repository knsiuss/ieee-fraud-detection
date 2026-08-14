import { create } from 'zustand';
import type { DecisionItem } from '../lib/types';

interface SelectedTxState {
  selectedTx: DecisionItem | null;
  isDrawerOpen: boolean;
  openDrawer: (tx: DecisionItem) => void;
  closeDrawer: () => void;
  setSelectedTx: (tx: DecisionItem | null) => void;
}

export const useSelectedTxStore = create<SelectedTxState>((set) => ({
  selectedTx: null,
  isDrawerOpen: false,
  openDrawer: (tx) => set({ selectedTx: tx, isDrawerOpen: true }),
  closeDrawer: () => set({ isDrawerOpen: false }),
  setSelectedTx: (tx) => set({ selectedTx: tx }),
}));
