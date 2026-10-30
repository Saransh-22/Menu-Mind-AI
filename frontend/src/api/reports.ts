export function getHtmlReportUrl(runId: number): string {
  const base = import.meta.env.VITE_API_BASE_URL || '';
  return `${base}/api/runs/${runId}/reports/html`;
}

export function getCsvReportUrl(runId: number): string {
  const base = import.meta.env.VITE_API_BASE_URL || '';
  return `${base}/api/runs/${runId}/reports/csv`;
}
