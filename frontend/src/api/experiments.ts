import { apiClient } from './client';
import { Experiment } from '../types';

export async function fetchExperiments(runId: number): Promise<Experiment[]> {
  const { data } = await apiClient.get<Experiment[]>(`/api/runs/${runId}/experiments`);
  return data;
}

export async function createExperiment(
  runId: number,
  payload: {
    title: string;
    hypothesis?: string;
    intervention?: string;
    baseline_start?: string;
    baseline_end?: string;
    test_start?: string;
    test_end?: string;
    success_criteria?: string;
    guardrail_metrics?: string;
    recommendation_id?: number;
  }
): Promise<Experiment> {
  const { data } = await apiClient.post<Experiment>(`/api/runs/${runId}/experiments`, payload);
  return data;
}

export async function updateExperimentStatus(
  experimentId: number,
  status: 'proposed' | 'approved' | 'active' | 'completed' | 'cancelled'
): Promise<{ status: string; experiment_id: number }> {
  const { data } = await apiClient.patch(`/api/experiments/${experimentId}/status`, { status });
  return data;
}

export async function recordExperimentResults(
  experimentId: number,
  results: {
    metric_name: string;
    baseline_value?: number;
    test_value?: number;
    change_pct?: number;
    notes?: string;
  }[]
): Promise<any> {
  const { data } = await apiClient.post(`/api/experiments/${experimentId}/results`, results);
  return data;
}
