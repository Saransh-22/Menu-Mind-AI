import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  UploadCloud,
  TrendingUp,
  MessageSquareQuote,
  Sparkles,
  FlaskConical,
  Recycle,
  FileSpreadsheet,
  UtensilsCrossed,
  ChevronLeft,
  ChevronRight,
  Store,
  Bot,
} from 'lucide-react';
import { useAppStore } from '../../store';

export const Sidebar: React.FC = () => {
  const { activeRestaurant, activeRun, isSidebarCollapsed, toggleSidebar } = useAppStore();

  const navItems = [
    { label: 'Overview', path: '/overview', icon: LayoutDashboard },
    { label: 'Data Upload', path: '/upload', icon: UploadCloud },
    { label: 'Sales Analytics', path: '/analytics', icon: TrendingUp },
    { label: 'Review Insights', path: '/reviews', icon: MessageSquareQuote },
    { label: 'AI Recommendations', path: '/recommendations', icon: Sparkles },
    { label: 'AI Assistant', path: '/assistant', icon: Bot, highlight: true },
    { label: 'Food Waste', path: '/waste', icon: Recycle },
    { label: 'Reports', path: '/reports', icon: FileSpreadsheet },
  ];

  return (
    <aside
      className={`fixed top-0 left-0 bottom-0 z-40 bg-forest text-cream flex flex-col transition-all duration-300 border-r border-forest-secondary ${
        isSidebarCollapsed ? 'w-20' : 'w-64'
      }`}
    >
      {/* Brand Header */}
      <div className="h-20 flex items-center px-5 border-b border-white/10 justify-between">
        <div className="flex items-center gap-3 overflow-hidden">
          <div className="w-10 h-10 rounded-xl bg-forest-secondary border border-white/10 flex items-center justify-center shrink-0 text-amber shadow-sm">
            <UtensilsCrossed className="w-5 h-5" />
          </div>
          {!isSidebarCollapsed && (
            <div className="leading-tight">
              <span className="font-display font-extrabold text-base tracking-wide text-white block">
                MenuMind<span className="text-amber">.ai</span>
              </span>
              <span className="text-[10px] tracking-widest uppercase font-semibold text-white/50 block">
                Restaurant Intelligence
              </span>
            </div>
          )}
        </div>
        <button
          onClick={toggleSidebar}
          className="text-white/40 hover:text-white p-1 rounded-lg hover:bg-white/5 transition"
          title={isSidebarCollapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
        >
          {isSidebarCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </div>

      {/* Active Restaurant Status Card */}
      {!isSidebarCollapsed && (
        <div className="px-4 py-3 mx-3 my-3 rounded-xl bg-forest-secondary/60 border border-white/5">
          <div className="flex items-center gap-2 text-xs text-amber font-semibold uppercase tracking-wider mb-1">
            <Store className="w-3.5 h-3.5" />
            Active Venue
          </div>
          <div className="font-semibold text-sm text-white truncate">
            {activeRestaurant ? activeRestaurant.name : 'No Venue Selected'}
          </div>
          <div className="text-xs text-white/60 flex items-center justify-between mt-1">
            <span>{activeRestaurant?.city || 'Onboarding'}</span>
            {activeRun && (
              <span className="text-[11px] px-1.5 py-0.5 rounded bg-white/10 text-white font-mono">
                Run #{activeRun.id}
              </span>
            )}
          </div>
        </div>
      )}

      {/* Navigation Links */}
      <nav className="flex-1 px-3 py-3 space-y-1 overflow-y-auto">
        <div className="px-3 pb-2 text-[10px] font-bold uppercase tracking-wider text-white/40">
          {!isSidebarCollapsed && 'Workspace'}
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-forest-secondary text-amber shadow-sm font-semibold'
                    : 'text-white/80 hover:text-white hover:bg-white/5'
                }`
              }
              title={isSidebarCollapsed ? item.label : undefined}
            >
              <Icon className="w-4 h-4 shrink-0" />
              {!isSidebarCollapsed && (
                <span className="truncate flex-1">{item.label}</span>
              )}
              {!isSidebarCollapsed && item.highlight && (
                <span className="w-2 h-2 rounded-full bg-terracotta"></span>
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* Bottom Footer Info */}
      {!isSidebarCollapsed && (
        <div className="p-4 border-t border-white/10 text-xs text-white/40 flex items-center justify-between">
          <span>v2.0 · SaaS Edition</span>
          <span className="flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span> Online
          </span>
        </div>
      )}
    </aside>
  );
};
