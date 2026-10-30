import React, { useState } from 'react';
import { GeneratedMenuDesign } from '../../../types';
import {
  X,
  Download,
  RefreshCw,
  Printer,
  Sparkles,
  Layout,
  ExternalLink,
} from 'lucide-react';
import { exportMenuDesignUrl, regenerateMenuDesign } from '../../../api/assistant';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  design: GeneratedMenuDesign;
  conversationId: string;
  onDesignUpdated?: (newDesign: GeneratedMenuDesign) => void;
}

const STYLE_OPTIONS = [
  { id: 'traditional_indian', name: 'Traditional Indian', desc: 'Warm spices, golden arches & deep crimson' },
  { id: 'cafe_bakery', name: 'Cafe & Bakery', desc: 'Artisanal sage green, latte cream & clean bistro lines' },
  { id: 'luxury_black_gold', name: 'Luxury Black & Gold', desc: 'Midnight obsidian, metallic gold & serif typography' },
  { id: 'modern_minimalist', name: 'Modern Minimalist', desc: 'Crisp swiss typography, subtle slate borders & whitespace' },
];

const LAYOUT_OPTIONS = [
  { id: 'single_page', name: 'Single Page A4' },
  { id: 'bi_fold', name: 'Bi-Fold Spread' },
  { id: 'digital_board', name: '16:9 Digital Board' },
];

