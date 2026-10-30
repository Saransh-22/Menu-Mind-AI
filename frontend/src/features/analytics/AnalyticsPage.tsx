import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  DollarSign,
  ShoppingBag,
  Receipt,
  Utensils,
  Trophy,
  Calendar,
  Info,
  TrendingUp,
  ArrowUpRight,
  ArrowDownRight,
  Minus,
} from 'lucide-react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  BarChart,
  Bar,
  Cell,
} from 'recharts';
import { useAppStore } from '../../store';
import { fetchAnalyticsSummary, fetchProfitability } from '../../api/analytics';
import { MetricCard } from '../../components/common/MetricCard';
import { EmptyState } from '../../components/common/EmptyState';

const BAR_COLORS = ['#183B32', '#24483E', '#D97757', '#D6A64F', '#437A6D', '#7A817B'];

export const AnalyticsPage: React.FC = () => {
  const { activeRun } = useAppStore();
  const runId = activeRun?.id;

  const [dateFilter, setDateFilter] = useState<'all' | '7d' | '30d'>('all');

  const { data: analytics, isLoading } = useQuery({
    queryKey: ['analyticsSummary', runId],
    queryFn: () => (runId ? fetchAnalyticsSummary(runId) : null),
    enabled: !!runId,
  });

  const { data: profitability = [] } = useQuery({
    queryKey: ['profitability', runId],
    queryFn: () => (runId ? fetchProfitability(runId) : Promise.resolve([])),
    enabled: !!runId,
  });

  if (!runId) {
    return (
      <EmptyState
        icon={TrendingUp}
        title="No Run Selected"
        description="Please select an active restaurant and analysis run from the header."
      />
    );
  }

  if (isLoading) {
    return (
      <div className="py-20 text-center text-brandText-secondary text-sm">
        Computing deterministic sales analytics...
      </div>
    );
  }

  const summary = analytics?.summary;
  if (!summary) {
    return (
      <EmptyState
        icon={ShoppingBag}
        title="No Sales Data Available"
        description="Upload a sales transactions dataset in Data Upload to generate financial intelligence."
        actionText="Go to Data Upload"
        onAction={() => window.location.href = '/upload'}
      />
    );
  }

  const avgPrice = summary.total_units > 0 ? summary.total_revenue / summary.total_units : 0;
  const bestItem = summary.top_items?.[0];

  // Map profit lookup
  const profitMap = new Map(
    profitability.map((p) => [p.item_name.toLowerCase().trim(), p])
  );

  // Category chart data
  const categoryBarData = (analytics?.category_shares || []).map((c) => ({
    name: c.category,
    revenue: c.revenue,
    units: c.units,
    percentage: c.percentage,
  }));

  // Trend points
  const rawTrends = analytics?.daily_trends || [];
  const trendPoints =
    dateFilter === '7d'
      ? rawTrends.slice(-7)
      : dateFilter === '30d'
      ? rawTrends.slice(-30)
      : rawTrends;

  return (
    <div className="space-y-6">
      {/* Title & Filter Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold font-display text-forest-dark">
            Sales & Revenue Analytics
          </h1>
          <p className="text-xs text-brandText-secondary mt-0.5">
            Deterministic revenue metrics, sales velocities, and item contribution margins.
          </p>
        </div>

        {/* Date Filter Pills */}
        <div className="flex items-center gap-1.5 p-1 rounded-xl bg-cream-card border border-cream-border text-xs">
          <button
            onClick={() => setDateFilter('all')}
            className={`px-3 py-1 rounded-lg font-medium transition ${
              dateFilter === 'all'
                ? 'bg-forest text-white font-bold'
                : 'text-brandText-secondary hover:text-forest'
            }`}
          >
            Full Period
          </button>
          <button
            onClick={() => setDateFilter('30d')}
            className={`px-3 py-1 rounded-lg font-medium transition ${
              dateFilter === '30d'
                ? 'bg-forest text-white font-bold'
                : 'text-brandText-secondary hover:text-forest'
            }`}
          >
            Last 30 Days
          </button>
          <button
            onClick={() => setDateFilter('7d')}
            className={`px-3 py-1 rounded-lg font-medium transition ${
              dateFilter === '7d'
                ? 'bg-forest text-white font-bold'
                : 'text-brandText-secondary hover:text-forest'
            }`}
          >
            Last 7 Days
          </button>
        </div>
      </div>

      {/* 5 KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
        <MetricCard
          label="Total Revenue"
          value={`₹${summary.total_revenue.toLocaleString('en-IN')}`}
          subValue={summary.period_start ? `${summary.period_start} → ${summary.period_end}` : undefined}
          icon={DollarSign}
        />
        <MetricCard
          label="Units Sold"
          value={summary.total_units.toLocaleString('en-IN')}
          subValue="Total volume served"
          icon={ShoppingBag}
        />
        <MetricCard
          label="Avg Unit Price"
          value={`₹${avgPrice.toFixed(2)}`}
          subValue="Revenue / Units"
          icon={Receipt}
        />
        <MetricCard
          label="Active Menu Items"
          value={summary.item_count}
          subValue="Identified in sales"
          icon={Utensils}
        />
        <MetricCard
          label="Best-Selling Dish"
          value={bestItem?.item_name || '—'}
          subValue={bestItem ? `₹${bestItem.total_revenue.toLocaleString('en-IN')} rev` : undefined}
          icon={Trophy}
          badge="Top Rank"
          badgeColor="green"
        />
      </div>

      {/* Revenue Trend Over Time */}
      <div className="bg-cream-card rounded-card border border-cream-border p-6 shadow-card">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="font-bold font-display text-sm text-forest-dark">
              Daily Revenue Trajectory
            </h3>
            <p className="text-xs text-brandText-secondary">
              Daily revenue receipts with 7-day smoothed trendline
            </p>
          </div>
          <span className="text-xs font-mono text-brandText-secondary">
            {trendPoints.length} points plotted
          </span>
        </div>

        <div className="h-64 w-full">
          {trendPoints.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trendPoints}>
                <defs>
                  <linearGradient id="areaRev" x1="0" y1="0" x2="0" y2="1">
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
                  contentStyle={{ backgroundColor: '#FFFFFF', borderRadius: '8px', borderColor: '#E8E5DD' }}
                />
                <Area
                  type="monotone"
                  dataKey="revenue"
                  stroke="#183B32"
                  strokeWidth={2}
                  fill="url(#areaRev)"
                  name="Daily Revenue"
                />
                <Area
                  type="monotone"
                  dataKey="rolling_7d"
                  stroke="#D97757"
                  strokeWidth={2}
                  strokeDasharray="4 4"
                  fill="none"
                  name="7-day Rolling Avg"
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-full flex items-center justify-center text-xs text-brandText-secondary">
              No revenue data points available for the selected period.
            </div>
          )}
        </div>
      </div>

      {/* Category Performance Bar Chart */}
      <div className="bg-cream-card rounded-card border border-cream-border p-6 shadow-card">
        <h3 className="font-bold font-display text-sm text-forest-dark mb-1">
          Revenue by Category
        </h3>
        <p className="text-xs text-brandText-secondary mb-4">
          Contribution across sections
        </p>

        <div className="h-60 w-full">
          {categoryBarData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={categoryBarData} layout="vertical" margin={{ left: 40, right: 20 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#E8E5DD" />
                <XAxis
                  type="number"
                  tick={{ fontSize: 11, fill: '#7A817B' }}
                  tickFormatter={(val) => `₹${val}`}
                />
                <YAxis dataKey="name" type="category" tick={{ fontSize: 11, fill: '#183B32', fontWeight: 600 }} />
                <Tooltip
                  formatter={(val: any) => [`₹${Number(val).toLocaleString('en-IN')}`, 'Revenue']}
                  contentStyle={{ backgroundColor: '#FFFFFF', borderRadius: '8px', borderColor: '#E8E5DD' }}
                />
                <Bar dataKey="revenue" radius={[0, 6, 6, 0]}>
                  {categoryBarData.map((_, index) => (
                    <Cell key={`bar-${index}`} fill={BAR_COLORS[index % BAR_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-full flex items-center justify-center text-xs text-brandText-secondary">
              No categories mapped.
            </div>
          )}
        </div>
      </div>

      {/* Item Performance & Profitability Table */}
      <div className="bg-cream-card rounded-card border border-cream-border p-6 shadow-card">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="font-bold font-display text-sm text-forest-dark">
              Menu Item Performance & Contribution Margins
            </h3>
            <p className="text-xs text-brandText-secondary">
              Ranked breakdown of sales, pricing, and margin profitability
            </p>
          </div>
          {profitability.length === 0 && (
            <span className="text-[11px] text-amber-dark bg-amber-light border border-amber/30 px-2.5 py-1 rounded-lg flex items-center gap-1">
              <Info className="w-3.5 h-3.5" />
              Upload costs.csv to unlock item contribution margins
            </span>
          )}
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-cream text-forest font-semibold uppercase text-[10px] tracking-wider border-b border-cream-border">
              <tr>
                <th className="px-3.5 py-2.5">Rank</th>
                <th className="px-3.5 py-2.5">Item Name</th>
                <th className="px-3.5 py-2.5">Category</th>
                <th className="px-3.5 py-2.5 text-right">Units Sold</th>
                <th className="px-3.5 py-2.5 text-right">Revenue</th>
                <th className="px-3.5 py-2.5 text-right">Selling Price</th>
                <th className="px-3.5 py-2.5 text-right">Margin / Unit</th>
                <th className="px-3.5 py-2.5 text-right">Margin %</th>
                <th className="px-3.5 py-2.5 text-center">Trend</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-cream-border">
              {summary.top_items.map((item, idx) => {
                const profit = profitMap.get(item.item_name.toLowerCase().trim());
                return (
                  <tr key={idx} className="hover:bg-cream/40 transition">
                    <td className="px-3.5 py-2.5 font-bold font-mono text-brandText-secondary">
                      #{item.sales_rank || idx + 1}
                    </td>
                    <td className="px-3.5 py-2.5 font-bold text-forest-dark">
                      {item.item_name}
                    </td>
                    <td className="px-3.5 py-2.5 text-brandText-secondary">
                      {item.category || 'Other'}
                    </td>
                    <td className="px-3.5 py-2.5 text-right font-mono tabular-nums font-semibold">
                      {item.total_quantity}
                    </td>
                    <td className="px-3.5 py-2.5 text-right font-mono tabular-nums font-bold text-forest">
                      ₹{item.total_revenue.toLocaleString('en-IN')}
                    </td>
                    <td className="px-3.5 py-2.5 text-right font-mono tabular-nums text-brandText-secondary">
                      {item.avg_price ? `₹${item.avg_price.toFixed(2)}` : '—'}
                    </td>
                    <td className="px-3.5 py-2.5 text-right font-mono tabular-nums">
                      {profit?.calculable && profit.contribution_margin !== undefined ? (
                        <span className={profit.contribution_margin >= 0 ? 'text-emerald-700 font-semibold' : 'text-terracotta font-semibold'}>
                          ₹{profit.contribution_margin.toFixed(2)}
                        </span>
                      ) : (
                        <span className="text-brandText-secondary text-[11px]">—</span>
                      )}
                    </td>
                    <td className="px-3.5 py-2.5 text-right font-mono tabular-nums">
                      {profit?.calculable && profit.margin_pct !== undefined ? (
                        <span className="font-bold text-emerald-800 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200">
                          {profit.margin_pct.toFixed(1)}%
                        </span>
                      ) : (
                        <span className="text-brandText-secondary text-[11px]">No cost</span>
                      )}
                    </td>
                    <td className="px-3.5 py-2.5 text-center">
                      {item.period_trend === 'growing' ? (
                        <span className="inline-flex items-center gap-0.5 text-emerald-700 font-semibold text-[11px]">
                          <ArrowUpRight className="w-3.5 h-3.5" /> Growing
                        </span>
                      ) : item.period_trend === 'declining' ? (
                        <span className="inline-flex items-center gap-0.5 text-terracotta font-semibold text-[11px]">
                          <ArrowDownRight className="w-3.5 h-3.5" /> Declining
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-0.5 text-brandText-secondary text-[11px]">
                          <Minus className="w-3 h-3" /> Stable
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default AnalyticsPage;
