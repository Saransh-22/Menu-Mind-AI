import React from 'react';
import { Outlet, Navigate, useLocation } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { useAppStore } from '../../store';
import { FloatingAssistant } from '../assistant/FloatingAssistant';
import { AssistantDrawer } from '../assistant/AssistantDrawer';

export const AppLayout: React.FC = () => {
  const { isSidebarCollapsed, activeRestaurant } = useAppStore();
  const location = useLocation();

  // If no restaurant is selected and not on onboarding, redirect to onboarding
  if (!activeRestaurant && location.pathname !== '/onboarding') {
    return <Navigate to="/onboarding" replace />;
  }

  return (
    <div className="min-h-screen bg-cream text-brandText-primary">
      <Sidebar />
      <Header />
      <main
        className={`transition-all duration-300 pt-20 px-6 pb-12 max-w-7xl ${
          isSidebarCollapsed ? 'ml-20' : 'ml-64'
        }`}
      >
        <Outlet />
      </main>
      <FloatingAssistant />
      <AssistantDrawer />
    </div>
  );
};
