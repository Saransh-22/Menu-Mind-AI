import React from 'react';
import { useLocation } from 'react-router-dom';
import { useAppStore } from '../../store';
import { Bot, Sparkles } from 'lucide-react';

export const FloatingAssistant: React.FC = () => {
  const { isAssistantDrawerOpen, toggleAssistantDrawer, activeRestaurant } = useAppStore();
  const location = useLocation();

  // Hide floating pill when already on the full assistant workspace or onboarding
  if (location.pathname === '/assistant' || location.pathname === '/onboarding') {
    return null;
  }

  return (
    <div className="fixed bottom-6 right-6 z-40">
      <button
        onClick={toggleAssistantDrawer}
        className={`group flex items-center gap-2.5 px-4 py-3 rounded-full shadow-xl transition-all duration-300 transform hover:scale-105 ${
          isAssistantDrawerOpen
            ? 'bg-emerald-800 text-white ring-4 ring-emerald-500/20'
            : 'bg-emerald-600 hover:bg-emerald-700 text-white'
        }`}
        title={`Ask MenuMind AI about ${activeRestaurant?.name || 'your restaurant'}`}
      >
        <div className="relative">
          <Bot className="w-5 h-5 text-white" />
          <span className="absolute -top-1 -right-1 flex h-2.5 w-2.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-300 opacity-75" />
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-400" />
          </span>
        </div>
        <span className="text-xs font-semibold tracking-wide hidden sm:inline-block">
          Ask MenuMind AI
        </span>
        <Sparkles className="w-3.5 h-3.5 text-emerald-200 group-hover:rotate-12 transition-transform hidden sm:inline-block" />
      </button>
    </div>
  );
};
