import React from 'react';
import { AgentActivityEvent } from '../../../types';
import { Cpu, CheckCircle2, Search, Sparkles } from 'lucide-react';

interface Props {
  events: AgentActivityEvent[];
  specialistName?: string;
}

export const AgentActivityStream: React.FC<Props> = ({ events, specialistName }) => {
  if (!events || events.length === 0) return null;

  return (
    <div className="my-3 rounded-lg border border-primary-200/60 bg-primary-50/40 p-3 text-xs">
      <div className="flex items-center justify-between pb-2 mb-2 border-b border-primary-100">
        <div className="flex items-center gap-1.5 font-semibold text-primary-900">
          <Cpu className="w-3.5 h-3.5 text-primary-700" />
          <span>Agent Execution Trace</span>
        </div>
        {specialistName && (
          <span className="px-2 py-0.5 rounded-full bg-primary-100 font-medium text-primary-800">
            {specialistName}
          </span>
        )}
      </div>

      <div className="space-y-1.5">
        {events.map((ev, idx) => {
          let Icon = Sparkles;
          const typeStr = (ev.activity_type || ev.step || ev.status || '').toLowerCase();
          if (
            typeStr.includes('tool') ||
            typeStr.includes('query') ||
            typeStr.includes('search') ||
            typeStr.includes('analyzing') ||
            typeStr.includes('routing')
          ) {
            Icon = Search;
          } else if (
            typeStr.includes('complete') ||
            typeStr.includes('success') ||
            typeStr.includes('done')
          ) {
            Icon = CheckCircle2;
          }

          return (
            <div key={ev.id || idx} className="flex items-start gap-2 text-primary-900/90">
              <Icon className="w-3.5 h-3.5 mt-0.5 text-primary-600 flex-shrink-0" />
              <div className="flex-1 flex items-baseline justify-between">
                <span>{ev.message}</span>
                <span className="text-[10px] text-primary-500 ml-2 font-mono">
                  {ev.timestamp ? new Date(ev.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : ''}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
