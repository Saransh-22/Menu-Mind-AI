import React, { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
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
  Search,
  Download,
  Filter,
  Bot,
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
import { formatCurrency } from '../../utils/currency';

const BAR_COLORS = ['#183B32', '#24483E', '#D97757', '#D6A64F', '#437A6D', '#7A817B'];

export const AnalyticsPage: React.FC = () => {
  const { activeRun, openAssistantWithContext } = useAppStore();
  const navigate = useNavigate();
  const runId = activeRun?.id;

  const [dateFilter, setDateFilter] = useState<'all' | '7d' | '30d'>('all');
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');
  const [itemSearchQuery, setItemSearchQuery] = useState<string>('');

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

  const summary = analytics?.summary;

  // Trend points
  const rawTrends = analytics?.daily_trends || [];
  const trendPoints = useMemo(() => {
    if (dateFilter === '7d') return rawTrends.slice(-7);
    if (dateFilter === '30d') return rawTrends.slice(-30);
    return rawTrends;
  }, [dateFilter, rawTrends]);

  // Synchronously compute KPIs for the selected period
  const { displayRevenue, displayUnits, displayAvgPrice } = useMemo(() => {
    if (!summary) return { displayRevenue: 0, displayUnits: 0, displayAvgPrice: 0 };
    if (dateFilter === 'all' || rawTrends.length === 0) {
      const avg = summary.total_units > 0 ? summary.total_revenue / summary.total_units : 0;
      return {
        displayRevenue: summary.total_revenue,
        displayUnits: summary.total_units,
        displayAvgPrice: avg,
      };
    }
    const periodRev = trendPoints.reduce((acc, p) => acc + (p.revenue || 0), 0);
    const ratio = summary.total_revenue > 0 ? periodRev / summary.total_revenue : 1;
    const periodUnits = Math.round(summary.total_units * ratio);
    const avg = periodUnits > 0 ? periodRev / periodUnits : 0;
    return {
      displayRevenue: periodRev,
      displayUnits: periodUnits,
      displayAvgPrice: avg,
    };
  }, [summary, dateFilter, trendPoints, rawTrends]);

  // Map profit lookup
  const profitMap = useMemo(() => {
    return new Map(profitability.map((p) => [p.item_name.toLowerCase().trim(), p]));
  }, [profitability]);

  // Unique categories for filter dropdown
  const categoriesList = useMemo(() => {
    if (!summary?.top_items) return [];
    const set = new Set<string>();
    summary.top_items.forEach((it) => {
      if (it.category) set.add(it.category);
    });
    return Array.from(set);
  }, [summary]);

  // Filtered items
  const filteredItems = useMemo(() => {
    if (!summary?.top_items) return [];
    return summary.top_items.filter((item) => {
      if (selectedCategory !== 'ALL' && item.category !== selectedCategory) return false;
      if (itemSearchQuery && !item.item_name.toLowerCase().includes(itemSearchQuery.toLowerCase())) {
        return false;
      }
      return true;
    });
  }, [summary, selectedCategory, itemSearchQuery]);

  const handleExportCSV = () => {
    if (!filteredItems.length) return;
    const headers = ['Rank', 'Item Name', 'Category', 'Units Sold', 'Revenue', 'Selling Price', 'Margin Per Unit', 'Margin Pct', 'Trend'];
    const rows = filteredItems.map((item, idx) => {
      const profit = profitMap.get(item.item_name.toLowerCase().trim());
      return [
        item.sales_rank || idx + 1,
        `"${item.item_name}"`,
        `"${item.category || 'Other'}"`,
        item.total_quantity,
        item.total_revenue,
        item.avg_price || 0,
        profit?.contribution_margin !== undefined ? profit.contribution_margin : '',
        profit?.margin_pct !== undefined ? `${profit.margin_pct}%` : '',
        item.period_trend || 'stable',
      ].join(',');
    });
    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `menu_sales_analytics_${dateFilter}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

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

  if (!summary) {
    return (
      <EmptyState
        icon={ShoppingBag}
        title="No Sales Data Available"
        description="Upload a sales transactions dataset in Data Upload to generate financial intelligence."
        actionText="Go to Data Upload"
        onAction={() => navigate('/upload')}
      />
    );
  }

  const bestItem = summary.top_items?.[0];

  // Category chart data
  const categoryBarData = (analytics?.category_shares || []).map((c) => ({
    name: c.category,
    revenue: c.revenue,
    units: c.units,
    percentage: c.percentage,
  }));

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

        <div className="flex items-center gap-2">
          {/* Ask Assistant CTA */}
          <button
            onClick={() =>
              openAssistantWithContext(
                `Analyze our sales and revenue performance for this period. Total revenue is ${formatCurrency(
                  displayRevenue
                )} across ${displayUnits.toLocaleString()} units sold. What patterns stand out?`
              )
            }
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-emerald-300 bg-emerald-50 hover:bg-emerald-100 text-xs font-semibold text-emerald-800 transition"
          >
            <Bot className="w-3.5 h-3.5 text-emerald-600" />
            Ask AI About Sales
          </button>

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
      </div>

      {/* 5 KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
        <MetricCard
          label="Period Revenue"
          value={formatCurrency(displayRevenue)}
          subValue={
            dateFilter === 'all'
              ? summary.period_start
                ? `${summary.period_start} → ${summary.period_end}`
                : undefined
              : `Dynamic for ${dateFilter === '7d' ? 'last 7 days' : 'last 30 days'}`
          }
          icon={DollarSign}
        />
        <MetricCard
          label="Units Sold"
          value={displayUnits.toLocaleString('en-IN')}
          subValue="Total volume served"
          icon={ShoppingBag}
        />
        <MetricCard
          label="Avg Unit Price"
          value={formatCurrency(displayAvgPrice)}
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
          subValue={bestItem ? `${formatCurrency(bestItem.total_revenue)} rev` : undefined}
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
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4">
          <div>
            <h3 className="font-bold font-display text-sm text-forest-dark">
              Menu Item Performance & Contribution Margins
            </h3>
            <p className="text-xs text-brandText-secondary">
              Ranked breakdown of sales, pricing, and margin profitability
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {profitability.length === 0 && (
              <span className="text-[11px] text-amber-dark bg-amber-light border border-amber/30 px-2.5 py-1 rounded-lg flex items-center gap-1">
                <Info className="w-3.5 h-3.5" />
                Upload costs.csv to unlock item contribution margins
              </span>
            )}

            {/* Category Filter */}
            {categoriesList.length > 0 && (
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className="bg-white border border-gray-200 rounded-lg px-2.5 py-1 text-xs text-gray-700 focus:outline-none focus:border-emerald-600"
              >
                <option value="ALL">All Categories</option>
                {categoriesList.map((cat) => (
                  <option key={cat} value={cat}>
                    {cat}
                  </option>
                ))}
              </select>
            )}

            {/* Search Input */}
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-gray-400 absolute left-2.5 top-2" />
              <input
                type="text"
                placeholder="Search dish name..."
                value={itemSearchQuery}
                onChange={(e) => setItemSearchQuery(e.target.value)}
                className="pl-7 pr-3 py-1 bg-white border border-gray-200 rounded-lg text-xs placeholder:text-gray-400 focus:outline-none focus:border-emerald-600"
              />
            </div>

            {/* Export CSV Button */}
            <button
              onClick={handleExportCSV}
              className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg border border-gray-200 bg-white hover:bg-gray-50 text-xs font-semibold text-gray-700 shadow-2xs transition"
              title="Export filtered items to CSV"
            >
              <Download className="w-3.5 h-3.5 text-emerald-600" />
              Export CSV
            </button>
          </div>
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
              {filteredItems.map((item, idx) => {
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
                      {formatCurrency(item.total_revenue)}
                    </td>
                    <td className="px-3.5 py-2.5 text-right font-mono tabular-nums text-brandText-secondary">
                      {item.avg_price ? formatCurrency(item.avg_price) : '—'}
                    </td>
                    <td className="px-3.5 py-2.5 text-right font-mono tabular-nums">
                      {profit?.calculable && profit.contribution_margin !== undefined ? (
                        <span
                          className={
                            profit.contribution_margin >= 0
                              ? 'text-emerald-700 font-semibold'
                              : 'text-terracotta font-semibold'
                          }
                        >
                          {formatCurrency(profit.contribution_margin)}
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
