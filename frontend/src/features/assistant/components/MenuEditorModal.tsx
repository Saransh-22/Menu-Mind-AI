import React, { useState } from 'react';
import {
  StructuredMenuDraft,
  StructuredMenuCategory,
  StructuredMenuItem,
} from '../../../types';
import { X, Plus, Trash2, Palette, Sparkles, Check } from 'lucide-react';
import { formatCurrency } from '../../../utils/currency';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  initialDraft: StructuredMenuDraft;
  onGenerateDesign: (updatedDraft: StructuredMenuDraft) => void;
  isGenerating?: boolean;
}

export const MenuEditorModal: React.FC<Props> = ({
  isOpen,
  onClose,
  initialDraft,
  onGenerateDesign,
  isGenerating = false,
}) => {
  const [draft, setDraft] = useState<StructuredMenuDraft>(JSON.parse(JSON.stringify(initialDraft)));
  const [isSaved, setIsSaved] = useState(false);

  if (!isOpen) return null;

  const handleUpdateItem = (
    catIdx: number,
    itemIdx: number,
    field: keyof StructuredMenuItem,
    value: any
  ) => {
    const nextCategories = [...draft.categories];
    const targetItem = { ...nextCategories[catIdx].items[itemIdx], [field]: value };
    nextCategories[catIdx].items[itemIdx] = targetItem;

    // Recalculate totals
    const totalItems = nextCategories.reduce((acc, c) => acc + c.items.length, 0);
    setDraft({ ...draft, categories: nextCategories, total_items: totalItems });
    setIsSaved(false);
  };

  const handleDeleteItem = (catIdx: number, itemIdx: number) => {
    const nextCategories = [...draft.categories];
    nextCategories[catIdx].items.splice(itemIdx, 1);
    const totalItems = nextCategories.reduce((acc, c) => acc + c.items.length, 0);
    setDraft({ ...draft, categories: nextCategories, total_items: totalItems });
    setIsSaved(false);
  };

  const handleAddItem = (catIdx: number) => {
    const nextCategories = [...draft.categories];
    const newItem: StructuredMenuItem = {
      name: 'New Signature Dish',
      category: nextCategories[catIdx].category,
      price: 250,
      description: 'Freshly prepared seasonal selection.',
      confidence: 1.0,
    };
    nextCategories[catIdx].items.push(newItem);
    const totalItems = nextCategories.reduce((acc, c) => acc + c.items.length, 0);
    setDraft({ ...draft, categories: nextCategories, total_items: totalItems });
    setIsSaved(false);
  };

  const handleAddCategory = () => {
    const newCategory: StructuredMenuCategory = {
      category: 'New Category',
      items: [
        {
          name: 'First Item',
          category: 'New Category',
          price: 200,
          description: 'Chef recommendation.',
        },
      ],
    };
    const nextCategories = [...draft.categories, newCategory];
    const totalItems = nextCategories.reduce((acc, c) => acc + c.items.length, 0);
    setDraft({ ...draft, categories: nextCategories, total_items: totalItems });
    setIsSaved(false);
  };

  const allItems = draft.categories.flatMap((c) => c.items);
  const avgPrice = allItems.length > 0 ? allItems.reduce((acc, it) => acc + (it.price || 0), 0) / allItems.length : 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="relative w-full max-w-5xl rounded-2xl bg-white shadow-2xl border border-gray-200 flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4 bg-gray-50/80 rounded-t-2xl">
          <div>
            <div className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-emerald-600" />
              <h2 className="text-xl font-bold text-gray-900">
                Structured Menu Editor
              </h2>
            </div>
            <p className="text-xs text-gray-500 mt-0.5">
              Review and refine extracted or proposed menu items before rendering visual artwork.
            </p>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-2 text-gray-400 hover:bg-gray-200 hover:text-gray-700 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Top Summary Bar */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 px-6 py-3 border-b border-gray-100 bg-emerald-50/30 text-xs">
          <div>
            <span className="text-gray-500 block">Menu Title:</span>
            <input
              type="text"
              value={draft.title}
              onChange={(e) => setDraft({ ...draft, title: e.target.value })}
              className="font-semibold text-gray-800 bg-transparent border-b border-dashed border-gray-300 focus:outline-none focus:border-emerald-600 w-full"
            />
          </div>
          <div>
            <span className="text-gray-500 block">Total Items:</span>
            <span className="font-semibold text-gray-900">{draft.total_items} items</span>
          </div>
          <div>
            <span className="text-gray-500 block">Avg Item Price:</span>
            <span className="font-semibold text-gray-900">{formatCurrency(avgPrice, draft.currency)}</span>
          </div>
          <div>
            <span className="text-gray-500 block">Concept:</span>
            <span className="font-medium text-gray-700 truncate block" title={draft.concept}>
              {draft.concept || 'Restaurant Menu'}
            </span>
          </div>
        </div>

        {/* Categories & Items Body */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-6">
          {draft.categories.map((cat, catIdx) => (
            <div key={catIdx} className="rounded-xl border border-gray-200 p-4 bg-white shadow-sm">
              <div className="flex items-center justify-between mb-3 border-b border-gray-100 pb-2">
                <input
                  type="text"
                  value={cat.category}
                  onChange={(e) => {
                    const nextCategories = [...draft.categories];
                    nextCategories[catIdx].category = e.target.value;
                    setDraft({ ...draft, categories: nextCategories });
                  }}
                  className="text-base font-bold text-gray-900 bg-transparent border-b border-transparent hover:border-gray-300 focus:border-emerald-600 focus:outline-none px-1"
                />
                <button
                  onClick={() => handleAddItem(catIdx)}
                  className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-700 hover:text-emerald-800 bg-emerald-50 hover:bg-emerald-100 px-2.5 py-1 rounded-md transition"
                >
                  <Plus className="w-3.5 h-3.5" />
                  Add Dish
                </button>
              </div>

              {/* Items Table */}
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-gray-200 text-gray-500">
                      <th className="pb-2 w-1/4 font-medium">Item Name</th>
                      <th className="pb-2 w-28 font-medium">Price ({draft.currency || '₹'})</th>
                      <th className="pb-2 font-medium">Description</th>
                      <th className="pb-2 w-12 text-center font-medium">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {cat.items.map((item, itemIdx) => (
                      <tr key={itemIdx} className="hover:bg-gray-50/80 transition">
                        <td className="py-2 pr-2">
                          <input
                            type="text"
                            value={item.name}
                            onChange={(e) =>
                              handleUpdateItem(catIdx, itemIdx, 'name', e.target.value)
                            }
                            className="w-full rounded border border-gray-200 px-2 py-1 font-medium text-gray-900 focus:border-emerald-600 focus:outline-none"
                          />
                        </td>
                        <td className="py-2 pr-2">
                          <input
                            type="number"
                            step="any"
                            value={item.price}
                            onChange={(e) =>
                              handleUpdateItem(
                                catIdx,
                                itemIdx,
                                'price',
                                parseFloat(e.target.value) || 0
                              )
                            }
                            className="w-full rounded border border-gray-200 px-2 py-1 font-semibold text-gray-900 focus:border-emerald-600 focus:outline-none"
                          />
                        </td>
                        <td className="py-2 pr-2">
                          <input
                            type="text"
                            value={item.description || ''}
                            onChange={(e) =>
                              handleUpdateItem(catIdx, itemIdx, 'description', e.target.value)
                            }
                            placeholder="Add appetizing dish notes..."
                            className="w-full rounded border border-gray-200 px-2 py-1 text-gray-600 focus:border-emerald-600 focus:outline-none"
                          />
                        </td>
                        <td className="py-2 text-center">
                          <button
                            onClick={() => handleDeleteItem(catIdx, itemIdx)}
                            className="p-1 text-gray-400 hover:text-rose-600 transition"
                            title="Remove item"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))}

          <button
            onClick={handleAddCategory}
            className="w-full py-2.5 rounded-xl border border-dashed border-gray-300 text-xs font-semibold text-gray-600 hover:border-emerald-600 hover:text-emerald-700 bg-gray-50/50 hover:bg-emerald-50/30 transition flex items-center justify-center gap-1.5"
          >
            <Plus className="w-4 h-4" />
            Add New Menu Category
          </button>
        </div>

        {/* Footer Actions */}
        <div className="flex items-center justify-between border-t border-gray-200 px-6 py-4 bg-gray-50/80 rounded-b-2xl">
          <button
            onClick={() => {
              setIsSaved(true);
              setTimeout(() => setIsSaved(false), 2000);
            }}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg border border-gray-300 bg-white text-xs font-semibold text-gray-700 hover:bg-gray-100 transition"
          >
            {isSaved ? <Check className="w-4 h-4 text-emerald-600" /> : null}
            {isSaved ? 'Changes Staged' : 'Save Draft Locally'}
          </button>

          <div className="flex items-center gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-lg text-xs font-medium text-gray-600 hover:bg-gray-200 transition"
            >
              Cancel
            </button>
            <button
              onClick={() => onGenerateDesign(draft)}
              disabled={isGenerating || allItems.length === 0}
              className="inline-flex items-center gap-2 px-5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold shadow-md transition disabled:opacity-50"
            >
              <Palette className="w-4 h-4" />
              {isGenerating ? 'Rendering Visual Menu...' : 'Generate Visual Publication Design'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
