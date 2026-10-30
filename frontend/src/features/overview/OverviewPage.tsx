import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
  DollarSign,
  ShoppingBag,
  Receipt,
  Utensils,
  Trophy,
  Sparkles,
  ArrowRight,
  UploadCloud,
  CheckCircle2,
  AlertTriangle,
  HelpCircle,
  TrendingUp,
} from 'lucide-react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  PieChart,
  Pie,
  Cell,
  Legend,
} from 'recharts';
import { useAppStore } from '../../store';
import { fetchAnalyticsSummary } from '../../api/analytics';
import { fetchRecommendations } from '../../api/recommendations';
import { fetchExperiments } from '../../api/experiments';
import { fetchWasteSummary } from '../../api/waste';
import { MetricCard } from '../../components/common/MetricCard';

const CATEGORY_COLORS = ['#183B32', '#24483E', '#D97757', '#D6A64F', '#437A6D', '#A55D46'];

export const OverviewPage: React.FC = () => {
  const navigate = useNavigate();
  const { activeRestaurant, activeRun } = useAppStore();
  const runId = activeRun?.id;

  // Analytics summary query
  const { data: analytics, isLoading: analyticsLoading } = useQuery({
    queryKey: ['analyticsSummary', runId],
    queryFn: () => (runId ? fetchAnalyticsSummary(runId) : null),
    enabled: !!runId,
  });

  // Recommendations query
  const { data: recommendations = [] } = useQuery({
    queryKey: ['recommendations', runId],
    queryFn: () => (runId ? fetchRecommendations(runId) : Promise.resolve([])),
    enabled: !!runId,
  });

  // Experiments query
  const { data: experiments = [] } = useQuery({
    queryKey: ['experiments', runId],
    queryFn: () => (runId ? fetchExperiments(runId) : Promise.resolve([])),
    enabled: !!runId,
  });

  // Waste summary query
  const { data: waste } = useQuery({
    queryKey: ['wasteSummary', runId],
    queryFn: () => (runId ? fetchWasteSummary(runId) : null),
    enabled: !!runId,
  });

  const summary = analytics?.summary;
  const avgTicket =
    summary && summary.total_units > 0
      ? summary.total_revenue / summary.total_units
      : 0;

  const topItemName = summary?.top_items?.[0]?.item_name || '—';

  // Format category pie data
  const categoryData =
    analytics?.category_shares?.map((cat) => ({
      name: cat.category,
      value: cat.revenue,
      units: cat.units,
    })) || [];

  const pendingApprovalsCount = recommendations.filter(
    (r) => !r.approval || r.approval.decision === 'saved_for_later'
  ).length;
  const approvedCount = recommendations.filter(
    (r) => r.approval?.decision === 'approved'
  ).length;

  return (
    <div className="space-y-6">
      {/* Page Title & Context Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold font-display text-forest-dark">
            Restaurant Overview
          </h1>
          <p className="text-xs text-brandText-secondary mt-0.5">
            Your restaurant's financial performance and AI menu intelligence at a glance.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => navigate('/upload')}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-cream-border bg-white hover:border-forest text-xs font-semibold text-brandText-primary transition"
          >
            <UploadCloud className="w-3.5 h-3.5 text-forest" />
            Manage Datasets
          </button>
          <button
            onClick={() => navigate('/recommendations')}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-forest hover:bg-forest-light text-white text-xs font-bold transition shadow-xs"
          >
            <Sparkles className="w-3.5 h-3.5 text-amber" />
            View Recommendations ({recommendations.length})
          </button>
        </div>
      </div>

      {/* 5 KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
        <MetricCard
          label="Total Revenue"
          value={summary ? `₹${summary.total_revenue.toLocaleString('en-IN')}` : '₹0'}
          subValue={summary?.period_start ? `${summary.period_start} → ${summary.period_end}` : 'No date range'}
          icon={DollarSign}
        />
        <MetricCard
          label="Units Sold"
          value={summary ? summary.total_units.toLocaleString('en-IN') : '0'}
          subValue="Total volume served"
          icon={ShoppingBag}
        />
        <MetricCard
          label="Average Ticket"
          value={avgTicket ? `₹${avgTicket.toFixed(2)}` : '—'}
          subValue="Revenue per unit sold"
          icon={Receipt}
        />
        <MetricCard
          label="Menu Items"
          value={summary ? summary.item_count : 0}
          subValue="Active menu catalog"
          icon={Utensils}
        />
        <MetricCard
          label="Top Performing Item"
          value={topItemName}
          subValue={summary?.top_items?.[0] ? `₹${summary.top_items[0].total_revenue.toLocaleString('en-IN')} rev` : 'Awaiting data'}
          icon={Trophy}
          badge="Lead Item"
          badgeColor="green"
        />
      </div>

      {/* Charts Section: 2 Columns */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Revenue Trend Over Time */}
        <div className="lg:col-span-2 bg-cream-card rounded-card border border-cream-border p-6 shadow-card">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="font-bold font-display text-sm text-forest-dark">
                Revenue Trajectory
              </h3>
              <p className="text-xs text-brandText-secondary">
                Daily sales with 7-day smoothed rolling average
              </p>
            </div>
            <button
              onClick={() => navigate('/analytics')}
              className="text-xs text-forest hover:text-forest-light font-semibold flex items-center gap-1"
            >
              Full Analytics <ArrowRight className="w-3 h-3" />
            </button>
          </div>

          <div className="h-64 w-full">
            {analytics?.daily_trends && analytics.daily_trends.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={analytics.daily_trends}>
                  <defs>
                    <linearGradient id="revGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#183B32" stopOpacity={0.25} />
                      <stop offset="95%" stopColor="#183B32" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E8E5DD" />
                  <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#7A817B' }} tickLine={false} />
                  <YAxis
                    tick={{ fontSize: 11, fill: '#7A817B' }}
                    tickLine={false}
                    tickFormatter={(val) => `₹${val}`}
                  />
                  <Tooltip
                    formatter={(val: any) => [`₹${Number(val).toLocaleString('en-IN')}`, 'Revenue']}
                    labelStyle={{ color: '#183B32', fontWeight: 'bold' }}
                    contentStyle={{ backgroundColor: '#FFFFFF', borderRadius: '10px', borderColor: '#E8E5DD' }}
                  />
                  <Area
                    type="monotone"
                    dataKey="revenue"
                    stroke="#183B32"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#revGrad)"
                    name="Daily Revenue"
                  />
                  <Area
                    type="monotone"
                    dataKey="rolling_7d"
                    stroke="#D97757"
                    strokeWidth={2}
                    strokeDasharray="4 4"
                    fill="none"
                    name="7d Avg"
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-brandText-secondary text-xs">
                <TrendingUp className="w-8 h-8 mb-2 text-forest/30" />
                No daily sales trends recorded yet. Upload a sales dataset to visualize.
              </div>
            )}
          </div>
        </div>

        {/* Right 1 Col: Category Shares Donut */}
        <div className="bg-cream-card rounded-card border border-cream-border p-6 shadow-card">
          <h3 className="font-bold font-display text-sm text-forest-dark mb-1">
            Category Contribution
          </h3>
          <p className="text-xs text-brandText-secondary mb-4">
            Revenue breakdown across cuisine sections
          </p>

          <div className="h-64 w-full">
            {categoryData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={categoryData}
                    cx="50%"
                    cy="45%"
                    innerRadius={50}
                    outerRadius={75}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {categoryData.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={CATEGORY_COLORS[index % CATEGORY_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(val: any) => [`₹${Number(val).toLocaleString('en-IN')}`, 'Revenue']}
                    contentStyle={{ backgroundColor: '#FFFFFF', borderRadius: '8px', borderColor: '#E8E5DD' }}
                  />
                  <Legend
                    layout="horizontal"
                    verticalAlign="bottom"
                    align="center"
                    iconSize={8}
                    wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-brandText-secondary text-xs">
                <Utensils className="w-8 h-8 mb-2 text-forest/30" />
                No category data available.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* AI Intelligence Summary & Data Readiness Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* AI Recommendations & Strategy Snapshot */}
        <div className="bg-cream-card rounded-card border border-cream-border p-6 shadow-card">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-amber" />
              <h3 className="font-bold font-display text-sm text-forest-dark">
                Agentic Intelligence Summary
              </h3>
            </div>
            <button
              onClick={() => navigate('/recommendations')}
              className="text-xs text-forest hover:text-forest-light font-semibold"
            >
              Review Queue →
            </button>
          </div>

          <div className="grid grid-cols-3 gap-3 mb-4">
            <div className="p-3 rounded-xl bg-cream border border-cream-border text-center">
              <span className="text-[10px] uppercase font-bold text-brandText-secondary block">
                Total Recs
              </span>
              <span className="text-xl font-bold font-display text-forest-dark">
                {recommendations.length}
              </span>
            </div>
            <div className="p-3 rounded-xl bg-amber-light border border-amber/30 text-center">
              <span className="text-[10px] uppercase font-bold text-amber-dark block">
                Pending Decisions
              </span>
              <span className="text-xl font-bold font-display text-amber-dark">
                {pendingApprovalsCount}
              </span>
            </div>
            <div className="p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-center">
              <span className="text-[10px] uppercase font-bold text-emerald-800 block">
                Approved
              </span>
              <span className="text-xl font-bold font-display text-emerald-800">
                {approvedCount}
              </span>
            </div>
          </div>

          {recommendations.length > 0 ? (
            <div className="space-y-2">
              {recommendations.slice(0, 3).map((rec) => (
                <div
                  key={rec.id}
                  onClick={() => navigate('/recommendations')}
                  className="p-3 rounded-xl border border-cream-border bg-white hover:border-forest/40 cursor-pointer transition flex items-center justify-between"
                >
                  <div>
                    <span className="font-bold text-xs text-forest-dark block">
                      {rec.item_name}
                    </span>
                    <span className="text-[11px] text-brandText-secondary line-clamp-1">
                      {rec.reasoning}
                    </span>
                  </div>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full border bg-forest-muted text-forest uppercase shrink-0">
                    {rec.action}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-4 rounded-xl border border-dashed border-cream-border text-center text-xs text-brandText-secondary">
              No recommendations generated for this run yet. Run AI Analysis to uncover menu optimizations.
            </div>
          )}
        </div>

        {/* Data Readiness & Dataset Status */}
        <div className="bg-cream-card rounded-card border border-cream-border p-6 shadow-card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-bold font-display text-sm text-forest-dark">
              Dataset Availability & Quality
            </h3>
            <span className="text-xs text-brandText-secondary">
              Run #{runId || '—'}
            </span>
          </div>

          <div className="space-y-3">
            {[
              {
                type: 'Menu Dataset',
                key: 'menu' as const,
                required: true,
                desc: 'Item names, categories, selling prices',
              },
              {
                type: 'Sales Orders',
                key: 'sales' as const,
                required: true,
                desc: 'Historical volume sold, transaction revenue',
              },
              {
                type: 'Customer Reviews',
                key: 'reviews' as const,
                required: false,
                desc: 'Customer sentiment & SerpApi web snippets',
              },
              {
                type: 'Ingredient Costs',
                key: 'costs' as const,
                required: false,
                desc: 'Food cost & contribution margin analysis',
              },
            ].map((ds) => {
              const isPresent = activeRun?.datasets?.[ds.key] ?? false;
              return (
                <div
                  key={ds.key}
                  className="p-3 rounded-xl border border-cream-border bg-white flex items-center justify-between"
                >
                  <div className="flex items-center gap-3">
                    {isPresent ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                    ) : ds.required ? (
                      <AlertTriangle className="w-4 h-4 text-terracotta shrink-0" />
                    ) : (
                      <HelpCircle className="w-4 h-4 text-brandText-secondary shrink-0" />
                    )}
                    <div>
                      <span className="text-xs font-bold text-brandText-primary block">
                        {ds.type} {ds.required && <span className="text-terracotta">*</span>}
                      </span>
                      <span className="text-[11px] text-brandText-secondary">
                        {ds.desc}
                      </span>
                    </div>
                  </div>
                  <div>
                    {isPresent ? (
                      <span className="text-[11px] px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 font-semibold border border-emerald-200">
                        Uploaded
                      </span>
                    ) : (
                      <button
                        onClick={() => navigate('/upload')}
                        className="text-[11px] px-2.5 py-1 rounded-md bg-cream hover:bg-forest hover:text-white text-forest font-semibold transition"
                      >
                        Upload
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};

export default OverviewPage;
