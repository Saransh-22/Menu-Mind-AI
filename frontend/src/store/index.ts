import { create } from 'zustand';
import { Restaurant, AnalysisRun } from '../types';

interface AppState {
  activeRestaurant: Restaurant | null;
  activeRun: AnalysisRun | null;
  isSidebarCollapsed: boolean;
  isAssistantDrawerOpen: boolean;
  assistantPromptContext: string | null;
  setActiveRestaurant: (restaurant: Restaurant | null) => void;
  setActiveRun: (run: AnalysisRun | null) => void;
  toggleSidebar: () => void;
  toggleAssistantDrawer: () => void;
  setAssistantDrawerOpen: (open: boolean) => void;
  openAssistantWithContext: (prompt: string) => void;
  clearAssistantPromptContext: () => void;
}

const SAVED_REST_KEY = 'menumind_active_restaurant';
const SAVED_RUN_KEY = 'menumind_active_run';

function loadSaved<T>(key: string): T | null {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export const useAppStore = create<AppState>((set) => ({
  activeRestaurant: loadSaved<Restaurant>(SAVED_REST_KEY),
  activeRun: loadSaved<AnalysisRun>(SAVED_RUN_KEY),
  isSidebarCollapsed: false,
  isAssistantDrawerOpen: false,
  assistantPromptContext: null,

  setActiveRestaurant: (restaurant) => {
    if (restaurant) {
      localStorage.setItem(SAVED_REST_KEY, JSON.stringify(restaurant));
    } else {
      localStorage.removeItem(SAVED_REST_KEY);
    }
    set({ activeRestaurant: restaurant });
  },

  setActiveRun: (run) => {
    if (run) {
      localStorage.setItem(SAVED_RUN_KEY, JSON.stringify(run));
    } else {
      localStorage.removeItem(SAVED_RUN_KEY);
    }
    set({ activeRun: run });
  },

  toggleSidebar: () =>
    set((state) => ({ isSidebarCollapsed: !state.isSidebarCollapsed })),

  toggleAssistantDrawer: () =>
    set((state) => ({ isAssistantDrawerOpen: !state.isAssistantDrawerOpen })),

  setAssistantDrawerOpen: (open: boolean) =>
    set({ isAssistantDrawerOpen: open }),

  openAssistantWithContext: (prompt: string) =>
    set({ isAssistantDrawerOpen: true, assistantPromptContext: prompt }),

  clearAssistantPromptContext: () =>
    set({ assistantPromptContext: null }),
}));
