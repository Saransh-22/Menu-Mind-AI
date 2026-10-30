import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Sparkles,
  CheckCircle2,
  XCircle,
  Clock,
  Filter,
  Search,
  ChevronRight,
  TrendingUp,
  DollarSign,
  AlertCircle,
  Check,
  X,
  Bookmark,
  RefreshCw,
  ExternalLink,
  FlaskConical,
  HelpCircle,
  SlidersHorizontal,
} from 'lucide-react';
import { useAppStore } from '../../store';
import {
  fetchRecommendations,
  triggerAiAnalysis,
  fetchAnalysisProgress,
  saveRecommendationApproval,
} from '../../api/recommendations';
import { Recommendation } from '../../types';
import ActionBadge from '../../components/common/ActionBadge';
import MetricCard from '../../components/common/MetricCard';
import EmptyState from '../../components/common/EmptyState';
import { useNavigate } from 'react-router-dom';

export default function RecommendationsPage() {
  const { activeRun } = useAppStore();
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const [actionFilter, setActionFilter] = useState<string>('ALL');
  const [approvalFilter, setApprovalFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedRec, setSelectedRec] = useState<Recommendation | null>(null);
  const [approvalNotes, setApprovalNotes] = useState('');
  const [isAgentRunning, setIsAgentRunning] = useState(false);

  const runId = activeRun?.id;

  const {
    data: recommendations,
    isLoading,
    refetch: refetchRecommendations,
  } = useQuery({
    queryKey: ['recommendations', runId],
    queryFn: () => (runId ? fetchRecommendations(runId) : []),
    enabled: !!runId,
  });

  const { data: progressData } = useQuery({
    queryKey: ['analysisProgress', runId],
    queryFn: () => (runId ? fetchAnalysisProgress(runId) : null),
    enabled: !!runId && isAgentRunning,
    refetchInterval: isAgentRunning ? 1500 : false,
  });

  useEffect(() => {
    if (progressData) {
      if (progressData.status === 'completed' || progressData.status === 'failed') {
        setIsAgentRunning(false);
        queryClient.invalidateQueries({ queryKey: ['recommendations', runId] });
      }
    }
  }, [progressData, runId, queryClient]);

  const runAgentMutation = useMutation({
    mutationFn: () => (runId ? triggerAiAnalysis(runId) : Promise.reject('No run ID')),
    onSuccess: () => {
      setIsAgentRunning(true);
    },
  });

  const approvalMutation = useMutation({
    mutationFn: ({
      recId,
      decision,
      notes,
    }: {
      recId: number;
      decision: 'approved' | 'rejected' | 'saved_for_later';
      notes: string;
    }) => saveRecommendationApproval(recId, decision, notes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recommendations', runId] });
      if (selectedRec) {
        setSelectedRec(null);
      }
    },
  });

  if (!activeRun) {
    return (
      <EmptyState
        title="No Active Run Selected"
        description="Select or create a restaurant analysis run to review AI-generated recommendations."
      />
    );
  }

  const recList = recommendations || [];

  // Summary counts
  const approvedCount = recList.filter((r) => r.approval?.decision === 'approved').length;
  const rejectedCount = recList.filter((r) => r.approval?.decision === 'rejected').length;
  const savedCount = recList.filter((r) => r.approval?.decision === 'saved_for_later').length;
  const pendingCount = recList.length - approvedCount - rejectedCount - savedCount;

  // Filter recommendations
  const filteredRecs = recList.filter((r) => {
    if (actionFilter !== 'ALL' && r.action !== actionFilter) return false;
    if (approvalFilter === 'PENDING' && r.approval) return false;
    if (approvalFilter === 'APPROVED' && r.approval?.decision !== 'approved') return false;
    if (approvalFilter === 'REJECTED' && r.approval?.decision !== 'rejected') return false;
    if (approvalFilter === 'SAVED' && r.approval?.decision !== 'saved_for_later') return false;
    if (searchQuery && !r.item_name.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  });

  const handleDecision = (
    recId: number,
    decision: 'approved' | 'rejected' | 'saved_for_later',
    notes: string = ''
  ) => {
    approvalMutation.mutate({ recId, decision, notes });
  };

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-stone-900 font-serif">AI Menu Recommendations</h1>
          <p className="text-sm text-stone-500">
            Agentic multi-perspective optimization with human-in-the-loop governance.
          </p>
        </div>
        <div>
          <button
            onClick={() => runAgentMutation.mutate()}
            disabled={isAgentRunning || runAgentMutation.isPending}
            className="flex items-center gap-2 rounded-lg bg-forest px-4 py-2 text-sm font-semibold text-cream hover:bg-forest-secondary transition-colors disabled:opacity-50"
          >
            {isAgentRunning || runAgentMutation.isPending ? (
              <RefreshCw className="h-4 w-4 animate-spin" />
            ) : (
              <Sparkles className="h-4 w-4" />
            )}
            {isAgentRunning ? 'Agent Running...' : 'Generate / Refresh Recommendations'}
          </button>
        </div>
      </div>

      {/* Progress Box when running */}
      {isAgentRunning && (
        <div className="rounded-xl border border-forest/30 bg-forest/5 p-5">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <RefreshCw className="h-4 w-4 animate-spin text-forest" />
              <span className="text-sm font-semibold text-forest">
                MenuMind Agent is executing multi-step optimization pipeline...
              </span>
            </div>
            <span className="text-xs font-semibold text-stone-500 uppercase">
              Status: {progressData?.status || 'running'}
            </span>
          </div>

          <div className="space-y-1">
            {progressData?.steps?.map((step, idx) => (
              <div key={idx} className="flex items-center gap-2 text-xs text-stone-600">
                <CheckCircle2 className="h-3.5 w-3.5 text-forest" />
                <span>{step}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* KPI Counters */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          title="Total Generated"
          value={recList.length}
          icon={<Sparkles className="h-5 w-5 text-forest" />}
          subtext="Actionable proposals"
        />
        <MetricCard
          title="Pending Review"
          value={pendingCount}
          icon={<Clock className="h-5 w-5 text-amber" />}
          subtext="Awaiting manager sign-off"
        />
        <MetricCard
          title="Approved Actions"
          value={approvedCount}
          icon={<CheckCircle2 className="h-5 w-5 text-forest" />}
          status="positive"
        />
        <MetricCard
          title="Rejected / Saved"
          value={rejectedCount + savedCount}
          icon={<XCircle className="h-5 w-5 text-stone-400" />}
          subtext={`${rejectedCount} rejected · ${savedCount} saved`}
        />
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col gap-3 rounded-xl border border-stone-200 bg-white p-4 shadow-sm md:flex-row md:items-center md:justify-between">
        {/* Action Type Tabs */}
        <div className="flex flex-wrap items-center gap-1.5">
          {['ALL', 'IMPROVE', 'REMOVE', 'PROMOTE', 'REPRICE', 'INSUFFICIENT_EVIDENCE'].map((action) => (
            <button
              key={action}
              onClick={() => setActionFilter(action)}
              className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors ${
                actionFilter === action
                  ? 'bg-forest text-cream'
                  : 'bg-stone-100 text-stone-600 hover:bg-stone-200'
              }`}
            >
              {action.replace('_', ' ')}
            </button>
          ))}
        </div>

        {/* Status Filter & Search */}
        <div className="flex items-center gap-2">
          <select
            value={approvalFilter}
            onChange={(e) => setApprovalFilter(e.target.value)}
            className="rounded-lg border border-stone-200 bg-stone-50 px-3 py-1.5 text-xs text-stone-700 focus:border-forest focus:outline-none"
          >
            <option value="ALL">All Statuses</option>
            <option value="PENDING">Pending Review</option>
            <option value="APPROVED">Approved</option>
            <option value="REJECTED">Rejected</option>
            <option value="SAVED">Saved for Later</option>
          </select>

          <div className="relative">
            <Search className="absolute left-3 top-2 h-3.5 w-3.5 text-stone-400" />
            <input
              type="text"
              placeholder="Search dish name..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="rounded-lg border border-stone-200 pl-8 pr-3 py-1.5 text-xs focus:border-forest focus:outline-none"
            />
          </div>
        </div>
      </div>

      {/* Recommendations Cards Grid */}
      {filteredRecs.length > 0 ? (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {filteredRecs.map((rec) => {
            const hasDecision = !!rec.approval;
            const currentDecision = rec.approval?.decision;

            return (
              <div
                key={rec.id}
                className={`flex flex-col justify-between rounded-xl border bg-white p-5 shadow-sm transition-all hover:border-forest/40 ${
                  currentDecision === 'approved'
                    ? 'border-forest/40 bg-forest/[0.02]'
                    : currentDecision === 'rejected'
                    ? 'border-stone-200 opacity-70'
                    : 'border-stone-200'
                }`}
              >
                <div>
                  {/* Card Header */}
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="text-base font-bold text-stone-900 font-serif">{rec.item_name}</h3>
                        {rec.priority && (
                          <span
                            className={`rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase ${
                              rec.priority === 'high'
                                ? 'bg-terracotta/10 text-terracotta'
                                : rec.priority === 'medium'
                                ? 'bg-amber/10 text-amber'
                                : 'bg-stone-100 text-stone-500'
                            }`}
                          >
                            {rec.priority} priority
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-stone-400 mt-0.5">
                        Confidence: {((rec.confidence_score || 0) * 100).toFixed(0)}%
                      </p>
                    </div>

                    <div className="flex items-center gap-2">
                      <ActionBadge action={rec.action} />
                    </div>
                  </div>

                  {/* Core Reasoning */}
                  <p className="mt-3 text-xs text-stone-600 leading-relaxed line-clamp-3">
                    {rec.reasoning || 'No specific reasoning recorded.'}
                  </p>

                  {/* Evidence Pills */}
                  <div className="mt-4 grid grid-cols-3 gap-2 rounded-lg bg-stone-50 p-2.5 text-[11px]">
                    <div>
                      <span className="text-stone-400 block text-[10px]">Sales Volume</span>
                      <span className="font-semibold text-stone-800">
                        {rec.sales_metrics?.total_units
                          ? `${rec.sales_metrics.total_units} units`
                          : 'No data'}
                      </span>
                    </div>
                    <div>
                      <span className="text-stone-400 block text-[10px]">Revenue</span>
                      <span className="font-semibold text-stone-800">
                        {rec.sales_metrics?.total_revenue
                          ? `$${rec.sales_metrics.total_revenue.toLocaleString()}`
                          : 'No data'}
                      </span>
                    </div>
                    <div>
                      <span className="text-stone-400 block text-[10px]">Margin</span>
                      <span className="font-semibold text-stone-800">
                        {rec.profitability?.margin_pct !== undefined
                          ? `${(rec.profitability.margin_pct * 100).toFixed(0)}%`
                          : 'Pending costs'}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Card Footer: Approval Buttons & Evidence Trigger */}
                <div className="mt-5 flex items-center justify-between border-t border-stone-100 pt-3">
                  <button
                    onClick={() => setSelectedRec(rec)}
                    className="flex items-center gap-1 text-xs font-semibold text-forest hover:underline"
                  >
                    View Full Evidence & Steps
                    <ChevronRight className="h-3.5 w-3.5" />
                  </button>

                  {/* Human-in-the-loop decisions */}
                  <div className="flex items-center gap-1.5">
                    {currentDecision ? (
                      <span
                        className={`rounded-md px-2 py-1 text-xs font-semibold capitalize ${
                          currentDecision === 'approved'
                            ? 'bg-forest/10 text-forest'
                            : currentDecision === 'rejected'
                            ? 'bg-terracotta/10 text-terracotta'
                            : 'bg-stone-100 text-stone-600'
                        }`}
                      >
                        {currentDecision.replace('_', ' ')}
                      </span>
                    ) : (
                      <>
                        <button
                          onClick={() => handleDecision(rec.id, 'approved')}
                          className="flex items-center gap-1 rounded bg-forest/10 px-2.5 py-1 text-xs font-semibold text-forest hover:bg-forest hover:text-cream transition-colors"
                          title="Approve Recommendation"
                        >
                          <Check className="h-3.5 w-3.5" />
                          Approve
                        </button>
                        <button
                          onClick={() => handleDecision(rec.id, 'rejected')}
                          className="flex items-center gap-1 rounded bg-terracotta/10 px-2.5 py-1 text-xs font-semibold text-terracotta hover:bg-terracotta hover:text-cream transition-colors"
                          title="Reject Recommendation"
                        >
                          <X className="h-3.5 w-3.5" />
                          Reject
                        </button>
                        <button
                          onClick={() => handleDecision(rec.id, 'saved_for_later')}
                          className="flex items-center gap-1 rounded bg-stone-100 px-2.5 py-1 text-xs font-semibold text-stone-600 hover:bg-stone-200 transition-colors"
                          title="Save for Later"
                        >
                          <Bookmark className="h-3.5 w-3.5" />
                        </button>
                      </>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <EmptyState
          title="No Matching Recommendations"
          description={
            recList.length === 0
              ? 'Click "Generate / Refresh Recommendations" above to trigger the agent reasoning pipeline.'
              : 'Try clearing your filters or search keywords.'
          }
        />
      )}

      {/* Detail Slide-over / Modal */}
      {selectedRec && (
        <div className="fixed inset-0 z-50 flex items-center justify-end bg-stone-900/40 backdrop-blur-sm">
          <div className="h-full w-full max-w-xl overflow-y-auto bg-white p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-stone-200 pb-4">
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-xl font-bold text-stone-900 font-serif">{selectedRec.item_name}</h2>
                  <ActionBadge action={selectedRec.action} />
                </div>
                <p className="text-xs text-stone-500 mt-1">
                  Confidence: {((selectedRec.confidence_score || 0) * 100).toFixed(0)}% · Priority:{' '}
                  {selectedRec.priority || 'standard'}
                </p>
              </div>
              <button
                onClick={() => setSelectedRec(null)}
                className="rounded-lg p-1 text-stone-400 hover:bg-stone-100 hover:text-stone-700"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="mt-5 space-y-5">
              {/* Reasoning */}
              <div>
                <h3 className="text-xs font-bold uppercase tracking-wider text-stone-400">Agent Reasoning</h3>
                <p className="mt-1 text-sm text-stone-800 leading-relaxed bg-cream/30 p-3 rounded-lg border border-stone-100">
                  {selectedRec.reasoning}
                </p>
              </div>

              {/* Expected Benefits */}
              {selectedRec.expected_benefits && (
                <div>
                  <h3 className="text-xs font-bold uppercase tracking-wider text-forest">Expected Benefits</h3>
                  <p className="mt-1 text-xs text-stone-700 leading-relaxed bg-forest/5 p-3 rounded-lg border border-forest/10">
                    {selectedRec.expected_benefits}
                  </p>
                </div>
              )}

              {/* Potential Risks */}
              {selectedRec.potential_risks && (
                <div>
                  <h3 className="text-xs font-bold uppercase tracking-wider text-terracotta">Potential Risks</h3>
                  <p className="mt-1 text-xs text-stone-700 leading-relaxed bg-terracotta/5 p-3 rounded-lg border border-terracotta/10">
                    {selectedRec.potential_risks}
                  </p>
                </div>
              )}

              {/* Actionable Next Steps */}
              {selectedRec.next_steps && selectedRec.next_steps.length > 0 && (
                <div>
                  <h3 className="text-xs font-bold uppercase tracking-wider text-stone-400">Actionable Next Steps</h3>
                  <ul className="mt-2 space-y-1.5">
                    {selectedRec.next_steps.map((step, idx) => (
                      <li key={idx} className="flex items-start gap-2 text-xs text-stone-700">
                        <CheckCircle2 className="h-4 w-4 text-forest shrink-0 mt-0.5" />
                        <span>{step}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Alternative Options */}
              {selectedRec.alternative_actions && selectedRec.alternative_actions.length > 0 && (
                <div>
                  <h3 className="text-xs font-bold uppercase tracking-wider text-stone-400">
                    Alternative Strategies Evaluated
                  </h3>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {selectedRec.alternative_actions.map((alt, idx) => (
                      <span
                        key={idx}
                        className="rounded-full bg-stone-100 px-3 py-1 text-xs text-stone-700 border border-stone-200"
                      >
                        {alt}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Human Approval Section */}
              <div className="rounded-xl border border-stone-200 bg-stone-50 p-4">
                <h3 className="text-xs font-bold uppercase tracking-wider text-stone-700 mb-2">
                  Manager Decision & Notes
                </h3>
                <textarea
                  placeholder="Add operational notes or reasons for approval / rejection..."
                  value={approvalNotes}
                  onChange={(e) => setApprovalNotes(e.target.value)}
                  className="w-full rounded-lg border border-stone-200 p-2 text-xs focus:border-forest focus:outline-none"
                  rows={2}
                />
                <div className="mt-3 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleDecision(selectedRec.id, 'approved', approvalNotes)}
                      className="rounded-lg bg-forest px-3 py-1.5 text-xs font-semibold text-cream hover:bg-forest-secondary"
                    >
                      Approve Action
                    </button>
                    <button
                      onClick={() => handleDecision(selectedRec.id, 'rejected', approvalNotes)}
                      className="rounded-lg bg-terracotta px-3 py-1.5 text-xs font-semibold text-cream hover:opacity-90"
                    >
                      Reject
                    </button>
                    <button
                      onClick={() => handleDecision(selectedRec.id, 'saved_for_later', approvalNotes)}
                      className="rounded-lg border border-stone-300 bg-white px-3 py-1.5 text-xs font-semibold text-stone-700 hover:bg-stone-100"
                    >
                      Save Later
                    </button>
                  </div>

                  <button
                    onClick={() => {
                      setSelectedRec(null);
                      navigate('/experiments');
                    }}
                    className="flex items-center gap-1 text-xs font-semibold text-forest hover:underline"
                  >
                    <FlaskConical className="h-3.5 w-3.5" />
                    Launch Experiment
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
