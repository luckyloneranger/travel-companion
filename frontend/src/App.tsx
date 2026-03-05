import { useCallback, useEffect } from 'react';
import { Routes, Route } from 'react-router-dom';
import { Header } from '@/components/layout/Header';
import { PageContainer } from '@/components/layout/PageContainer';
import { ChatPanel } from '@/components/trip/ChatPanel';
import { AUTH_REFRESH_INTERVAL_MS } from '@/constants';
import { WizardForm } from '@/components/trip/WizardForm';
import { PlanningDashboard } from '@/components/trip/PlanningDashboard';
import { JourneyDashboard } from '@/components/trip/JourneyDashboard';
import { SharedTrip } from '@/pages/SharedTrip';
import { useStreamingPlan } from '@/hooks/useStreamingPlan';
import { useStreamingDayPlans } from '@/hooks/useStreamingDayPlans';
import { useUIStore } from '@/stores/uiStore';
import { useTripStore } from '@/stores/tripStore';
import { useAuthStore } from '@/stores/authStore';
import { AlertCircle } from 'lucide-react';

function App() {
  const { phase, isLoading, error, setError } = useUIStore();
  const { journey } = useTripStore();
  const { fetchUser } = useAuthStore();
  const { startPlanning, cancelPlanning } = useStreamingPlan();
  const { startGenerating, cancelGenerating } = useStreamingDayPlans();

  // Restore session from sessionStorage on page refresh
  useEffect(() => {
    const savedTripId = sessionStorage.getItem('tc_tripId');
    const savedPhase = sessionStorage.getItem('tc_phase');
    if (savedTripId && savedPhase && savedPhase !== 'input' && savedPhase !== 'planning') {
      useTripStore.getState().loadTrip(savedTripId).then(() => {
        // All trips load into preview now (day plans show inline)
        useUIStore.getState().setPhase('preview');
      }).catch(() => {
        sessionStorage.removeItem('tc_tripId');
        sessionStorage.removeItem('tc_phase');
      });
    }
  }, []);

  useEffect(() => {
    fetchUser();
    const interval = setInterval(fetchUser, AUTH_REFRESH_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [fetchUser]);

  const handleGenerateDayPlans = useCallback(() => {
    startGenerating();
  }, [startGenerating]);

  const handleOpenChat = useCallback(() => {
    useUIStore.getState().openChat('journey');
  }, []);

  // Browser back/forward button navigation
  useEffect(() => {
    const validPhases = new Set(['input', 'preview', 'day-plans']);
    const handler = (e: PopStateEvent) => {
      const targetPhase = e.state?.phase as string | undefined;
      if (targetPhase && validPhases.has(targetPhase)) {
        useUIStore.setState({ phase: targetPhase as 'input' | 'preview' });
      }
    };
    window.addEventListener('popstate', handler);
    return () => window.removeEventListener('popstate', handler);
  }, []);

  // ESC to dismiss error
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && error) {
        setError(null);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [error, setError]);

  // Cancel handler for journey planning
  const handleCancelPlanning = useCallback(() => {
    cancelPlanning();
  }, [cancelPlanning]);

  return (
    <div className="min-h-screen bg-surface-dim">
      <a href="#main-content" className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:bg-primary-600 focus:text-white focus:px-4 focus:py-2 focus:rounded-md focus:top-2 focus:left-2">
        Skip to content
      </a>
      <Routes>
        <Route path="/shared/:token" element={<SharedTrip />} />
        <Route path="*" element={
          <>
            <Header />
            <PageContainer>
              {error && (
                <div className="max-w-lg mx-auto mb-4 animate-fade-in-up">
                  <div role="alert" className="bg-red-50 dark:bg-red-950/50 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 px-4 py-3 rounded-lg flex items-start gap-3">
                    <AlertCircle className="h-5 w-5 shrink-0 mt-0.5" />
                    <p className="text-sm flex-1">{error}</p>
                    <button
                      onClick={() => setError(null)}
                      className="text-red-400 hover:text-red-600 dark:hover:text-red-200 font-bold text-lg leading-none shrink-0"
                      aria-label="Dismiss error"
                    >
                      &times;
                    </button>
                  </div>
                </div>
              )}

              {phase === 'input' && (
                <div key="input" className="animate-fade-in-up">
                  <WizardForm onSubmit={startPlanning} isLoading={isLoading} />
                </div>
              )}

              {phase === 'planning' && (
                <div key="planning" className="animate-fade-in-up">
                  <PlanningDashboard onCancel={handleCancelPlanning} />
                </div>
              )}

              {(phase === 'preview' || phase === 'day-plans') && journey && (
                <div key="preview" className="animate-fade-in-up">
                  <JourneyDashboard
                    onGenerateDayPlans={handleGenerateDayPlans}
                    onCancelDayPlans={cancelGenerating}
                    onOpenChat={handleOpenChat}
                  />
                </div>
              )}
            </PageContainer>

            <ChatPanel />
          </>
        } />
      </Routes>
    </div>
  );
}

export default App;
