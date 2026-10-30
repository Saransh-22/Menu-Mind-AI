import { apiClient } from './client';
import { Restaurant, RestaurantSuggestion, AnalysisRun } from '../types';

export async function fetchRestaurants(): Promise<Restaurant[]> {
  const { data } = await apiClient.get<Restaurant[]>('/api/restaurants');
  return data;
}

export async function createRestaurant(payload: {
  name: string;
  city?: string;
  location?: string;
  website?: string;
  category?: string;
}): Promise<Restaurant> {
  const { data } = await apiClient.post<Restaurant>('/api/restaurants', payload);
  return data;
}

export async function fetchAutocomplete(query: string, city: string = ''): Promise<RestaurantSuggestion[]> {
  const { data } = await apiClient.get<RestaurantSuggestion[]>('/api/restaurants/autocomplete', {
    params: { query, city },
  });
  return data;
}

export async function fetchRestaurantRuns(restaurantId: number): Promise<AnalysisRun[]> {
  const { data } = await apiClient.get<AnalysisRun[]>(`/api/restaurants/${restaurantId}/runs`);
  return data;
}

export async function createAnalysisRun(
  restaurantId: number,
  payload: { period_start?: string; period_end?: string; notes?: string }
): Promise<AnalysisRun> {
  const { data } = await apiClient.post<AnalysisRun>(`/api/restaurants/${restaurantId}/runs`, payload);
  return data;
}
