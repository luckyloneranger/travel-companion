import { useCallback, useEffect } from 'react';
import { Routes, Route } from 'react-router-dom';
import { Header } from '@/components/layout/Header';
import { PageContainer } from '@/components/layout/PageContainer';
import { ChatPanel } from '@/components/trip/ChatPanel';
import { WizardForm } from '@/components/trip/WizardForm';
import { PlanningDashboard } from '@/components/trip/PlanningDashboard';
import { JourneyPreview } from '@/components/trip/JourneyPreview';
import { DayCard } from '@/components/trip/DayCard';
import { BudgetSummary } from '@/components/trip/BudgetSummary';
import { SharedTrip } from '@/pages/SharedTrip';
import { useStreamingPlan } from '@/hooks/useStreamingPlan';
import { useStreamingDayPlans } from '@/hooks/useStreamingDayPlans';
import { useUIStore } from '@/stores/uiStore';
import { useTripStore } from '@/stores/tripStore';
import { useAuthStore } from '@/stores/authStore';
import { Button } from '@/components/ui/button';
import { ArrowLeft, MessageSquare, PlusCircle, AlertCircle } from 'lucide-react';

function App() {
  const { phase, isLoading, error, setError, setPhase, resetUI } = useUIStore();
  const { journey, dayPlans, costBreakdown, reset: resetTrip } = useTripStore();
  const { fetchUser } = useAuthStore();
  const { startPlanning, cancelPlanning } = useStreamingPlan();
  const { startGenerating, cancelGenerating } = useStreamingDayPlans();

  // Restore session from sessionStorage on page refresh
  useEffect(() => {
    const savedTripId = sessionStorage.getItem('tc_tripId');
    const savedPhase = sessionStorage.getItem('tc_phase');
    if (savedTripId && savedPhase && savedPhase !== 'input' && savedPhase !== 'planning') {
      useTripStore.getState().loadTrip(savedTripId).then(() => {
        useUIStore.getState().setPhase(savedPhase as 'preview' | 'day-plans');
      }).catch(() => {
        sessionStorage.removeItem('tc_tripId');
        sessionStorage.removeItem('tc_phase');
      });
    }
  }, []);

  useEffect(() => {
    fetchUser();
    const interval = setInterval(fetchUser, 30 * 60 * 1000);
    return () => clearInterval(interval);
  }, [fetchUser]);

  const handleGenerateDayPlans = useCallback(() => {
    startGenerating();
  }, [startGenerating]);

  const handleOpenChat = useCallback(() => {
    useUIStore.getState().openChat('journey');
  }, []);

  const handleOpenDayPlanChat = useCallback(() => {
    useUIStore.getState().openChat('day_plans');
  }, []);

  const handleBackToPreview = useCallback(() => {
    setPhase('preview');
  }, [setPhase]);

  const handleNewTrip = useCallback(() => {
    resetTrip();
    resetUI();
  }, [resetTrip, resetUI]);

  // Browser back/forward button navigation
  useEffect(() => {
    const validPhases = new Set(['input', 'preview', 'day-plans']);
    const handler = (e: PopStateEvent) => {
      const targetPhase = e.state?.phase as string | undefined;
      if (targetPhase && validPhases.has(targetPhase)) {
        useUIStore.setState({ phase: targetPhase as 'input' | 'preview' | 'day-plans' });
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

  // Determine which cancel handler to use based on context
  const handleCancelPlanning = useCallback(() => {
    // If we came from preview (day plan generation), go back to preview
    if (journey) {
      cancelGenerating();
    } else {
      cancelPlanning();
    }
  }, [journey, cancelGenerating, cancelPlanning]);

  // Group day plans by city
  const dayPlansByCity = dayPlans
    ? dayPlans.reduce<Record<string, typeof dayPlans>>((acc, plan) => {
        const city = plan.city_name;
        if (!acc[city]) acc[city] = [];
        acc[city].push(plan);
        return acc;
      }, {})
    : {};

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

              {phase === 'preview' && journey && (
                <div key="preview" className="animate-fade-in-up">
                  <JourneyPreview
                    onGenerateDayPlans={handleGenerateDayPlans}
                    onOpenChat={handleOpenChat}
                    onNewTrip={handleNewTrip}
                  />
                </div>
              )}

              {phase === 'day-plans' && dayPlans && dayPlans.length > 0 && (
                <div key="day-plans" className="animate-fade-in-up space-y-6">
                  {/* Day plans header */}
                  <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 sm:gap-4">
                    <div className="flex items-center gap-3">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={handleBackToPreview}
                      >
                        <ArrowLeft className="h-4 w-4" />
                        Back to Overview
                      </Button>
                      <div>
                        <h2 className="text-lg font-display font-bold text-text-primary">
                          Day Plans
                        </h2>
                        <p className="text-xs text-text-muted">
                          {dayPlans.length} {dayPlans.length === 1 ? 'day' : 'days'} &middot;{' '}
                          {dayPlans.reduce((sum, d) => sum + d.activities.length, 0)} activities
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button variant="outline" size="sm" onClick={handleOpenDayPlanChat}>
                        <MessageSquare className="h-4 w-4" />
                        Edit via Chat
                      </Button>
                      <Button variant="ghost" size="sm" onClick={handleNewTrip}>
                        <PlusCircle className="h-4 w-4" />
                        New Trip
                      </Button>
                    </div>
                  </div>

                  {costBreakdown && (
                    <BudgetSummary costBreakdown={costBreakdown} totalDays={dayPlans.length} />
                  )}

                  {/* Day plans grouped by city */}
                  {Object.entries(dayPlansByCity).map(([cityName, plans]) => (
                    <div key={cityName} className="space-y-3">
                      <h3 className="text-sm font-semibold text-text-muted uppercase tracking-wider px-1">
                        {cityName}
                      </h3>
                      <div className="space-y-4">
                        {plans.map((plan) => (
                          <DayCard key={plan.day_number} dayPlan={plan} />
                        ))}
                      </div>
                    </div>
                  ))}
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
