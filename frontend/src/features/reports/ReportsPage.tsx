import React, { useState } from 'react';
import {
  FileText,
  Download,
  ExternalLink,
  Eye,
  CheckCircle2,
  Calendar,
  Building,
  Sparkles,
  CheckSquare,
  FileSpreadsheet,
} from 'lucide-react';
import { useAppStore } from '../../store';
import { getHtmlReportUrl, getCsvReportUrl } from '../../api/reports';
import EmptyState from '../../components/common/EmptyState';

export default function ReportsPage() {
  const { activeRestaurant, activeRun } = useAppStore();
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);

  if (!activeRun || !activeRestaurant) {
    return (
      <EmptyState
        title="No Active Run Selected"
        description="Select a restaurant and analysis run to generate and export executive reports."
      />
    );
  }

  const htmlReportUrl = getHtmlReportUrl(activeRun.id);
  const csvReportUrl = getCsvReportUrl(activeRun.id);

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div>
        <h1 className="text-2xl font-bold text-stone-900 font-serif">Executive Reports & Exports</h1>
        <p className="text-sm text-stone-500">
          Generate comprehensive audit deliverables, human-in-the-loop decisions, and spreadsheet exports for executive review.
        </p>
      </div>

      {/* Run Summary Meta Card */}
      <div className="rounded-xl border border-stone-200 bg-white p-6 shadow-sm">
        <h2 className="text-base font-semibold text-stone-900 font-serif mb-4">Current Run Metadata</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4 text-xs">
          <div className="rounded-lg bg-stone-50 p-3">
            <span className="text-stone-400 block text-[11px] mb-1">Restaurant</span>
            <div className="flex items-center gap-2 font-bold text-stone-800 text-sm">
              <Building className="h-4 w-4 text-forest" />
              <span>{activeRestaurant.name}</span>
            </div>
            {activeRestaurant.city && <span className="text-stone-500">{activeRestaurant.city}</span>}
          </div>

          <div className="rounded-lg bg-stone-50 p-3">
            <span className="text-stone-400 block text-[11px] mb-1">Analysis Period</span>
            <div className="flex items-center gap-2 font-bold text-stone-800 text-sm">
              <Calendar className="h-4 w-4 text-amber" />
              <span>
                {activeRun.period_start || 'All Time'} - {activeRun.period_end || 'Present'}
              </span>
            </div>
            <span className="text-stone-500">Run ID: #{activeRun.id}</span>
          </div>

          <div className="rounded-lg bg-stone-50 p-3">
            <span className="text-stone-400 block text-[11px] mb-1">Data Quality</span>
            <div className="flex items-center gap-2 font-bold text-forest text-sm">
              <CheckCircle2 className="h-4 w-4 text-forest" />
              <span>{activeRun.data_quality_score ? `${activeRun.data_quality_score.toFixed(0)} / 100` : 'Verified'}</span>
            </div>
            <span className="text-stone-500">Integrity Validated</span>
          </div>

          <div className="rounded-lg bg-stone-50 p-3">
            <span className="text-stone-400 block text-[11px] mb-1">Execution Status</span>
            <div className="flex items-center gap-2 font-bold text-forest text-sm capitalize">
              <Sparkles className="h-4 w-4 text-forest" />
              <span>{activeRun.status || 'Active'}</span>
            </div>
            <span className="text-stone-500">Ready for Export</span>
          </div>
        </div>
      </div>

      {/* Export Cards Grid */}
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        {/* Full HTML Executive Report Card */}
        <div className="flex flex-col justify-between rounded-xl border border-stone-200 bg-white p-6 shadow-sm hover:border-forest/40 transition-colors">
          <div>
            <div className="flex items-center gap-3 mb-4">
              <div className="rounded-xl bg-forest/10 p-3 text-forest">
                <FileText className="h-7 w-7" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-stone-900 font-serif">Comprehensive HTML Audit</h3>
                <span className="rounded bg-forest/10 px-2 py-0.5 text-[10px] font-semibold text-forest uppercase">
                  Executive Deliverable
                </span>
              </div>
            </div>

            <p className="text-xs text-stone-600 leading-relaxed">
              Complete, self-contained HTML report detailing data quality scores, revenue breakdown, matrix positioning,
              customer sentiment highlights, waste exposure, and all prioritized recommendations.
            </p>

            <ul className="mt-4 space-y-1.5 text-xs text-stone-500">
              <li className="flex items-center gap-2">
                <CheckCircle2 className="h-3.5 w-3.5 text-forest" />
                <span>Executive visual dashboard with embedded styling</span>
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="h-3.5 w-3.5 text-forest" />
                <span>Human-in-the-loop manager approval statuses</span>
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="h-3.5 w-3.5 text-forest" />
                <span>Print-friendly and archival ready</span>
              </li>
            </ul>
          </div>

          <div className="mt-6 flex flex-wrap items-center gap-3 border-t border-stone-100 pt-4">
            <a
              href={htmlReportUrl}
              download={`menumind_report_run_${activeRun.id}.html`}
              className="flex items-center gap-2 rounded-lg bg-forest px-4 py-2 text-xs font-semibold text-cream hover:bg-forest-secondary transition-colors"
            >
              <Download className="h-3.5 w-3.5" />
              Download HTML Report
            </a>
            <button
              onClick={() => setIsPreviewOpen(true)}
              className="flex items-center gap-2 rounded-lg border border-stone-300 bg-white px-4 py-2 text-xs font-semibold text-stone-700 hover:bg-stone-50 transition-colors"
            >
              <Eye className="h-3.5 w-3.5" />
              Live Preview
            </button>
            <a
              href={htmlReportUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 text-xs font-semibold text-forest hover:underline"
            >
              <ExternalLink className="h-3.5 w-3.5" />
              Open New Tab
            </a>
          </div>
        </div>

        {/* Recommendations & Actions CSV Export Card */}
        <div className="flex flex-col justify-between rounded-xl border border-stone-200 bg-white p-6 shadow-sm hover:border-forest/40 transition-colors">
          <div>
            <div className="flex items-center gap-3 mb-4">
              <div className="rounded-xl bg-amber/10 p-3 text-amber">
                <FileSpreadsheet className="h-7 w-7" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-stone-900 font-serif">Recommendations CSV Export</h3>
                <span className="rounded bg-amber/15 px-2 py-0.5 text-[10px] font-semibold text-amber uppercase">
                  Operational Spreadsheet
                </span>
              </div>
            </div>

            <p className="text-xs text-stone-600 leading-relaxed">
              Export all recommendations, calculated metrics, margin projections, customer sentiment indicators, and manager
              approvals formatted for Microsoft Excel, Google Sheets, or ERP ingestion.
            </p>

            <ul className="mt-4 space-y-1.5 text-xs text-stone-500">
              <li className="flex items-center gap-2">
                <CheckCircle2 className="h-3.5 w-3.5 text-forest" />
                <span>Compatible with Excel, Google Sheets, POS systems</span>
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="h-3.5 w-3.5 text-forest" />
                <span>Includes action tags (IMPROVE, REMOVE, PROMOTE, REPRICE)</span>
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="h-3.5 w-3.5 text-forest" />
                <span>Manager notes and decision timestamps</span>
              </li>
            </ul>
          </div>

          <div className="mt-6 flex items-center gap-3 border-t border-stone-100 pt-4">
            <a
              href={csvReportUrl}
              download={`menumind_recommendations_run_${activeRun.id}.csv`}
              className="flex items-center gap-2 rounded-lg bg-forest px-4 py-2 text-xs font-semibold text-cream hover:bg-forest-secondary transition-colors"
            >
              <Download className="h-3.5 w-3.5" />
              Download CSV Spreadsheet
            </a>
          </div>
        </div>
      </div>

      {/* Live Preview Modal */}
      {isPreviewOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-stone-900/60 p-4 backdrop-blur-sm">
          <div className="flex h-[90vh] w-full max-w-5xl flex-col rounded-2xl bg-white shadow-2xl">
            <div className="flex items-center justify-between border-b border-stone-200 px-6 py-4">
              <div className="flex items-center gap-2">
                <FileText className="h-5 w-5 text-forest" />
                <h3 className="text-base font-bold text-stone-900 font-serif">
                  Report Preview – Run #{activeRun.id}
                </h3>
              </div>
              <div className="flex items-center gap-3">
                <a
                  href={htmlReportUrl}
                  download={`menumind_report_run_${activeRun.id}.html`}
                  className="flex items-center gap-1.5 rounded-lg bg-forest px-3 py-1.5 text-xs font-semibold text-cream hover:bg-forest-secondary"
                >
                  <Download className="h-3.5 w-3.5" />
                  Download
                </a>
                <button
                  onClick={() => setIsPreviewOpen(false)}
                  className="rounded-lg border border-stone-200 px-3 py-1.5 text-xs font-medium text-stone-600 hover:bg-stone-50"
                >
                  Close
                </button>
              </div>
            </div>

            <div className="flex-1 overflow-hidden p-2">
              <iframe
                src={htmlReportUrl}
                title="Report Live Preview"
                className="h-full w-full rounded-xl border border-stone-200"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
