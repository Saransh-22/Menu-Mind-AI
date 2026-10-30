import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { AppLayout } from './components/layout/AppLayout';
import OnboardingPage from './features/onboarding/OnboardingPage';
import OverviewPage from './features/overview/OverviewPage';
import UploadPage from './features/upload/UploadPage';
import AnalyticsPage from './features/analytics/AnalyticsPage';
import ReviewInsightsPage from './features/reviews/ReviewInsightsPage';
import RecommendationsPage from './features/recommendations/RecommendationsPage';
import ExperimentsPage from './features/experiments/ExperimentsPage';
import FoodWastePage from './features/waste/FoodWastePage';
import ReportsPage from './features/reports/ReportsPage';
import { AssistantPage } from './features/assistant/AssistantPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 1000 * 60 * 3, // 3 minutes cache
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          {/* Onboarding outside standard dashboard layout */}
          <Route path="/onboarding" element={<OnboardingPage />} />

          {/* SaaS Dashboard Shell */}
          <Route element={<AppLayout />}>
            <Route path="/overview" element={<OverviewPage />} />
            <Route path="/upload" element={<UploadPage />} />
            <Route path="/analytics" element={<AnalyticsPage />} />
            <Route path="/reviews" element={<ReviewInsightsPage />} />
            <Route path="/recommendations" element={<RecommendationsPage />} />
            <Route path="/experiments" element={<ExperimentsPage />} />
            <Route path="/waste" element={<FoodWastePage />} />
            <Route path="/reports" element={<ReportsPage />} />
            <Route path="/assistant" element={<AssistantPage />} />

            {/* Default root path redirects to overview */}
            <Route path="/" element={<Navigate to="/overview" replace />} />
          </Route>

          {/* Catch-all */}
          <Route path="*" element={<Navigate to="/overview" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
