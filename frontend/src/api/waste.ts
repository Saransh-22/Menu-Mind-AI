import { apiClient } from './client';
import { WasteIntelligenceSummary, WasteRecord } from '../types';

export async function fetchWasteSummary(runId: number): Promise<WasteIntelligenceSummary> {
  const { data } = await apiClient.get<WasteIntelligenceSummary>(`/api/runs/${runId}/waste/summary`);
  return data;
}

export async function recordWasteEntry(
  runId: number,
  payload: {
    ingredient_name: string;
    quantity: number;
    unit: string;
    unit_cost: number;
    waste_reason?: string;
    associated_dish?: string;
    image_item_name?: string;
    image_confidence?: number;
    verified_by_user?: boolean;
  }
): Promise<WasteRecord> {
  const { data } = await apiClient.post<WasteRecord>(`/api/runs/${runId}/waste/records`, payload);
  return data;
}

export async function analyzeFoodImage(
  runId: number,
  file: File
): Promise<{
  items: {
    name: string;
    state: string;
    confidence: number;
    visual_notes: string;
  }[];
  image_limitations: string[];
}> {
  const formData = new FormData();
  formData.append('image', file);

  const { data } = await apiClient.post(`/api/runs/${runId}/waste/analyze-image`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return data;
}
