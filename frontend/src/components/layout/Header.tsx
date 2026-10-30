import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
  Store,
  Calendar,
  Sparkles,
  ChevronDown,
  PlusCircle,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  RefreshCw,
} from 'lucide-react';
import { useAppStore } from '../../store';
import { fetchRestaurants, fetchRestaurantRuns, createAnalysisRun } from '../../api/restaurants';
import { triggerAiAnalysis } from '../../api/recommendations';

export const Header: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { activeRestaurant, activeRun, setActiveRestaurant, setActiveRun, isSidebarCollapsed } = useAppStore();

  const [isRestDropdownOpen, setIsRestDropdownOpen] = useState(false);
  const [isRunDropdownOpen, setIsRunDropdownOpen] = useState(false);

  // Fetch all restaurants for switcher
  const { data: restaurants = [] } = useQuery({
    queryKey: ['restaurants'],
    queryFn: fetchRestaurants,
  });

  // Fetch runs for the active restaurant
  const { data: runs = [] } = useQuery({
    queryKey: ['runs', activeRestaurant?.id],
    queryFn: () => (activeRestaurant ? fetchRestaurantRuns(activeRestaurant.id) : Promise.resolve([])),
    enabled: !!activeRestaurant?.id,
  });

  // Trigger AI Analysis mutation
  const runAiMutation = useMutation({
    mutationFn: (runId: number) => triggerAiAnalysis(runId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recommendations', activeRun?.id] });
      queryClient.invalidateQueries({ queryKey: ['analysisProgress', activeRun?.id] });
      navigate('/recommendations');
    },
  });

  // Create new run mutation
  const createRunMutation = useMutation({
    mutationFn: (restaurantId: number) =>
      createAnalysisRun(restaurantId, {
        period_start: new Date(Date.now() - 30 * 86400000).toISOString().split('T')[0],
        period_end: new Date().toISOString().split('T')[0],
        notes: 'New Analysis Cycle',
      }),
    onSuccess: (newRun) => {
      setActiveRun(newRun);
      queryClient.invalidateQueries({ queryKey: ['runs', activeRestaurant?.id] });
      setIsRunDropdownOpen(false);
    },
  });

  return (
    <header
      className={`fixed top-0 right-0 z-30 h-16 bg-cream-card/90 backdrop-blur-md border-b border-cream-border flex items-center justify-between px-6 transition-all duration-300 ${
        isSidebarCollapsed ? 'left-20' : 'left-64'
      }`}
    >
      {/* Left: Venue & Run Selector */}
      <div className="flex items-center gap-3">
        {/* Restaurant Switcher */}
        <div className="relative">
          <button
            onClick={() => {
              setIsRestDropdownOpen(!isRestDropdownOpen);
              setIsRunDropdownOpen(false);
            }}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-cream-border bg-white hover:border-forest/30 text-xs font-semibold text-brandText-primary shadow-xs transition"
          >
            <Store className="w-3.5 h-3.5 text-forest" />
            <span className="truncate max-w-[140px]">
              {activeRestaurant ? activeRestaurant.name : 'Select Venue'}
            </span>
            <ChevronDown className="w-3.5 h-3.5 text-brandText-secondary" />
          </button>

          {isRestDropdownOpen && (
            <div className="absolute left-0 mt-2 w-64 bg-white rounded-xl shadow-modal border border-cream-border py-1.5 z-50">
              <div className="px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider text-brandText-secondary border-b border-cream-border">
                Switch Venue
              </div>
              <div className="max-h-52 overflow-y-auto py-1">
                {restaurants.map((rest) => (
                  <button
                    key={rest.id}
                    onClick={() => {
                      setActiveRestaurant(rest);
                      setIsRestDropdownOpen(false);
                    }}
                    className={`w-full text-left px-3 py-2 text-xs flex items-center justify-between hover:bg-cream/60 transition ${
                      activeRestaurant?.id === rest.id ? 'bg-forest-muted text-forest font-bold' : 'text-brandText-primary'
                    }`}
                  >
                    <div>
                      <div className="font-semibold">{rest.name}</div>
                      <div className="text-[11px] text-brandText-secondary">{rest.city || 'No City'}</div>
                    </div>
                    {activeRestaurant?.id === rest.id && <CheckCircle2 className="w-3.5 h-3.5 text-forest" />}
                  </button>
                ))}
              </div>
              <div className="p-2 border-t border-cream-border">
                <button
                  onClick={() => {
                    setIsRestDropdownOpen(false);
                    navigate('/onboarding');
                  }}
                  className="w-full flex items-center justify-center gap-1.5 py-1.5 rounded-lg bg-cream text-xs font-semibold text-forest hover:bg-forest hover:text-white transition"
                >
                  <PlusCircle className="w-3.5 h-3.5" />
                  Add New Restaurant
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Run Selector */}
        {activeRestaurant && (
          <div className="relative">
            <button
              onClick={() => {
                setIsRunDropdownOpen(!isRunDropdownOpen);
                setIsRestDropdownOpen(false);
              }}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-cream-border bg-white hover:border-forest/30 text-xs font-semibold text-brandText-primary shadow-xs transition"
            >
              <Calendar className="w-3.5 h-3.5 text-amber" />
              <span>{activeRun ? `Run #${activeRun.id}` : 'Select Run'}</span>
              <ChevronDown className="w-3.5 h-3.5 text-brandText-secondary" />
            </button>

            {isRunDropdownOpen && (
              <div className="absolute left-0 mt-2 w-72 bg-white rounded-xl shadow-modal border border-cream-border py-1.5 z-50">
                <div className="px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider text-brandText-secondary border-b border-cream-border flex items-center justify-between">
                  <span>Analysis Runs</span>
                  <span className="font-mono text-[10px]">{runs.length} total</span>
                </div>
                <div className="max-h-52 overflow-y-auto py-1">
                  {runs.map((r) => (
                    <button
                      key={r.id}
                      onClick={() => {
                        setActiveRun(r);
                        setIsRunDropdownOpen(false);
                      }}
                      className={`w-full text-left px-3 py-2 text-xs flex items-center justify-between hover:bg-cream/60 transition ${
                        activeRun?.id === r.id ? 'bg-forest-muted text-forest font-bold' : 'text-brandText-primary'
                      }`}
                    >
                      <div>
                        <div className="font-semibold">Run #{r.id} · {r.status}</div>
                        <div className="text-[11px] text-brandText-secondary">
                          {r.period_start || '?'} → {r.period_end || '?'}
                        </div>
                      </div>
                      {r.data_quality_score && (
                        <span className="text-[10px] font-mono font-bold text-forest bg-forest-muted px-1.5 py-0.5 rounded">
                          {Math.round(r.data_quality_score * 100)}% Q
                        </span>
                      )}
                    </button>
                  ))}
                </div>
                <div className="p-2 border-t border-cream-border">
                  <button
                    onClick={() => activeRestaurant && createRunMutation.mutate(activeRestaurant.id)}
                    disabled={createRunMutation.isPending}
                    className="w-full flex items-center justify-center gap-1.5 py-1.5 rounded-lg bg-cream text-xs font-semibold text-forest hover:bg-forest hover:text-white transition"
                  >
                    <PlusCircle className="w-3.5 h-3.5" />
                    Start New Analysis Run
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Right: Data badges and Run AI CTA */}
      <div className="flex items-center gap-3">
        {/* Dataset presence pills */}
        {activeRun?.datasets && (
          <div className="hidden lg:flex items-center gap-1.5 px-3 py-1 rounded-full bg-cream border border-cream-border text-[11px]">
            <span className={`flex items-center gap-1 ${activeRun.datasets.menu ? 'text-forest font-semibold' : 'text-brandText-secondary'}`}>
              {activeRun.datasets.menu ? '●' : '○'} Menu
            </span>
            <span className="text-cream-border">|</span>
            <span className={`flex items-center gap-1 ${activeRun.datasets.sales ? 'text-forest font-semibold' : 'text-brandText-secondary'}`}>
              {activeRun.datasets.sales ? '●' : '○'} Sales
            </span>
            <span className="text-cream-border">|</span>
            <span className={`flex items-center gap-1 ${activeRun.datasets.reviews ? 'text-forest font-semibold' : 'text-brandText-secondary'}`}>
              {activeRun.datasets.reviews ? '●' : '○'} Reviews
            </span>
            <span className="text-cream-border">|</span>
            <span className={`flex items-center gap-1 ${activeRun.datasets.costs ? 'text-forest font-semibold' : 'text-brandText-secondary'}`}>
              {activeRun.datasets.costs ? '●' : '○'} Costs
            </span>
          </div>
        )}

        {/* Primary CTA: Run AI Analysis */}
        {activeRun && (
          <button
            onClick={() => runAiMutation.mutate(activeRun.id)}
            disabled={runAiMutation.isPending}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-forest hover:bg-forest-light text-white text-xs font-bold transition shadow-sm disabled:opacity-50"
          >
            {runAiMutation.isPending ? (
              <>
                <RefreshCw className="w-3.5 h-3.5 animate-spin text-amber" />
                <span>Analyzing...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-3.5 h-3.5 text-amber" />
                <span>Run AI Analysis</span>
              </>
            )}
          </button>
        )}
      </div>
    </header>
  );
};
