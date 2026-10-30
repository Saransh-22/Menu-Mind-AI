import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Trash2,
  Camera,
  AlertTriangle,
  DollarSign,
  TrendingDown,
  UploadCloud,
  CheckCircle2,
  Plus,
  RefreshCw,
  Info,
  ShieldCheck,
  Eye,
  Bot,
} from 'lucide-react';
import { useAppStore } from '../../store';
import {
  fetchWasteSummary,
  recordWasteEntry,
  analyzeFoodImage,
} from '../../api/waste';
import MetricCard from '../../components/common/MetricCard';
import EmptyState from '../../components/common/EmptyState';
import { formatCurrency } from '../../utils/currency';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';

export default function FoodWastePage() {
  const { activeRun, openAssistantWithContext } = useAppStore();
  const queryClient = useQueryClient();

  const [activeTab, setActiveTab] = useState<'measured' | 'spoilage'>('measured');
  const [selectedImage, setSelectedImage] = useState<File | null>(null);
  const [visionResults, setVisionResults] = useState<{
    items: { name: string; state: string; confidence: number; visual_notes: string }[];
    image_limitations: string[];
  } | null>(null);

  // Manual Waste Entry Form State
  const [ingredientName, setIngredientName] = useState('');
  const [quantity, setQuantity] = useState<number>(1);
  const [unit, setUnit] = useState('kg');
  const [unitCost, setUnitCost] = useState<number>(0);
  const [wasteReason, setWasteReason] = useState('spoilage');
  const [associatedDish, setAssociatedDish] = useState('');

  const runId = activeRun?.id;

  const {
    data: wasteData,
    isLoading,
  } = useQuery({
    queryKey: ['wasteSummary', runId],
    queryFn: () => (runId ? fetchWasteSummary(runId) : null),
    enabled: !!runId,
  });

  const recordMutation = useMutation({
    mutationFn: (payload: {
      ingredient_name: string;
      quantity: number;
      unit: string;
      unit_cost: number;
      waste_reason?: string;
      associated_dish?: string;
      image_item_name?: string;
      image_confidence?: number;
      verified_by_user?: boolean;
    }) => {
      if (!runId) return Promise.reject('No run ID');
      return recordWasteEntry(runId, payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wasteSummary', runId] });
      // Reset form
      setIngredientName('');
      setQuantity(1);
      setUnitCost(0);
      setAssociatedDish('');
    },
  });

  const visionMutation = useMutation({
    mutationFn: (file: File) => {
      if (!runId) return Promise.reject('No run ID');
      return analyzeFoodImage(runId, file);
    },
    onSuccess: (data) => {
      setVisionResults(data);
    },
  });

  if (!activeRun) {
    return (
      <EmptyState
        title="No Active Run Selected"
        description="Select an active restaurant run to view waste analytics and Gemini Vision dish inspection."
      />
    );
  }

  const measured = wasteData?.measured;
  const spoilage = wasteData?.spoilage;
  const records = wasteData?.records || [];

  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedImage(file);
      visionMutation.mutate(file);
    }
  };

  const handleUseVisionItem = (item: { name: string; state: string; confidence: number }) => {
    setIngredientName(item.name);
    setWasteReason(item.state.toLowerCase().includes('trim') ? 'prep_trim' : 'spoilage');
  };

  // Measured by ingredient chart data
  const ingredientWasteData = measured?.by_ingredient
    ? Object.entries(measured.by_ingredient).map(([name, cost]) => ({
        name,
        cost: Number(cost.toFixed(2)),
      }))
    : [];

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-stone-900 font-serif">Food Waste Intelligence</h1>
          <p className="text-sm text-stone-500">
            Physical kitchen waste logging, Gemini Vision image identification, and predictive spoilage exposure.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={() =>
              openAssistantWithContext(
                `Act as the Operations & Waste specialist. Review our kitchen waste records and slow-moving items at high risk of spoilage. What operational adjustments and specials can reduce waste?`
              )
            }
            className="flex items-center gap-2 rounded-lg bg-emerald-600 px-3.5 py-2 text-xs font-semibold text-white hover:bg-emerald-700 shadow-2xs transition"
          >
            <Bot className="h-4 w-4" />
            Ask AI About Waste Reduction
          </button>

          {/* Tab Switcher */}
          <div className="flex rounded-lg border border-stone-200 bg-white p-1">
            <button
              onClick={() => setActiveTab('measured')}
              className={`rounded-md px-3 py-1.5 text-xs font-semibold transition-colors ${
                activeTab === 'measured'
                  ? 'bg-forest text-cream'
                  : 'text-stone-600 hover:text-stone-900'
              }`}
            >
              Measured Waste & Vision
            </button>
            <button
              onClick={() => setActiveTab('spoilage')}
              className={`rounded-md px-3 py-1.5 text-xs font-semibold transition-colors ${
                activeTab === 'spoilage'
                  ? 'bg-forest text-cream'
                  : 'text-stone-600 hover:text-stone-900'
              }`}
            >
              Predictive Spoilage Risk
            </button>
          </div>
        </div>
      </div>

      {activeTab === 'measured' ? (
        <>
          {/* KPI Cards */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <MetricCard
              title="Measured Waste Cost"
              value={formatCurrency(measured?.total_waste_cost || 0)}
              icon={<DollarSign className="h-5 w-5 text-terracotta" />}
              status="negative"
              subtext={`${measured?.calculable_records || 0} items with costed units`}
            />
            <MetricCard
              title="Logged Incidents"
              value={records.length}
              icon={<Trash2 className="h-5 w-5 text-stone-500" />}
              subtext={`${measured?.uncalculable_records || 0} uncosted items`}
            />
            <MetricCard
              title="Weekly Spoilage Exposure"
              value={formatCurrency(spoilage?.total_weekly_exposure || 0)}
              icon={<TrendingDown className="h-5 w-5 text-amber" />}
              status="warning"
              subtext="At-risk slow-moving inventory"
            />
            <MetricCard
              title="High Risk Menu Items"
              value={spoilage?.high_risk_count || 0}
              icon={<AlertTriangle className="h-5 w-5 text-terracotta" />}
              status={spoilage?.high_risk_count ? 'negative' : 'positive'}
              subtext="Low sales velocity"
            />
          </div>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            {/* Gemini Vision Identification Section */}
            <div className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm lg:col-span-1">
              <div className="flex items-center gap-2 mb-3">
                <div className="rounded-md bg-forest/10 p-1.5 text-forest">
                  <Camera className="h-4 w-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-stone-900 font-serif">Gemini Vision Food Identifier</h3>
                  <p className="text-[11px] text-stone-500">Scan prep discard or plate waste</p>
                </div>
              </div>

              {/* Upload Drag/Drop Box */}
              <label className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-stone-200 p-6 text-center hover:border-forest/50 hover:bg-forest/[0.02] cursor-pointer transition-colors">
                <UploadCloud className="h-8 w-8 text-stone-400 mb-2" />
                <span className="text-xs font-semibold text-stone-700">Upload kitchen waste photo</span>
                <span className="text-[10px] text-stone-400 mt-1">PNG, JPG or WEBP (Max 10MB)</span>
                <input
                  type="file"
                  accept="image/*"
                  onChange={handleImageUpload}
                  className="hidden"
                />
              </label>

              {visionMutation.isPending && (
                <div className="mt-4 flex items-center justify-center gap-2 text-xs text-forest">
                  <RefreshCw className="h-4 w-4 animate-spin" />
                  <span>Gemini Vision analyzing item composition...</span>
                </div>
              )}

              {/* Vision Results */}
              {visionResults && (
                <div className="mt-4 space-y-2.5">
                  <span className="text-xs font-bold text-stone-800">Detected Food Items:</span>
                  {visionResults.items.map((item, idx) => (
                    <div
                      key={idx}
                      className="rounded-lg border border-stone-200 bg-cream/40 p-2.5 text-xs flex items-center justify-between"
                    >
                      <div>
                        <div className="font-semibold text-stone-900 capitalize">{item.name}</div>
                        <div className="text-[10px] text-stone-500">
                          State: <span className="font-medium">{item.state}</span> · Conf:{' '}
                          {(item.confidence * 100).toFixed(0)}%
                        </div>
                      </div>
                      <button
                        onClick={() => handleUseVisionItem(item)}
                        className="rounded bg-forest/10 px-2 py-1 text-[11px] font-semibold text-forest hover:bg-forest hover:text-cream transition-colors"
                      >
                        Fill Form
                      </button>
                    </div>
                  ))}

                  {visionResults.image_limitations?.length > 0 && (
                    <div className="text-[10px] text-stone-400 italic">
                      Note: {visionResults.image_limitations.join(' ')}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Manual / Verified Waste Form */}
            <div className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm lg:col-span-2">
              <div className="flex items-center gap-2 mb-3">
                <div className="rounded-md bg-forest/10 p-1.5 text-forest">
                  <Plus className="h-4 w-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-stone-900 font-serif">Log Waste Incident</h3>
                  <p className="text-[11px] text-stone-500">
                    Deterministic cost recording verified with kitchen weight and supplier price
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-stone-700">Ingredient / Item *</label>
                  <input
                    type="text"
                    placeholder="e.g. Avocado, Salmon Fillet, Sourdough"
                    value={ingredientName}
                    onChange={(e) => setIngredientName(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-stone-200 px-3 py-1.5 text-xs focus:border-forest focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-stone-700">Associated Dish</label>
                  <input
                    type="text"
                    placeholder="e.g. Avocado Toast, Grilled Salmon"
                    value={associatedDish}
                    onChange={(e) => setAssociatedDish(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-stone-200 px-3 py-1.5 text-xs focus:border-forest focus:outline-none"
                  />
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="block text-xs font-semibold text-stone-700">Quantity</label>
                    <input
                      type="number"
                      step="0.1"
                      value={quantity}
                      onChange={(e) => setQuantity(parseFloat(e.target.value) || 0)}
                      className="mt-1 w-full rounded-lg border border-stone-200 px-3 py-1.5 text-xs focus:border-forest focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-stone-700">Unit</label>
                    <select
                      value={unit}
                      onChange={(e) => setUnit(e.target.value)}
                      className="mt-1 w-full rounded-lg border border-stone-200 px-3 py-1.5 text-xs focus:border-forest focus:outline-none"
                    >
                      <option value="kg">kg</option>
                      <option value="lbs">lbs</option>
                      <option value="portions">portions</option>
                      <option value="units">units</option>
                      <option value="liters">liters</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-stone-700">Unit Cost</label>
                  <input
                    type="number"
                    step="0.01"
                    placeholder="0.00"
                    value={unitCost}
                    onChange={(e) => setUnitCost(parseFloat(e.target.value) || 0)}
                    className="mt-1 w-full rounded-lg border border-stone-200 px-3 py-1.5 text-xs focus:border-forest focus:outline-none"
                  />
                </div>

                <div className="sm:col-span-2">
                  <label className="block text-xs font-semibold text-stone-700">Reason for Waste</label>
                  <select
                    value={wasteReason}
                    onChange={(e) => setWasteReason(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-stone-200 px-3 py-1.5 text-xs focus:border-forest focus:outline-none"
                  >
                    <option value="spoilage">Spoilage / Expiration</option>
                    <option value="prep_trim">Prep Trim / Over-peeling</option>
                    <option value="overcooked">Kitchen Mistake / Overcooked</option>
                    <option value="customer_return">Customer Return / Plate Waste</option>
                  </select>
                </div>
              </div>

              <div className="mt-4 flex items-center justify-between border-t border-stone-100 pt-3">
                <div className="text-xs text-stone-600">
                  Calculated Cost:{' '}
                  <span className="font-bold text-stone-900">
                    {formatCurrency(quantity * unitCost)}
                  </span>
                </div>
                <button
                  onClick={() =>
                    recordMutation.mutate({
                      ingredient_name: ingredientName,
                      quantity,
                      unit,
                      unit_cost: unitCost,
                      waste_reason: wasteReason,
                      associated_dish: associatedDish,
                      verified_by_user: true,
                    })
                  }
                  disabled={!ingredientName.trim() || recordMutation.isPending}
                  className="rounded-lg bg-forest px-4 py-2 text-xs font-semibold text-cream hover:bg-forest-secondary disabled:opacity-50"
                >
                  {recordMutation.isPending ? 'Logging...' : 'Log Verified Waste'}
                </button>
              </div>
            </div>
          </div>

          {/* Waste History Table */}
          <div className="rounded-xl border border-stone-200 bg-white p-6 shadow-sm">
            <h3 className="text-base font-semibold text-stone-900 font-serif mb-4">
              Physical Waste Audit Log
            </h3>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-stone-200 text-left text-xs">
                <thead className="bg-stone-50 text-stone-600 font-semibold uppercase tracking-wider">
                  <tr>
                    <th className="py-3 px-4">Date</th>
                    <th className="py-3 px-4">Ingredient</th>
                    <th className="py-3 px-4">Quantity</th>
                    <th className="py-3 px-4">Unit Cost</th>
                    <th className="py-3 px-4">Total Cost</th>
                    <th className="py-3 px-4">Reason</th>
                    <th className="py-3 px-4">Dish</th>
                    <th className="py-3 px-4">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-stone-100 bg-white">
                  {records.length > 0 ? (
                    records.map((rec, idx) => (
                      <tr key={idx} className="hover:bg-cream/40">
                        <td className="py-3 px-4 text-stone-500">
                          {rec.created_at ? new Date(rec.created_at).toLocaleDateString() : 'Recent'}
                        </td>
                        <td className="py-3 px-4 font-semibold text-stone-900">{rec.ingredient_name}</td>
                        <td className="py-3 px-4 text-stone-700">
                          {rec.quantity} {rec.unit}
                        </td>
                        <td className="py-3 px-4 text-stone-700">{formatCurrency(rec.unit_cost)}</td>
                        <td className="py-3 px-4 font-bold text-terracotta">
                          {formatCurrency(rec.quantity * rec.unit_cost)}
                        </td>
                        <td className="py-3 px-4 capitalize text-stone-600">
                          {rec.waste_reason?.replace('_', ' ') || 'N/A'}
                        </td>
                        <td className="py-3 px-4 text-stone-600">{rec.associated_dish || '—'}</td>
                        <td className="py-3 px-4">
                          <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-forest">
                            <ShieldCheck className="h-3 w-3" />
                            Verified
                          </span>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={8} className="py-8 text-center text-stone-400">
                        No physical waste incidents recorded yet for this run.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      ) : (
        /* Predictive Spoilage Risk View */
        <div className="space-y-6">
          <div className="rounded-xl border border-stone-200 bg-white p-6 shadow-sm">
            <div className="mb-4">
              <h2 className="text-base font-semibold text-stone-900 font-serif">
                Predictive Spoilage & Low-Velocity Exposure
              </h2>
              <p className="text-xs text-stone-500">
                Identifies menu items whose low consumption speed exposes inventory to expiration and trim waste.
              </p>
            </div>

            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-stone-200 text-left text-xs">
                <thead className="bg-stone-50 text-stone-600 font-semibold uppercase tracking-wider">
                  <tr>
                    <th className="py-3 px-4">Dish Name</th>
                    <th className="py-3 px-4">Units Sold</th>
                    <th className="py-3 px-4">Daily Velocity</th>
                    <th className="py-3 px-4">Unit Cost</th>
                    <th className="py-3 px-4">Est. Weekly Exposure</th>
                    <th className="py-3 px-4">Risk Level</th>
                    <th className="py-3 px-4">Suggested Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-stone-100 bg-white">
                  {spoilage?.slow_moving_items && spoilage.slow_moving_items.length > 0 ? (
                    spoilage.slow_moving_items.map((item, idx) => (
                      <tr key={idx} className="hover:bg-cream/40">
                        <td className="py-3 px-4 font-semibold text-stone-900">{item.item_name}</td>
                        <td className="py-3 px-4 text-stone-700">{item.units_sold}</td>
                        <td className="py-3 px-4 text-stone-700">{item.daily_velocity.toFixed(2)} / day</td>
                        <td className="py-3 px-4 text-stone-700">{formatCurrency(item.unit_cost)}</td>
                        <td className="py-3 px-4 font-bold text-terracotta">
                          {formatCurrency(item.weekly_exposure)}
                        </td>
                        <td className="py-3 px-4">
                          <span
                            className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${
                              item.risk_level === 'High'
                                ? 'bg-terracotta/10 text-terracotta'
                                : item.risk_level === 'Medium'
                                ? 'bg-amber/10 text-amber'
                                : 'bg-forest/10 text-forest'
                            }`}
                          >
                            {item.risk_level}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-stone-600 font-medium">
                          {item.suggested_action}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={7} className="py-8 text-center text-stone-400">
                        No high spoilage risks detected for current sales velocities.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Kitchen Action Items */}
          {spoilage?.action_items && spoilage.action_items.length > 0 && (
            <div className="rounded-xl border border-forest/20 bg-forest/5 p-5">
              <h3 className="text-sm font-bold text-forest uppercase tracking-wider mb-2">
                Operational Waste Mitigation Recommendations
              </h3>
              <ul className="space-y-2">
                {spoilage.action_items.map((action, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-xs text-stone-700">
                    <CheckCircle2 className="h-4 w-4 text-forest shrink-0 mt-0.5" />
                    <span>{action}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
