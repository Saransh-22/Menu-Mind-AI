import { apiClient } from './client';
import { SentimentSummary, ItemReviewInsight, ReviewTrendRecord } from '../types';

export async function fetchSentimentSummary(runId: number): Promise<SentimentSummary> {
  const { data } = await apiClient.get<SentimentSummary>(`/api/runs/${runId}/reviews/sentiment`);
  return data;
}

export async function fetchItemReviewInsights(runId: number): Promise<ItemReviewInsight[]> {
  const { data } = await apiClient.get<ItemReviewInsight[]>(`/api/runs/${runId}/reviews/items`);
  return data;
}

export async function fetchReviewTrends(runId: number): Promise<ReviewTrendRecord[]> {
  const { data } = await apiClient.get<ReviewTrendRecord[]>(`/api/runs/${runId}/reviews/trends`);
  return data;
}

export async function fetchWebReviews(runId: number): Promise<{
  success: boolean;
  reviews_retrieved: number;
  total_reviews?: number;
  source?: string;
  attribution?: string;
  limitations?: string[];
  error?: string;
}> {
  const { data } = await apiClient.post(`/api/runs/${runId}/reviews/fetch-web`);
  return data;
}
