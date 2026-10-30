import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  UtensilsCrossed,
  Store,
  Sparkles,
  ArrowRight,
  Search,
  Building,
  CheckCircle2,
} from 'lucide-react';
import { useAppStore } from '../../store';
import {
  fetchRestaurants,
  createRestaurant,
  fetchAutocomplete,
  createAnalysisRun,
  fetchRestaurantRuns,
} from '../../api/restaurants';

export const OnboardingPage: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { setActiveRestaurant, setActiveRun } = useAppStore();

  const [tab, setTab] = useState<'create' | 'existing'>('create');
  const [name, setName] = useState('');
  const [city, setCity] = useState('');
  const [location, setLocation] = useState('');
  const [category, setCategory] = useState('');
  const [website, setWebsite] = useState('');
  const [selectedExistingId, setSelectedExistingId] = useState<number | null>(null);

  // Autocomplete suggestions
  const { data: suggestions = [] } = useQuery({
    queryKey: ['autocomplete', name, city],
    queryFn: () => (name.length >= 2 ? fetchAutocomplete(name, city) : Promise.resolve([])),
    enabled: name.length >= 2,
  });

  // Existing restaurants
  const { data: existingRestaurants = [] } = useQuery({
    queryKey: ['restaurants'],
    queryFn: fetchRestaurants,
  });

  // Create restaurant & initial run
  const createMutation = useMutation({
    mutationFn: async () => {
      const rest = await createRestaurant({
        name: name.trim(),
        city: city.trim(),
        location: location.trim(),
        category: category.trim(),
        website: website.trim(),
      });
      const run = await createAnalysisRun(rest.id, {
        period_start: new Date(Date.now() - 30 * 86400000).toISOString().split('T')[0],
        period_end: new Date().toISOString().split('T')[0],
        notes: 'Initial Onboarding Run',
      });
      return { rest, run };
    },
    onSuccess: ({ rest, run }) => {
      setActiveRestaurant(rest);
      setActiveRun(run);
      queryClient.invalidateQueries({ queryKey: ['restaurants'] });
      navigate('/upload');
    },
  });

  const selectExistingMutation = useMutation({
    mutationFn: async (restaurantId: number) => {
      const rest = existingRestaurants.find((r) => r.id === restaurantId);
      if (!rest) throw new Error('Restaurant not found');
      
      const existingRuns = await fetchRestaurantRuns(restaurantId);
      let run = existingRuns && existingRuns.length > 0 ? existingRuns[0] : null;

      if (!run) {
        run = await createAnalysisRun(restaurantId, {
          period_start: new Date(Date.now() - 30 * 86400000).toISOString().split('T')[0],
          period_end: new Date().toISOString().split('T')[0],
          notes: 'Session Run',
        });
      }
      return { rest, run };
    },
    onSuccess: ({ rest, run }) => {
      setActiveRestaurant(rest);
      setActiveRun(run);
      navigate('/overview');
    },
  });

  return (
    <div className="min-h-screen bg-cream flex flex-col justify-center items-center py-12 px-4 sm:px-6 lg:px-8">
      {/* Brand Hero */}
      <div className="text-center max-w-xl mx-auto mb-8">
        <div className="w-14 h-14 rounded-2xl bg-forest text-amber flex items-center justify-center mx-auto mb-4 shadow-card">
          <UtensilsCrossed className="w-7 h-7" />
        </div>
        <h1 className="text-3xl font-extrabold font-display text-forest-dark tracking-tight">
          Welcome to MenuMind<span className="text-amber">.ai</span>
        </h1>
        <p className="mt-2 text-sm text-brandText-secondary leading-relaxed">
          The modern culinary intelligence workspace combining sales analytics, customer sentiment,
          and Gemini agentic recommendations.
        </p>
      </div>

      {/* Main Form Card */}
      <div className="bg-cream-card rounded-card border border-cream-border p-8 shadow-cardHover max-w-xl w-full">
        {/* Tab Toggle */}
        <div className="flex border-b border-cream-border mb-6">
          <button
            onClick={() => setTab('create')}
            className={`flex-1 py-3 text-sm font-semibold border-b-2 text-center transition ${
              tab === 'create'
                ? 'border-forest text-forest font-bold'
                : 'border-transparent text-brandText-secondary hover:text-forest'
            }`}
          >
            ✨ New Restaurant
          </button>
          <button
            onClick={() => setTab('existing')}
            className={`flex-1 py-3 text-sm font-semibold border-b-2 text-center transition ${
              tab === 'existing'
                ? 'border-forest text-forest font-bold'
                : 'border-transparent text-brandText-secondary hover:text-forest'
            }`}
          >
            📂 Load Existing ({existingRestaurants.length})
          </button>
        </div>

        {tab === 'create' ? (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (name.trim()) createMutation.mutate();
            }}
            className="space-y-4"
          >
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-brandText-secondary mb-1">
                Restaurant Name *
              </label>
              <div className="relative">
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Trattoria Bella, Haldiram's, Barbeque Nation"
                  className="w-full px-3.5 py-2.5 rounded-lg border border-cream-border focus:border-forest focus:ring-1 focus:ring-forest outline-hidden text-sm bg-white"
                />
              </div>

              {/* Suggestions */}
              {suggestions.length > 0 && (
                <div className="mt-2 p-2 bg-cream rounded-lg border border-cream-border text-xs">
                  <span className="text-[11px] font-bold text-brandText-secondary uppercase tracking-wider block mb-1">
                    Suggestions:
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {suggestions.map((s, idx) => (
                      <button
                        key={idx}
                        type="button"
                        onClick={() => setName(s.name)}
                        className="px-2.5 py-1 rounded-md bg-white border border-cream-border hover:border-forest text-brandText-primary font-medium text-xs transition"
                      >
                        {s.name}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-brandText-secondary mb-1">
                  City
                </label>
                <input
                  type="text"
                  value={city}
                  onChange={(e) => setCity(e.target.value)}
                  placeholder="e.g. Mumbai, New York"
                  className="w-full px-3.5 py-2.5 rounded-lg border border-cream-border focus:border-forest focus:ring-1 focus:ring-forest outline-hidden text-sm bg-white"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-brandText-secondary mb-1">
                  Cuisine / Category
                </label>
                <input
                  type="text"
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  placeholder="e.g. Italian, Casual Dining"
                  className="w-full px-3.5 py-2.5 rounded-lg border border-cream-border focus:border-forest focus:ring-1 focus:ring-forest outline-hidden text-sm bg-white"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-brandText-secondary mb-1">
                  Neighborhood / Location
                </label>
                <input
                  type="text"
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                  placeholder="e.g. Downtown, Bandra West"
                  className="w-full px-3.5 py-2.5 rounded-lg border border-cream-border focus:border-forest focus:ring-1 focus:ring-forest outline-hidden text-sm bg-white"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-brandText-secondary mb-1">
                  Website (Optional)
                </label>
                <input
                  type="text"
                  value={website}
                  onChange={(e) => setWebsite(e.target.value)}
                  placeholder="https://..."
                  className="w-full px-3.5 py-2.5 rounded-lg border border-cream-border focus:border-forest focus:ring-1 focus:ring-forest outline-hidden text-sm bg-white"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={createMutation.isPending || !name.trim()}
              className="w-full mt-6 flex items-center justify-center gap-2 py-3 rounded-xl bg-forest hover:bg-forest-light text-white font-bold text-sm transition shadow-card disabled:opacity-50"
            >
              {createMutation.isPending ? 'Setting up Profile...' : 'Create & Proceed to Data Upload'}
              <ArrowRight className="w-4 h-4 text-amber" />
            </button>
          </form>
        ) : (
          <div className="space-y-4">
            {existingRestaurants.length === 0 ? (
              <div className="text-center py-8 text-brandText-secondary text-sm">
                No existing restaurants found. Please use the New Restaurant tab.
              </div>
            ) : (
              <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
                {existingRestaurants.map((rest) => (
                  <div
                    key={rest.id}
                    onClick={() => setSelectedExistingId(rest.id)}
                    className={`p-3.5 rounded-xl border cursor-pointer transition flex items-center justify-between ${
                      selectedExistingId === rest.id
                        ? 'border-forest bg-forest-muted'
                        : 'border-cream-border hover:border-forest/40 bg-white'
                    }`}
                  >
                    <div>
                      <h4 className="font-bold text-sm text-forest-dark">{rest.name}</h4>
                      <p className="text-xs text-brandText-secondary mt-0.5">
                        {rest.category || 'Restaurant'} · {rest.city || 'No location'}
                      </p>
                    </div>
                    {selectedExistingId === rest.id && (
                      <CheckCircle2 className="w-5 h-5 text-forest" />
                    )}
                  </div>
                ))}
              </div>
            )}

            {existingRestaurants.length > 0 && (
              <button
                type="button"
                onClick={() => selectedExistingId && selectExistingMutation.mutate(selectedExistingId)}
                disabled={!selectedExistingId || selectExistingMutation.isPending}
                className="w-full mt-6 flex items-center justify-center gap-2 py-3 rounded-xl bg-forest hover:bg-forest-light text-white font-bold text-sm transition shadow-card disabled:opacity-50"
              >
                {selectExistingMutation.isPending ? 'Loading Venue...' : 'Load Workspace'}
                <ArrowRight className="w-4 h-4 text-amber" />
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default OnboardingPage;
