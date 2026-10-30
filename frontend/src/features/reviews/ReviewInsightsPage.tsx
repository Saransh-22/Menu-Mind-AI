import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  MessageSquare,
  ThumbsUp,
  ThumbsDown,
  Minus,
  Star,
  Globe,
  RefreshCw,
  AlertTriangle,
  Search,
  ExternalLink,
  ChevronRight,
  TrendingUp,
} from 'lucide-react';
import { useAppStore } from '../../store';
import {
  fetchSentimentSummary,
  fetchItemReviewInsights,
  fetchReviewTrends,
  fetchWebReviews,
} from '../../api/reviews';
import MetricCard from '../../components/common/MetricCard';
import EmptyState from '../../components/common/EmptyState';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
  LineChart,
  Line,
} from 'recharts';

export default function ReviewInsightsPage() {
  const { activeRun } = useAppStore();
  const queryClient = useQueryClient();
  const [itemSearch, setItemSearch] = useState('');
  const [retrievalStatus, setRetrievalStatus] = useState<string | null>(null);

  const runId = activeRun?.id;

  const {
    data: sentiment,
    isLoading: loadingSentiment,
    error: sentimentError,
  } = useQuery({
    queryKey: ['sentimentSummary', runId],
    queryFn: () => (runId ? fetchSentimentSummary(runId) : null),
    enabled: !!runId,
  });

  const {
    data: itemInsights,
    isLoading: loadingItems,
  } = useQuery({
    queryKey: ['itemReviewInsights', runId],
    queryFn: () => (runId ? fetchItemReviewInsights(runId) : []),
    enabled: !!runId,
  });

  const {
    data: trends,
    isLoading: loadingTrends,
  } = useQuery({
    queryKey: ['reviewTrends', runId],
    queryFn: () => (runId ? fetchReviewTrends(runId) : []),
    enabled: !!runId,
  });

  const webReviewsMutation = useMutation({
    mutationFn: () => (runId ? fetchWebReviews(runId) : Promise.reject('No run ID')),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['sentimentSummary', runId] });
      queryClient.invalidateQueries({ queryKey: ['itemReviewInsights', runId] });
      queryClient.invalidateQueries({ queryKey: ['reviewTrends', runId] });
      if (data.success) {
        setRetrievalStatus(`Retrieved ${data.reviews_retrieved} external reviews via ${data.source || 'web retrieval'}.`);
      } else {
        setRetrievalStatus(data.error || 'No additional reviews were discovered.');
      }
    },
    onError: (err: any) => {
      setRetrievalStatus(err?.response?.data?.detail || 'Web review retrieval failed.');
    },
  });

  if (!activeRun) {
    return (
      <EmptyState
        title="No Active Run Selected"
        description="Select an active restaurant run to explore customer sentiment and feedback insights."
      />
    );
  }

  if (loadingSentiment || loadingItems || loadingTrends) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <RefreshCw className="h-8 w-8 animate-spin text-forest" />
          <p className="text-sm font-medium text-stone-600">Analyzing customer sentiment and feedback...</p>
        </div>
      </div>
    );
  }

  if (sentimentError || !sentiment || sentiment.review_count === 0) {
    return (
      <EmptyState
        title="No Review Data Available"
        description="Upload customer reviews in CSV format or fetch public reviews using external retrieval."
        action={
          <button
            onClick={() => webReviewsMutation.mutate()}
            disabled={webReviewsMutation.isPending}
            className="flex items-center gap-2 rounded-lg bg-forest px-4 py-2 text-sm font-semibold text-cream hover:bg-forest-secondary disabled:opacity-50"
          >
            {webReviewsMutation.isPending ? (
              <RefreshCw className="h-4 w-4 animate-spin" />
            ) : (
              <Globe className="h-4 w-4" />
            )}
            Fetch External Reviews
          </button>
        }
      />
    );
  }

  // Filter items by search
  const filteredItems = (itemInsights || []).filter((item) =>
    item.item_name.toLowerCase().includes(itemSearch.toLowerCase())
  );

  // Rating distribution data formatting
  const ratingData = [5, 4, 3, 2, 1].map((stars) => ({
    stars: `${stars} ★`,
    count: sentiment.rating_distribution?.[String(stars)] || 0,
  }));

  return (
    <div className="space-y-6">
      {/* Top Action Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-stone-900 font-serif">Customer Sentiment & Reviews</h1>
          <p className="text-sm text-stone-500">
            Synthesized customer feedback, granular item perceptions, and external reputation trends.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => webReviewsMutation.mutate()}
            disabled={webReviewsMutation.isPending}
            className="flex items-center gap-2 rounded-lg border border-forest bg-forest/5 px-4 py-2 text-sm font-semibold text-forest hover:bg-forest hover:text-cream transition-colors disabled:opacity-50"
          >
            {webReviewsMutation.isPending ? (
              <RefreshCw className="h-4 w-4 animate-spin" />
            ) : (
              <Globe className="h-4 w-4" />
            )}
            Fetch External Reviews
          </button>
        </div>
      </div>

      {retrievalStatus && (
        <div className="flex items-center justify-between rounded-lg border border-forest/20 bg-forest/5 p-4 text-sm text-forest">
          <div className="flex items-center gap-2">
            <Globe className="h-4 w-4 shrink-0" />
            <span>{retrievalStatus}</span>
          </div>
          <button
            onClick={() => setRetrievalStatus(null)}
            className="text-xs font-semibold hover:underline"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <MetricCard
          title="Total Reviews"
          value={sentiment.review_count.toLocaleString()}
          icon={<MessageSquare className="h-5 w-5 text-forest" />}
          subtext={`${sentiment.verified_count} verified · ${sentiment.snippet_count} snippets`}
        />
        <MetricCard
          title="Average Rating"
          value={sentiment.avg_rating ? `${sentiment.avg_rating.toFixed(1)} / 5.0` : 'N/A'}
          icon={<Star className="h-5 w-5 text-amber" />}
          subtext="Across all platforms"
        />
        <MetricCard
          title="Positive Feedback"
          value={`${(sentiment.positive_pct * 100).toFixed(0)}%`}
          icon={<ThumbsUp className="h-5 w-5 text-forest" />}
          status="positive"
        />
        <MetricCard
          title="Neutral Sentiment"
          value={`${(sentiment.neutral_pct * 100).toFixed(0)}%`}
          icon={<Minus className="h-5 w-5 text-stone-500" />}
          status="neutral"
        />
        <MetricCard
          title="Negative Sentiment"
          value={`${(sentiment.negative_pct * 100).toFixed(0)}%`}
          icon={<ThumbsDown className="h-5 w-5 text-terracotta" />}
          status="negative"
        />
      </div>

      {/* Visual Analytics Row */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Rating Breakdown */}
        <div className="rounded-xl border border-stone-200 bg-white p-6 shadow-sm">
          <div className="mb-4">
            <h2 className="text-base font-semibold text-stone-900 font-serif">Rating Distribution</h2>
            <p className="text-xs text-stone-500">Star rating breakdown across customer submissions</p>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart layout="vertical" data={ratingData} margin={{ top: 5, right: 30, left: 10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#E5E7EB" />
                <XAxis type="number" stroke="#9CA3AF" />
                <YAxis dataKey="stars" type="category" stroke="#9CA3AF" tick={{ fontSize: 13, fontWeight: 500 }} />
                <Tooltip
                  formatter={(val: any) => [`${val} reviews`, 'Volume']}
                  contentStyle={{ backgroundColor: '#183B32', color: '#F7F5EF', borderRadius: '8px' }}
                />
                <Bar dataKey="count" fill="#D6A64F" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Sentiment Over Time */}
        <div className="rounded-xl border border-stone-200 bg-white p-6 shadow-sm">
          <div className="mb-4">
            <h2 className="text-base font-semibold text-stone-900 font-serif">Sentiment Trends Over Time</h2>
            <p className="text-xs text-stone-500">Chronological trajectory of positive vs negative feedback</p>
          </div>
          <div className="h-64">
            {trends && trends.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trends} margin={{ top: 5, right: 20, left: -10, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                  <XAxis dataKey="period" stroke="#9CA3AF" tick={{ fontSize: 11 }} />
                  <YAxis stroke="#9CA3AF" tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} />
                  <Tooltip
                    formatter={(val: any) => [`${(Number(val || 0) * 100).toFixed(1)}%`]}
                    contentStyle={{ backgroundColor: '#183B32', color: '#F7F5EF', borderRadius: '8px' }}
                  />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="positive_pct"
                    name="Positive %"
                    stroke="#183B32"
                    strokeWidth={2}
                    dot={{ r: 3 }}
                  />
                  <Line
                    type="monotone"
                    dataKey="negative_pct"
                    name="Negative %"
                    stroke="#D97757"
                    strokeWidth={2}
                    dot={{ r: 3 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-full items-center justify-center text-xs text-stone-400">
                Insufficient timestamp data to plot chronological trend
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Customer Themes: Praises vs Complaints */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* What Customers Love */}
        <div className="rounded-xl border border-stone-200 bg-white p-6 shadow-sm">
          <div className="flex items-center gap-2 mb-4">
            <div className="rounded-md bg-forest/10 p-2 text-forest">
              <ThumbsUp className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-stone-900 font-serif">What Customers Love</h2>
              <p className="text-xs text-stone-500">Key positive themes repeatedly praised</p>
            </div>
          </div>

          <div className="space-y-3">
            {sentiment.appreciated_features && sentiment.appreciated_features.length > 0 ? (
              sentiment.appreciated_features.map((feature, idx) => (
                <div key={idx} className="rounded-lg border border-stone-100 bg-forest/5 p-3">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-stone-800 capitalize text-sm">{feature.theme}</span>
                    <span className="rounded-full bg-forest px-2 py-0.5 text-xs font-semibold text-cream">
                      {feature.frequency} mentions
                    </span>
                  </div>
                  {feature.representative_quote && (
                    <p className="mt-2 text-xs italic text-stone-600 bg-white/70 p-2 rounded border border-stone-200">
                      "{feature.representative_quote}"
                    </p>
                  )}
                </div>
              ))
            ) : (
              <p className="text-xs text-stone-400">No recurring positive themes identified.</p>
            )}
          </div>
        </div>

        {/* Areas to Improve */}
        <div className="rounded-xl border border-stone-200 bg-white p-6 shadow-sm">
          <div className="flex items-center gap-2 mb-4">
            <div className="rounded-md bg-terracotta/10 p-2 text-terracotta">
              <ThumbsDown className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-stone-900 font-serif">Areas to Improve</h2>
              <p className="text-xs text-stone-500">Recurring complaints and customer pain points</p>
            </div>
          </div>

          <div className="space-y-3">
            {sentiment.complaints && sentiment.complaints.length > 0 ? (
              sentiment.complaints.map((complaint, idx) => (
                <div key={idx} className="rounded-lg border border-stone-100 bg-terracotta/5 p-3">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-stone-800 capitalize text-sm">{complaint.theme}</span>
                    <span className="rounded-full bg-terracotta px-2 py-0.5 text-xs font-semibold text-cream">
                      {complaint.frequency} mentions
                    </span>
                  </div>
                  {complaint.representative_quote && (
                    <p className="mt-2 text-xs italic text-stone-600 bg-white/70 p-2 rounded border border-stone-200">
                      "{complaint.representative_quote}"
                    </p>
                  )}
                </div>
              ))
            ) : (
              <p className="text-xs text-stone-400">No major recurring complaints detected.</p>
            )}
          </div>
        </div>
      </div>

      {/* Item-Level Review Feedback Table */}
      <div className="rounded-xl border border-stone-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between mb-4">
          <div>
            <h2 className="text-base font-semibold text-stone-900 font-serif">Item-Level Feedback Matrix</h2>
            <p className="text-xs text-stone-500">Individual dish mentions, ratings, and customer impressions</p>
          </div>
          <div className="relative">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-stone-400" />
            <input
              type="text"
              placeholder="Filter menu items..."
              value={itemSearch}
              onChange={(e) => setItemSearch(e.target.value)}
              className="rounded-lg border border-stone-200 pl-9 pr-4 py-1.5 text-xs focus:border-forest focus:outline-none"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-stone-200 text-left text-xs">
            <thead className="bg-stone-50 text-stone-600 font-semibold uppercase tracking-wider">
              <tr>
                <th className="py-3 px-4">Menu Item</th>
                <th className="py-3 px-4">Mentions</th>
                <th className="py-3 px-4">Avg Rating</th>
                <th className="py-3 px-4">Sentiment (Pos / Neg)</th>
                <th className="py-3 px-4">Top Compliment</th>
                <th className="py-3 px-4">Top Complaint</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100 bg-white">
              {filteredItems.length > 0 ? (
                filteredItems.map((item, idx) => (
                  <tr key={idx} className="hover:bg-cream/40 transition-colors">
                    <td className="py-3 px-4 font-medium text-stone-900">{item.item_name}</td>
                    <td className="py-3 px-4 text-stone-600">
                      <span className="font-semibold text-stone-900">{item.mention_count}</span>
                      <span className="text-[10px] text-stone-400 block">
                        ({item.verified_count} ver / {item.snippet_count} snp)
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      {item.avg_rating ? (
                        <div className="flex items-center gap-1 font-semibold text-stone-900">
                          <Star className="h-3.5 w-3.5 fill-amber text-amber" />
                          <span>{item.avg_rating.toFixed(1)}</span>
                        </div>
                      ) : (
                        <span className="text-stone-400">N/A</span>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-forest">{(item.positive_pct * 100).toFixed(0)}%</span>
                        <span className="text-stone-300">/</span>
                        <span className="font-semibold text-terracotta">{(item.negative_pct * 100).toFixed(0)}%</span>
                      </div>
                      <div className="mt-1 h-1.5 w-24 rounded-full bg-stone-100 overflow-hidden flex">
                        <div style={{ width: `${item.positive_pct * 100}%` }} className="bg-forest" />
                        <div style={{ width: `${item.neutral_pct * 100}%` }} className="bg-stone-300" />
                        <div style={{ width: `${item.negative_pct * 100}%` }} className="bg-terracotta" />
                      </div>
                    </td>
                    <td className="py-3 px-4 text-forest max-w-xs truncate">
                      {item.top_compliment || <span className="text-stone-300 italic">—</span>}
                    </td>
                    <td className="py-3 px-4 text-terracotta max-w-xs truncate">
                      {item.top_complaint || <span className="text-stone-300 italic">—</span>}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-stone-400">
                    No items match the search query.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
