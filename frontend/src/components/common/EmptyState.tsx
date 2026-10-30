import React from 'react';
import { HelpCircle } from 'lucide-react';

interface EmptyStateProps {
  icon?: any;
  title: string;
  description: string;
  actionText?: string;
  onAction?: () => void;
  action?: React.ReactNode;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon: Icon = HelpCircle,
  title,
  description,
  actionText,
  onAction,
  action,
}) => {
  const renderIcon = () => {
    if (React.isValidElement(Icon)) return Icon;
    const IconComp = Icon || HelpCircle;
    return <IconComp className="w-8 h-8" />;
  };

  return (
    <div className="bg-white rounded-xl border border-stone-200 p-12 text-center shadow-sm max-w-xl mx-auto my-8">
      <div className="w-16 h-16 rounded-2xl bg-forest/5 text-forest mx-auto flex items-center justify-center mb-4">
        {renderIcon()}
      </div>
      <h3 className="text-lg font-bold font-serif text-stone-900 mb-2">{title}</h3>
      <p className="text-sm text-stone-500 leading-relaxed mb-6 max-w-md mx-auto">
        {description}
      </p>
      {action ? (
        <div className="flex justify-center">{action}</div>
      ) : actionText && onAction ? (
        <button
          onClick={onAction}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-forest hover:bg-forest-secondary text-cream text-sm font-semibold transition-all shadow-sm"
        >
          {actionText}
        </button>
      ) : null}
    </div>
  );
};

export default EmptyState;
