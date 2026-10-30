import { apiClient } from './client';
import { Recommendation, Approval } from '../types';

export async function fetchRecommendations(runId: number): Promise<Recommendation[]> {
  const { data } = await apiClient.get<Recommendation[]>(`/api/runs/${runId}/recommendations`);
  return data;
}

export async function triggerAiAnalysis(runId: number): Promise<{
  status: string;
  message: string;
  run_id?: number;
}> {
  const { data } = await apiClient.post(`/api/runs/${runId}/run-analysis`);
  return data;
}

export async function fetchAnalysisProgress(runId: number): Promise<{
  status: string;
  steps: string[];
  error?: string;
  recommendations_count: number;
}> {
  const { data } = await apiClient.get(`/api/runs/${runId}/analysis-progress`);
  return data;
}

export async function saveRecommendationApproval(
  recommendationId: number,
  decision: 'approved' | 'rejected' | 'saved_for_later',
  notes: string = ''
): Promise<Approval> {
  const { data } = await apiClient.post<Approval>(`/api/recommendations/${recommendationId}/approval`, {
    decision,
    notes,
  });
  return data;
}
