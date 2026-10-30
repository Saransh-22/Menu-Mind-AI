import React from 'react';

interface ActionBadgeProps {
  action: 'IMPROVE' | 'REMOVE' | 'PROMOTE' | 'REPRICE' | 'INSUFFICIENT_EVIDENCE' | string;
}

export const ActionBadge: React.FC<ActionBadgeProps> = ({ action }) => {
  const normalized = action?.toUpperCase();

  switch (normalized) {
    case 'PROMOTE':
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-600"></span>
          PROMOTE
        </span>
      );
    case 'IMPROVE':
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-50 text-blue-800 border border-blue-200">
          <span className="w-1.5 h-1.5 rounded-full bg-blue-600"></span>
          IMPROVE
        </span>
      );
    case 'REMOVE':
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-terracotta-light text-terracotta border border-terracotta-border">
          <span className="w-1.5 h-1.5 rounded-full bg-terracotta"></span>
          REMOVE
        </span>
      );
    case 'REPRICE':
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-light text-amber-dark border border-amber/30">
          <span className="w-1.5 h-1.5 rounded-full bg-amber"></span>
          REPRICE
        </span>
      );
    default:
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-700 border border-gray-200">
          <span className="w-1.5 h-1.5 rounded-full bg-gray-400"></span>
          MORE EVIDENCE
        </span>
      );
  }
};

export default ActionBadge;
