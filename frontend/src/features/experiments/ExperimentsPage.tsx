import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  FlaskConical,
  Plus,
  Play,
  CheckCircle,
  XCircle,
  Clock,
  ArrowRight,
  TrendingUp,
  BarChart2,
  Calendar,
  ShieldAlert,
  Target,
  RefreshCw,
  X,
} from 'lucide-react';
import { useAppStore } from '../../store';
import {
  fetchExperiments,
  createExperiment,
  updateExperimentStatus,
  recordExperimentResults,
} from '../../api/experiments';
import { Experiment } from '../../types';
import MetricCard from '../../components/common/MetricCard';
import EmptyState from '../../components/common/EmptyState';

export default function ExperimentsPage() {
  const { activeRun } = useAppStore();
  const queryClient = useQueryClient();

  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [selectedExpForResults, setSelectedExpForResults] = useState<Experiment | null>(null);

  // New Experiment Form State
  const [formTitle, setFormTitle] = useState('');
  const [formHypothesis, setFormHypothesis] = useState('');
  const [formIntervention, setFormIntervention] = useState('');
  const [formBaselineStart, setFormBaselineStart] = useState('');
  const [formBaselineEnd, setFormBaselineEnd] = useState('');
  const [formTestStart, setFormTestStart] = useState('');
  const [formTestEnd, setFormTestEnd] = useState('');
  const [formSuccessCriteria, setFormSuccessCriteria] = useState('');
  const [formGuardrails, setFormGuardrails] = useState('');

  // Results Recording State
  const [metricName, setMetricName] = useState('Sales Units');
  const [baselineVal, setBaselineVal] = useState<number>(0);
  const [testVal, setTestVal] = useState<number>(0);
  const [resultNotes, setResultNotes] = useState('');

  const runId = activeRun?.id;

  const {
    data: experiments,
    isLoading,
  } = useQuery({
    queryKey: ['experiments', runId],
    queryFn: () => (runId ? fetchExperiments(runId) : []),
    enabled: !!runId,
  });

  const createMutation = useMutation({
    mutationFn: () => {
      if (!runId) return Promise.reject('No run ID');
      return createExperiment(runId, {
        title: formTitle,
        hypothesis: formHypothesis,
        intervention: formIntervention,
        baseline_start: formBaselineStart,
        baseline_end: formBaselineEnd,
        test_start: formTestStart,
        test_end: formTestEnd,
        success_criteria: formSuccessCriteria,
        guardrail_metrics: formGuardrails,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['experiments', runId] });
      setIsCreateOpen(false);
      resetCreateForm();
    },
  });

  const statusMutation = useMutation({
    mutationFn: ({
      expId,
      status,
    }: {
      expId: number;
      status: 'proposed' | 'approved' | 'active' | 'completed' | 'cancelled';
    }) => updateExperimentStatus(expId, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['experiments', runId] });
    },
  });

  const recordResultsMutation = useMutation({
    mutationFn: () => {
      if (!selectedExpForResults) return Promise.reject('No experiment selected');
      const changePct = baselineVal > 0 ? (testVal - baselineVal) / baselineVal : 0;
      return recordExperimentResults(selectedExpForResults.id, [
        {
          metric_name: metricName,
          baseline_value: baselineVal,
          test_value: testVal,
          change_pct: changePct,
          notes: resultNotes,
        },
      ]);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['experiments', runId] });
      setSelectedExpForResults(null);
      setBaselineVal(0);
      setTestVal(0);
      setResultNotes('');
    },
  });

  const resetCreateForm = () => {
    setFormTitle('');
    setFormHypothesis('');
    setFormIntervention('');
    setFormBaselineStart('');
    setFormBaselineEnd('');
    setFormTestStart('');
    setFormTestEnd('');
    setFormSuccessCriteria('');
    setFormGuardrails('');
  };

  if (!activeRun) {
    return (
      <EmptyState
        title="No Active Run Selected"
        description="Select an active restaurant run to manage menu optimization experiments."
      />
    );
  }

  const expList = experiments || [];
  const activeCount = expList.filter((e) => e.status === 'active').length;
  const completedCount = expList.filter((e) => e.status === 'completed').length;
  const proposedCount = expList.filter((e) => e.status === 'proposed').length;
  const approvedCount = expList.filter((e) => e.status === 'approved').length;

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'active':
        return <span className="rounded-full bg-forest px-2.5 py-0.5 text-xs font-semibold text-cream">Active</span>;
      case 'approved':
        return <span className="rounded-full bg-amber/20 px-2.5 py-0.5 text-xs font-semibold text-amber">Approved</span>;
      case 'completed':
        return <span className="rounded-full bg-forest/10 px-2.5 py-0.5 text-xs font-semibold text-forest">Completed</span>;
      case 'cancelled':
        return <span className="rounded-full bg-terracotta/10 px-2.5 py-0.5 text-xs font-semibold text-terracotta">Cancelled</span>;
      default:
        return <span className="rounded-full bg-stone-100 px-2.5 py-0.5 text-xs font-semibold text-stone-600">Proposed</span>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-stone-900 font-serif">Menu Experiments & A/B Tests</h1>
          <p className="text-sm text-stone-500">
            Scientifically test price elasticity, recipe adjustments, and menu positioning before permanent rollout.
          </p>
        </div>
        <button
          onClick={() => setIsCreateOpen(true)}
          className="flex items-center gap-2 rounded-lg bg-forest px-4 py-2 text-sm font-semibold text-cream hover:bg-forest-secondary transition-colors"
        >
          <Plus className="h-4 w-4" />
          Create Experiment
        </button>
      </div>

      {/* KPI Counters */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          title="Active Experiments"
          value={activeCount}
          icon={<FlaskConical className="h-5 w-5 text-forest" />}
          status={activeCount > 0 ? 'positive' : 'neutral'}
          subtext="Currently running live"
        />
        <MetricCard
          title="Completed & Verified"
          value={completedCount}
          icon={<CheckCircle className="h-5 w-5 text-forest" />}
          subtext="Evaluated outcomes"
        />
        <MetricCard
          title="Approved (Ready to Run)"
          value={approvedCount}
          icon={<Clock className="h-5 w-5 text-amber" />}
          subtext="Scheduled tests"
        />
        <MetricCard
          title="Proposed Pipeline"
          value={proposedCount}
          icon={<Target className="h-5 w-5 text-stone-500" />}
          subtext="Awaiting manager approval"
        />
      </div>

      {/* Experiment List / Table */}
      {expList.length > 0 ? (
        <div className="space-y-4">
          {expList.map((exp) => (
            <div
              key={exp.id}
              className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm transition-all hover:border-forest/30"
            >
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div className="space-y-2">
                  <div className="flex items-center gap-3">
                    <h3 className="text-lg font-bold text-stone-900 font-serif">{exp.title}</h3>
                    {getStatusBadge(exp.status)}
                  </div>

                  {exp.hypothesis && (
                    <div className="text-xs text-stone-700">
                      <strong className="text-stone-900">Hypothesis:</strong> {exp.hypothesis}
                    </div>
                  )}

                  {exp.intervention && (
                    <div className="text-xs text-stone-700">
                      <strong className="text-stone-900">Intervention:</strong> {exp.intervention}
                    </div>
                  )}

                  {/* Dates & Metrics */}
                  <div className="flex flex-wrap items-center gap-4 text-xs text-stone-500 pt-1">
                    {(exp.baseline_start || exp.baseline_end) && (
                      <div className="flex items-center gap-1">
                        <Calendar className="h-3.5 w-3.5 text-stone-400" />
                        <span>Baseline: {exp.baseline_start || 'N/A'} to {exp.baseline_end || 'N/A'}</span>
                      </div>
                    )}
                    {(exp.test_start || exp.test_end) && (
                      <div className="flex items-center gap-1">
                        <ArrowRight className="h-3.5 w-3.5 text-forest" />
                        <span>Test: {exp.test_start || 'N/A'} to {exp.test_end || 'N/A'}</span>
                      </div>
                    )}
                    {exp.guardrail_metrics && (
                      <div className="flex items-center gap-1 text-terracotta">
                        <ShieldAlert className="h-3.5 w-3.5" />
                        <span>Guardrail: {exp.guardrail_metrics}</span>
                      </div>
                    )}
                  </div>

                  {/* Recorded Results Display */}
                  {exp.results && exp.results.length > 0 && (
                    <div className="mt-3 rounded-lg border border-forest/20 bg-forest/5 p-3">
                      <div className="text-xs font-semibold text-forest mb-2">Recorded Evaluation Results:</div>
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                        {exp.results.map((res, rIdx) => (
                          <div key={rIdx} className="bg-white p-2 rounded border border-stone-100 text-xs">
                            <span className="text-stone-500 block text-[10px]">{res.metric_name}</span>
                            <div className="flex items-center justify-between mt-1">
                              <span className="text-stone-700">
                                {res.baseline_value} → {res.test_value}
                              </span>
                              <span
                                className={`font-bold ${
                                  (res.change_pct || 0) >= 0 ? 'text-forest' : 'text-terracotta'
                                }`}
                              >
                                {((res.change_pct || 0) * 100).toFixed(1)}%
                              </span>
                            </div>
                            {res.notes && <p className="text-[10px] text-stone-400 mt-1 italic">{res.notes}</p>}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* State Machine Action Controls */}
                <div className="flex flex-wrap items-center gap-2 self-start lg:self-center shrink-0">
                  {exp.status === 'proposed' && (
                    <button
                      onClick={() => statusMutation.mutate({ expId: exp.id, status: 'approved' })}
                      className="rounded-lg bg-amber/20 px-3 py-1.5 text-xs font-semibold text-amber hover:bg-amber hover:text-stone-900 transition-colors"
                    >
                      Approve Experiment
                    </button>
                  )}

                  {exp.status === 'approved' && (
                    <button
                      onClick={() => statusMutation.mutate({ expId: exp.id, status: 'active' })}
                      className="flex items-center gap-1.5 rounded-lg bg-forest px-3 py-1.5 text-xs font-semibold text-cream hover:bg-forest-secondary transition-colors"
                    >
                      <Play className="h-3 w-3" />
                      Start Experiment
                    </button>
                  )}

                  {exp.status === 'active' && (
                    <>
                      <button
                        onClick={() => setSelectedExpForResults(exp)}
                        className="flex items-center gap-1 rounded-lg border border-forest px-3 py-1.5 text-xs font-semibold text-forest hover:bg-forest hover:text-cream transition-colors"
                      >
                        <BarChart2 className="h-3.5 w-3.5" />
                        Record Results
                      </button>
                      <button
                        onClick={() => statusMutation.mutate({ expId: exp.id, status: 'completed' })}
                        className="rounded-lg bg-forest/10 px-3 py-1.5 text-xs font-semibold text-forest hover:bg-forest hover:text-cream transition-colors"
                      >
                        Complete Test
                      </button>
                    </>
                  )}

                  {exp.status !== 'completed' && exp.status !== 'cancelled' && (
                    <button
                      onClick={() => statusMutation.mutate({ expId: exp.id, status: 'cancelled' })}
                      className="rounded-lg border border-stone-200 px-2.5 py-1.5 text-xs font-semibold text-stone-500 hover:bg-stone-100"
                    >
                      Cancel
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <EmptyState
          title="No Experiments Configured"
          description="Create your first controlled menu experiment or convert an approved recommendation into an active A/B test."
          action={
            <button
              onClick={() => setIsCreateOpen(true)}
              className="flex items-center gap-2 rounded-lg bg-forest px-4 py-2 text-sm font-semibold text-cream hover:bg-forest-secondary"
            >
              <Plus className="h-4 w-4" />
              Create Experiment
            </button>
          }
        />
      )}

      {/* Modal: Create Experiment */}
      {isCreateOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-stone-900/50 p-4 backdrop-blur-sm">
          <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-stone-200 pb-3">
              <h3 className="text-lg font-bold text-stone-900 font-serif">Create New Menu Experiment</h3>
              <button
                onClick={() => setIsCreateOpen(false)}
                className="rounded-lg p-1 text-stone-400 hover:bg-stone-100 hover:text-stone-700"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="mt-4 space-y-3.5 max-h-[75vh] overflow-y-auto pr-1">
              <div>
                <label className="block text-xs font-semibold text-stone-700">Experiment Title *</label>
                <input
                  type="text"
                  placeholder="e.g. Truffle Fries Repricing & Upsell"
                  value={formTitle}
                  onChange={(e) => setFormTitle(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-stone-200 px-3 py-2 text-xs focus:border-forest focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-stone-700">Hypothesis</label>
                <textarea
                  placeholder="e.g. Raising price from $12 to $14 will not degrade sales volume by > 5% and will increase dish margin by 12%."
                  value={formHypothesis}
                  onChange={(e) => setFormHypothesis(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-stone-200 p-2 text-xs focus:border-forest focus:outline-none"
                  rows={2}
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-stone-700">Intervention (Action)</label>
                <input
                  type="text"
                  placeholder="e.g. Price updated on POS and physical menus."
                  value={formIntervention}
                  onChange={(e) => setFormIntervention(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-stone-200 px-3 py-2 text-xs focus:border-forest focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-stone-700">Baseline Start</label>
                  <input
                    type="date"
                    value={formBaselineStart}
                    onChange={(e) => setFormBaselineStart(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-stone-200 px-3 py-1.5 text-xs focus:border-forest focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-stone-700">Baseline End</label>
                  <input
                    type="date"
                    value={formBaselineEnd}
                    onChange={(e) => setFormBaselineEnd(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-stone-200 px-3 py-1.5 text-xs focus:border-forest focus:outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-stone-700">Test Start</label>
                  <input
                    type="date"
                    value={formTestStart}
                    onChange={(e) => setFormTestStart(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-stone-200 px-3 py-1.5 text-xs focus:border-forest focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-stone-700">Test End</label>
                  <input
                    type="date"
                    value={formTestEnd}
                    onChange={(e) => setFormTestEnd(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-stone-200 px-3 py-1.5 text-xs focus:border-forest focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-stone-700">Success Criteria</label>
                <input
                  type="text"
                  placeholder="e.g. Net weekly revenue increases by $300 without drop in 4+ star reviews"
                  value={formSuccessCriteria}
                  onChange={(e) => setFormSuccessCriteria(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-stone-200 px-3 py-2 text-xs focus:border-forest focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-stone-700">Guardrail Metrics</label>
                <input
                  type="text"
                  placeholder="e.g. Sales drops > 15% triggers immediate rollback"
                  value={formGuardrails}
                  onChange={(e) => setFormGuardrails(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-stone-200 px-3 py-2 text-xs focus:border-forest focus:outline-none"
                />
              </div>
            </div>

            <div className="mt-5 flex justify-end gap-2 border-t border-stone-200 pt-3">
              <button
                onClick={() => setIsCreateOpen(false)}
                className="rounded-lg border border-stone-200 px-3 py-1.5 text-xs font-medium text-stone-600 hover:bg-stone-50"
              >
                Cancel
              </button>
              <button
                onClick={() => createMutation.mutate()}
                disabled={!formTitle.trim() || createMutation.isPending}
                className="rounded-lg bg-forest px-4 py-1.5 text-xs font-semibold text-cream hover:bg-forest-secondary disabled:opacity-50"
              >
                {createMutation.isPending ? 'Saving...' : 'Propose Experiment'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Record Experiment Results */}
      {selectedExpForResults && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-stone-900/50 p-4 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-stone-200 pb-3">
              <div>
                <h3 className="text-base font-bold text-stone-900 font-serif">Record Experiment Results</h3>
                <p className="text-xs text-stone-500">{selectedExpForResults.title}</p>
              </div>
              <button
                onClick={() => setSelectedExpForResults(null)}
                className="rounded-lg p-1 text-stone-400 hover:bg-stone-100 hover:text-stone-700"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="mt-4 space-y-3">
              <div>
                <label className="block text-xs font-semibold text-stone-700">Metric Name</label>
                <input
                  type="text"
                  value={metricName}
                  onChange={(e) => setMetricName(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-stone-200 px-3 py-1.5 text-xs focus:border-forest focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-stone-700">Baseline Value</label>
                  <input
                    type="number"
                    step="0.01"
                    value={baselineVal}
                    onChange={(e) => setBaselineVal(parseFloat(e.target.value) || 0)}
                    className="mt-1 w-full rounded-lg border border-stone-200 px-3 py-1.5 text-xs focus:border-forest focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-stone-700">Test Period Value</label>
                  <input
                    type="number"
                    step="0.01"
                    value={testVal}
                    onChange={(e) => setTestVal(parseFloat(e.target.value) || 0)}
                    className="mt-1 w-full rounded-lg border border-stone-200 px-3 py-1.5 text-xs focus:border-forest focus:outline-none"
                  />
                </div>
              </div>

              <div className="rounded-lg bg-stone-50 p-2 text-xs text-stone-600 flex justify-between">
                <span>Calculated Change:</span>
                <span
                  className={`font-bold ${
                    testVal >= baselineVal ? 'text-forest' : 'text-terracotta'
                  }`}
                >
                  {baselineVal > 0
                    ? `${(((testVal - baselineVal) / baselineVal) * 100).toFixed(1)}%`
                    : 'N/A'}
                </span>
              </div>

              <div>
                <label className="block text-xs font-semibold text-stone-700">Operational Observations</label>
                <textarea
                  placeholder="Notes on customer reaction, kitchen workflow, or stock levels..."
                  value={resultNotes}
                  onChange={(e) => setResultNotes(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-stone-200 p-2 text-xs focus:border-forest focus:outline-none"
                  rows={2}
                />
              </div>
            </div>

            <div className="mt-5 flex justify-end gap-2 border-t border-stone-200 pt-3">
              <button
                onClick={() => setSelectedExpForResults(null)}
                className="rounded-lg border border-stone-200 px-3 py-1.5 text-xs font-medium text-stone-600 hover:bg-stone-50"
              >
                Cancel
              </button>
              <button
                onClick={() => recordResultsMutation.mutate()}
                disabled={recordResultsMutation.isPending}
                className="rounded-lg bg-forest px-4 py-1.5 text-xs font-semibold text-cream hover:bg-forest-secondary disabled:opacity-50"
              >
                {recordResultsMutation.isPending ? 'Saving...' : 'Save Results'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
