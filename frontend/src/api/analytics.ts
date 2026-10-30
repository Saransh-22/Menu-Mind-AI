import { apiClient } from './client';
import { AnalyticsSummaryOut, RevenueTrendPoint, ProfitabilityMetrics } from '../types';

export async function fetchAnalyticsSummary(runId: number): Promise<AnalyticsSummaryOut> {
  const { data } = await apiClient.get<AnalyticsSummaryOut>(`/api/runs/${runId}/analytics/summary`);
  return data;
}

export async function fetchRevenueTrends(
  runId: number,
  startDate?: string,
  endDate?: string
): Promise<RevenueTrendPoint[]> {
  const { data } = await apiClient.get<RevenueTrendPoint[]>(`/api/runs/${runId}/analytics/trends`, {
    params: { start_date: startDate, end_date: endDate },
  });
  return data;
}

export async function fetchProfitability(runId: number): Promise<ProfitabilityMetrics[]> {
  const { data } = await apiClient.get<ProfitabilityMetrics[]>(`/api/runs/${runId}/analytics/profitability`);
  return data;
}