export const MenuDesignStudioModal: React.FC<Props> = ({
  isOpen,
  onClose,
  design: initialDesign,
  conversationId,
  onDesignUpdated,
}) => {
  const [design, setDesign] = useState<GeneratedMenuDesign>(initialDesign);
  const [selectedStyle, setSelectedStyle] = useState(
    initialDesign.style || initialDesign.style_preset || 'modern_minimalist'
  );
  const [selectedLayout, setSelectedLayout] = useState(
    initialDesign.layout_format || initialDesign.layout || initialDesign.spec?.layout || 'single_page'
  );
  const [isRegenerating, setIsRegenerating] = useState(false);

  if (!isOpen) return null;

  const designId = design.design_id || design.id || '';
  const designTitle = design.title || design.draft_title || 'Menu Design';
  const totalItems = design.menu_draft?.total_items || design.total_items || 0;

  const handleRegenerate = async () => {
    if (!designId) return;
    setIsRegenerating(true);
    try {
      const updated = await regenerateMenuDesign(conversationId, designId, {
        style: selectedStyle,
        layout: selectedLayout,
      });
      setDesign(updated);
      if (onDesignUpdated) onDesignUpdated(updated);
    } catch (err) {
      console.error('Failed to regenerate design:', err);
    } finally {
      setIsRegenerating(false);
    }
  };

  const handlePrint = () => {
    const iframe = document.getElementById('menu-design-preview-frame') as HTMLIFrameElement;
    if (iframe && iframe.contentWindow) {
      iframe.contentWindow.focus();
      iframe.contentWindow.print();
    }
  };

  const exportHtmlUrl = exportMenuDesignUrl(conversationId, designId, 'html');
  const exportSvgUrl = exportMenuDesignUrl(conversationId, designId, 'svg');

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-md p-4 overflow-y-auto">
      <div className="relative w-full max-w-6xl rounded-2xl bg-white shadow-2xl border border-gray-200 flex flex-col h-[92vh]">
        {/* Top Header */}
        <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4 bg-gray-50/90 rounded-t-2xl">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-100 text-emerald-700 flex items-center justify-center">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                Menu Design Studio
                <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 font-semibold uppercase tracking-wider">
                  Publication Grade
                </span>
              </h2>
              <p className="text-xs text-gray-500">
                {designTitle} • {totalItems} items rendered with zero text distortion.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handlePrint}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gray-300 bg-white text-xs font-semibold text-gray-700 hover:bg-gray-100 transition"
              title="Print directly or save as PDF"
            >
              <Printer className="w-4 h-4 text-gray-600" />
              Print / Save PDF
            </button>
            <a
              href={exportHtmlUrl}
              download={`${designTitle.replace(/\s+/g, '_')}_menu.html`}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gray-300 bg-white text-xs font-semibold text-gray-700 hover:bg-gray-100 transition"
            >
              <Download className="w-4 h-4 text-emerald-600" />
              HTML Bundle
            </a>
            <a
              href={exportSvgUrl}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gray-300 bg-white text-xs font-semibold text-gray-700 hover:bg-gray-100 transition"
            >
              <ExternalLink className="w-4 h-4 text-blue-600" />
              Raw SVG
            </a>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-gray-400 hover:bg-gray-200 hover:text-gray-700 transition ml-2"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content Split: Left Controls, Right Preview */}
        <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 overflow-hidden bg-gray-100">
          {/* Controls Panel */}
          <div className="lg:col-span-4 p-5 bg-white border-r border-gray-200 flex flex-col justify-between overflow-y-auto space-y-6">
            <div className="space-y-5">
              <div>
                <label className="text-xs font-bold text-gray-700 uppercase tracking-wider block mb-2">
                  Visual Theme & Artwork Style
                </label>
                <div className="space-y-2">
                  {STYLE_OPTIONS.map((st) => (
                    <div
                      key={st.id}
                      onClick={() => setSelectedStyle(st.id)}
                      className={`cursor-pointer rounded-xl p-3 border text-xs transition ${
                        selectedStyle === st.id
                          ? 'border-emerald-600 bg-emerald-50/60 ring-2 ring-emerald-500/20'
                          : 'border-gray-200 hover:border-gray-300 bg-white'
                      }`}
                    >
                      <div className="font-semibold text-gray-900">{st.name}</div>
                      <div className="text-[11px] text-gray-500 mt-0.5">{st.desc}</div>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <label className="text-xs font-bold text-gray-700 uppercase tracking-wider block mb-2">
                  Layout Format
                </label>
                <div className="grid grid-cols-1 gap-2">
                  {LAYOUT_OPTIONS.map((lo) => (
                    <button
                      key={lo.id}
                      onClick={() => setSelectedLayout(lo.id)}
                      className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-xs font-medium transition text-left ${
                        selectedLayout === lo.id
                          ? 'border-emerald-600 bg-emerald-50/50 text-emerald-900 font-semibold'
                          : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300'
                      }`}
                    >
                      <Layout className="w-4 h-4 text-emerald-600" />
                      {lo.name}
                    </button>
                  ))}
                </div>
              </div>

              {/* Active Palette Indicators */}
              <div>
                <label className="text-xs font-bold text-gray-700 uppercase tracking-wider block mb-2">
                  Active Color Palette
                </label>
                <div className="flex items-center gap-2">
                  {(design.spec?.palette || design.palette || ['#1E3A8A', '#F59E0B', '#10B981']).map((color, idx) => (
                    <div
                      key={idx}
                      className="w-8 h-8 rounded-lg shadow-sm border border-gray-300 flex items-center justify-center font-mono text-[9px] font-bold text-white uppercase"
                      style={{ backgroundColor: color }}
                      title={color}
                    />
                  ))}
                </div>
              </div>
            </div>

            <div className="pt-4 border-t border-gray-200">
              <button
                onClick={handleRegenerate}
                disabled={isRegenerating}
                className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold shadow-md transition disabled:opacity-50"
              >
                <RefreshCw className={`w-4 h-4 ${isRegenerating ? 'animate-spin' : ''}`} />
                {isRegenerating ? 'Regenerating Artwork...' : 'Re-render Menu Design'}
              </button>
            </div>
          </div>

          {/* Right Preview Frame */}
          <div className="lg:col-span-8 p-6 flex flex-col items-center justify-center overflow-auto bg-gray-200/60">
            <div className="w-full h-full max-w-3xl rounded-xl shadow-2xl overflow-hidden bg-white border border-gray-300 flex flex-col">
              <iframe
                id="menu-design-preview-frame"
                title="Visual Menu Design Preview"
                srcDoc={design.html_preview || design.html_source || '<html><body><p>Loading menu...</p></body></html>'}
                className="w-full flex-1 border-0"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
