import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { useDropzone } from 'react-dropzone';
import {
  UploadCloud,
  FileText,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Table as TableIcon,
  Sparkles,
  ArrowRight,
  RefreshCw,
  Info,
} from 'lucide-react';
import { useAppStore } from '../../store';
import {
  uploadDataset,
  validateDatasets,
  fetchDatasetPreview,
  fetchQualityReports,
} from '../../api/ingestion';
import { triggerAiAnalysis } from '../../api/recommendations';
import { DataQualityReport } from '../../types';

interface DatasetCardProps {
  title: string;
  fileType: 'menu' | 'sales' | 'reviews' | 'costs';
  required?: boolean;
  description: string;
  runId: number;
  report?: DataQualityReport;
  onPreview: (type: string) => void;
}

const DatasetCard: React.FC<DatasetCardProps> = ({
  title,
  fileType,
  required,
  description,
  runId,
  report,
  onPreview,
}) => {
  const queryClient = useQueryClient();
  const [progress, setProgress] = useState<number | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const uploadMutation = useMutation({
    mutationFn: (file: File) =>
      uploadDataset(runId, fileType, file, (pct) => setProgress(pct)),
    onSuccess: () => {
      setProgress(null);
      setErrorMsg(null);
      queryClient.invalidateQueries({ queryKey: ['runDetails', runId] });
      queryClient.invalidateQueries({ queryKey: ['qualityReports', runId] });
      queryClient.invalidateQueries({ queryKey: ['validation', runId] });
      queryClient.invalidateQueries({ queryKey: ['datasetPreview', runId, fileType] });
    },
    onError: (err: any) => {
      setProgress(null);
      setErrorMsg(err.message || 'Upload failed');
    },
  });

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: (files) => {
      if (files.length > 0) {
        setErrorMsg(null);
        uploadMutation.mutate(files[0]);
      }
    },
    accept: {
      'text/csv': ['.csv'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
    },
    maxFiles: 1,
  });

  return (
    <div className="bg-cream-card rounded-card border border-cream-border p-5 shadow-card hover:shadow-cardHover transition flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <span className="font-bold font-display text-sm text-forest-dark">
              {title}
            </span>
            {required ? (
              <span className="text-[10px] uppercase font-bold text-terracotta bg-terracotta-light border border-terracotta-border px-1.5 py-0.5 rounded">
                Required
              </span>
            ) : (
              <span className="text-[10px] uppercase font-bold text-brandText-secondary bg-cream px-1.5 py-0.5 rounded">
                Optional
              </span>
            )}
          </div>
          {report && (
            <span className="text-xs font-mono font-bold text-emerald-800 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full flex items-center gap-1">
              <CheckCircle2 className="w-3 h-3 text-emerald-600" />
              {Math.round(report.quality_score * 100)}%
            </span>
          )}
        </div>
        <p className="text-xs text-brandText-secondary mb-4">{description}</p>

        {/* Dropzone Area */}
        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition ${
            isDragActive
              ? 'border-forest bg-forest-muted'
              : 'border-cream-border hover:border-forest/40 bg-cream/40'
          }`}
        >
          <input {...getInputProps()} />
          <UploadCloud className="w-8 h-8 text-forest/40 mx-auto mb-2" />
          <p className="text-xs font-semibold text-brandText-primary">
            {isDragActive ? 'Drop file here...' : 'Drag & drop or click to browse'}
          </p>
          <p className="text-[10px] text-brandText-secondary mt-1">
            CSV, XLSX or XLS (max 50 MB)
          </p>
        </div>

        {/* Progress Bar */}
        {progress !== null && (
          <div className="mt-3">
            <div className="w-full bg-cream-border h-1.5 rounded-full overflow-hidden">
              <div
                className="bg-forest h-full transition-all duration-200"
                style={{ width: `${progress}%` }}
              ></div>
            </div>
            <p className="text-[10px] text-brandText-secondary text-right mt-1 font-mono">
              {progress}%
            </p>
          </div>
        )}

        {/* Error message */}
        {errorMsg && (
          <div className="mt-3 p-2 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-lg flex items-start gap-1.5">
            <XCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <span>{errorMsg}</span>
          </div>
        )}

        {/* Quality breakdown if uploaded */}
        {report && (
          <div className="mt-4 pt-3 border-t border-cream-border text-xs space-y-1">
            <div className="flex justify-between text-brandText-secondary">
              <span>Accepted Records:</span>
              <span className="font-semibold text-forest-dark tabular-nums">
                {report.accepted_records} / {report.total_records}
              </span>
            </div>
            {report.duplicate_records > 0 && (
              <div className="flex justify-between text-amber-dark">
                <span>Duplicates cleaned:</span>
                <span className="font-semibold tabular-nums">{report.duplicate_records}</span>
              </div>
            )}
            {report.warnings.length > 0 && (
              <div className="text-[11px] text-amber-dark bg-amber-light p-1.5 rounded mt-2">
                ⚠️ {report.warnings[0]}
              </div>
            )}
          </div>
        )}
      </div>

      {report && (
        <button
          onClick={() => onPreview(fileType)}
          className="mt-4 w-full py-1.5 rounded-lg border border-cream-border hover:border-forest text-xs font-semibold text-brandText-primary bg-white flex items-center justify-center gap-1.5 transition"
        >
          <TableIcon className="w-3.5 h-3.5 text-forest" />
          Preview Cleaned Data
        </button>
      )}
    </div>
  );
};

export const UploadPage: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { activeRun } = useAppStore();
  const runId = activeRun?.id;

  const [previewType, setPreviewType] = useState<string | null>(null);

  // Quality reports query
  const { data: qualityReports = [] } = useQuery({
    queryKey: ['qualityReports', runId],
    queryFn: () => (runId ? fetchQualityReports(runId) : Promise.resolve([])),
    enabled: !!runId,
  });

  // Cross-dataset validation query
  const { data: validation, refetch: refetchValidation, isFetching: isValidating } = useQuery({
    queryKey: ['validation', runId],
    queryFn: () => (runId ? validateDatasets(runId) : null),
    enabled: !!runId,
  });

  // Preview query
  const { data: previewData } = useQuery({
    queryKey: ['datasetPreview', runId, previewType],
    queryFn: () => (runId && previewType ? fetchDatasetPreview(runId, previewType) : null),
    enabled: !!runId && !!previewType,
  });

  // AI run trigger mutation
  const runAiMutation = useMutation({
    mutationFn: () => (runId ? triggerAiAnalysis(runId) : Promise.reject('No active run')),
    onSuccess: () => {
      navigate('/recommendations');
    },
  });

  if (!runId) {
    return (
      <div className="text-center py-16">
        <h2 className="text-lg font-bold font-display text-forest-dark mb-2">No Active Run Selected</h2>
        <p className="text-sm text-brandText-secondary mb-4">Please create or select a restaurant analysis run.</p>
        <button
          onClick={() => navigate('/onboarding')}
          className="px-4 py-2 rounded-xl bg-forest text-white text-xs font-bold"
        >
          Go to Onboarding
        </button>
      </div>
    );
  }

  const reportsByType = qualityReports.reduce((acc, r) => {
    acc[r.file_type] = r;
    return acc;
  }, {} as Record<string, DataQualityReport>);

  return (
    <div className="space-y-6">
      {/* Title */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold font-display text-forest-dark">
            Data Upload & Quality Engine
          </h1>
          <p className="text-xs text-brandText-secondary mt-0.5">
            Ingest, clean, and validate restaurant operational files for Run #{runId}.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => refetchValidation()}
            disabled={isValidating}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-cream-border bg-white hover:border-forest text-xs font-semibold text-brandText-primary transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-forest ${isValidating ? 'animate-spin' : ''}`} />
            Re-check Validation
          </button>
        </div>
      </div>

      {/* 4 Dataset Cards (2x2 Grid) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        <DatasetCard
          title="Menu Catalog"
          fileType="menu"
          required
          description="Item names, selling prices, categories, and descriptions."
          runId={runId}
          report={reportsByType['menu']}
          onPreview={(t) => setPreviewType(t)}
        />
        <DatasetCard
          title="Sales Transactions"
          fileType="sales"
          required
          description="Daily quantities sold, dates, and order revenue."
          runId={runId}
          report={reportsByType['sales']}
          onPreview={(t) => setPreviewType(t)}
        />
        <DatasetCard
          title="Customer Reviews"
          fileType="reviews"
          description="Review text, star ratings, and external customer feedback."
          runId={runId}
          report={reportsByType['reviews']}
          onPreview={(t) => setPreviewType(t)}
        />
        <DatasetCard
          title="Ingredient Costs"
          fileType="costs"
          description="Ingredient and packaging costs for contribution margin calculations."
          runId={runId}
          report={reportsByType['costs']}
          onPreview={(t) => setPreviewType(t)}
        />
      </div>

      {/* Validation Status Banner */}
      {validation && (
        <div className="bg-cream-card rounded-card border border-cream-border p-5 shadow-card">
          <div className="flex items-center gap-2 mb-3">
            {validation.is_valid ? (
              <CheckCircle2 className="w-5 h-5 text-emerald-600" />
            ) : (
              <AlertTriangle className="w-5 h-5 text-terracotta" />
            )}
            <h3 className="font-bold font-display text-sm text-forest-dark">
              {validation.is_valid
                ? 'Dataset Integrity Verified'
                : 'Validation Action Required'}
            </h3>
          </div>

          {validation.errors.length > 0 && (
            <div className="space-y-1.5 mb-3">
              {validation.errors.map((err, i) => (
                <div key={i} className="text-xs text-rose-800 bg-rose-50 border border-rose-200 p-2 rounded-lg">
                  ❌ {err}
                </div>
              ))}
            </div>
          )}

          {validation.warnings.length > 0 && (
            <div className="space-y-1.5">
              {validation.warnings.map((warn, i) => (
                <div key={i} className="text-xs text-amber-800 bg-amber-50 border border-amber-200 p-2 rounded-lg">
                  ⚠️ {warn}
                </div>
              ))}
            </div>
          )}

          {validation.is_valid && validation.errors.length === 0 && (
            <p className="text-xs text-emerald-800 bg-emerald-50 border border-emerald-200 p-2 rounded-lg">
              All essential schema checks and cross-dataset foreign keys validated successfully. Ready for AI Analysis!
            </p>
          )}
        </div>
      )}

      {/* Dataset Preview Modal / Drawer */}
      {previewType && previewData && (
        <div className="bg-cream-card rounded-card border border-cream-border p-5 shadow-card">
          <div className="flex items-center justify-between mb-4 pb-2 border-b border-cream-border">
            <div className="flex items-center gap-2">
              <TableIcon className="w-4 h-4 text-forest" />
              <h3 className="font-bold font-display text-sm text-forest-dark capitalize">
                Cleaned {previewData.file_type} Dataset Preview ({previewData.total_rows} rows)
              </h3>
            </div>
            <button
              onClick={() => setPreviewType(null)}
              className="text-xs text-brandText-secondary hover:text-forest font-semibold"
            >
              ✕ Close Preview
            </button>
          </div>

          <div className="overflow-x-auto max-h-72">
            <table className="w-full text-xs text-left">
              <thead className="bg-cream text-forest font-semibold uppercase text-[10px] tracking-wider border-b border-cream-border">
                <tr>
                  {previewData.columns.map((col) => (
                    <th key={col} className="px-3 py-2">
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-cream-border">
                {previewData.rows.map((row, idx) => (
                  <tr key={idx} className="hover:bg-cream/40">
                    {previewData.columns.map((col) => (
                      <td key={col} className="px-3 py-2 text-brandText-primary whitespace-nowrap">
                        {row[col] !== null ? String(row[col]) : '—'}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Run Full Analysis Primary Bar */}
      <div className="bg-forest text-cream rounded-card p-6 flex flex-col sm:flex-row items-center justify-between gap-4 shadow-card">
        <div>
          <h3 className="font-bold font-display text-base text-white">
            Ready to analyze your menu?
          </h3>
          <p className="text-xs text-cream/70 mt-1 max-w-xl">
            MenuMind AI synthesizes sales trends, profit margins, customer reviews, and food waste logs to generate evidence-backed recommendations.
          </p>
        </div>
        <button
          onClick={() => runAiMutation.mutate()}
          disabled={Boolean(runAiMutation.isPending || (validation && !validation.is_valid))}
          className="shrink-0 inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-amber hover:bg-amber-dark text-forest-dark font-extrabold text-sm transition shadow-card disabled:opacity-50"
        >
          {runAiMutation.isPending ? (
            <>
              <RefreshCw className="w-4 h-4 animate-spin" />
              <span>Analyzing...</span>
            </>
          ) : (
            <>
              <Sparkles className="w-4 h-4" />
              <span>Execute Full AI Analysis</span>
              <ArrowRight className="w-4 h-4" />
            </>
          )}
        </button>
      </div>
    </div>
  );
};

export default UploadPage;
