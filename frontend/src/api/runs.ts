import { apiClient } from './client';
import { AnalysisRun } from '../types';

export async function fetchRunDetails(runId: number): Promise<AnalysisRun> {
  const { data } = await apiClient.get<AnalysisRun>(`/api/runs/${runId}`);
  return data;
}

export async function fetchRunStatus(runId: number): Promise<{
  run_id: number;
  status: string;
  data_quality_score?: number;
  completed_at?: string;
  datasets: { menu: boolean; sales: boolean; reviews: boolean; costs: boolean };
}> {
  const { data } = await apiClient.get(`/api/runs/${runId}/status`);
  return data;
}
