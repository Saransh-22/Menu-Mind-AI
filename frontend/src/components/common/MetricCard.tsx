import React from 'react';

interface MetricCardProps {
  label?: string;
  title?: string;
  value: string | number;
  subValue?: string;
  subtext?: string;
  icon?: any;
  badge?: string;
  badgeColor?: 'green' | 'amber' | 'terracotta';
  status?: 'positive' | 'negative' | 'neutral' | 'warning';
}

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  title,
  value,
  subValue,
  subtext,
  icon: Icon,
  badge,
  badgeColor = 'green',
  status,
}) => {
  const displayLabel = title || label;
  const displaySub = subtext || subValue;

  const badgeClasses = {
    green: 'bg-emerald-50 text-emerald-800 border-emerald-200',
    amber: 'bg-amber-50 text-amber-800 border-amber-200',
    terracotta: 'bg-terracotta-light text-terracotta border-terracotta-border',
  }[badgeColor];

  const statusColor = status === 'positive'
    ? 'text-forest'
    : status === 'negative'
    ? 'text-terracotta'
    : status === 'warning'
    ? 'text-amber'
    : 'text-stone-700';

  const renderIcon = () => {
    if (!Icon) return null;
    if (React.isValidElement(Icon)) {
      return Icon;
    }
    const IconComp = Icon;
    return <IconComp className="w-4 h-4" />;
  };

  return (
    <div className="bg-white rounded-xl border border-stone-200 p-5 shadow-sm hover:shadow-md transition-all duration-200">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs uppercase font-semibold tracking-wider text-stone-500">
          {displayLabel}
        </span>
        {Icon && (
          <div className="w-8 h-8 rounded-lg bg-stone-50 flex items-center justify-center">
            {renderIcon()}
          </div>
        )}
      </div>
      <div className="flex items-baseline gap-2">
        <span className={`text-2xl font-bold font-serif tabular-nums tracking-tight ${statusColor}`}>
          {value}
        </span>
        {badge && (
          <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${badgeClasses}`}>
            {badge}
          </span>
        )}
      </div>
      {displaySub && (
        <p className="text-xs text-stone-400 mt-1.5 flex items-center gap-1 font-medium">
          {displaySub}
        </p>
      )}
    </div>
  );
};

export default MetricCard;
