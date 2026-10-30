import { apiClient } from './client';
import { DataQualityReport, ValidationResult, DatasetPreview } from '../types';

export async function uploadDataset(
  runId: number,
  fileType: 'menu' | 'sales' | 'reviews' | 'costs',
  file: File,
  onProgress?: (pct: number) => void
): Promise<DataQualityReport> {
  const formData = new FormData();
  formData.append('file', file);

  const { data } = await apiClient.post<DataQualityReport>(
    `/api/runs/${runId}/upload/${fileType}`,
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (evt) => {
        if (evt.total && onProgress) {
          const pct = Math.round((evt.loaded * 100) / evt.total);
          onProgress(pct);
        }
      },
    }
  );
  return data;
}

export async function validateDatasets(runId: number): Promise<ValidationResult> {
  const { data } = await apiClient.get<ValidationResult>(`/api/runs/${runId}/validate`);
  return data;
}

export async function fetchDatasetPreview(
  runId: number,
  fileType: string,
  limit: number = 20
): Promise<DatasetPreview> {
  const { data } = await apiClient.get<DatasetPreview>(`/api/runs/${runId}/datasets/${fileType}/preview`, {
    params: { limit },
  });
  return data;
}

export async function fetchQualityReports(runId: number): Promise<DataQualityReport[]> {
  const { data } = await apiClient.get<DataQualityReport[]>(`/api/runs/${runId}/quality-reports`);
  return data;
}
