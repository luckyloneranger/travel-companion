import { useCallback, useEffect, useState } from 'react';
import { Routes, Route, useNavigate, useParams, useLocation } from 'react-router-dom';
import { Header } from '@/components/layout/Header';
import { PageContainer } from '@/components/layout/PageContainer';
import { ChatPanel } from '@/components/trip/ChatPanel';
import { AUTH_REFRESH_INTERVAL_MS } from '@/constants';
import { WizardForm } from '@/components/trip/WizardForm';
import { PlanningDashboard } from '@/components/trip/PlanningDashboard';
import { JourneyDashboard } from '@/components/trip/JourneyDashboard';
import { SharedTrip } from '@/pages/SharedTrip';
import { SignIn, SignInModal } from '@/pages/SignIn';
import { useStreamingPlan } from '@/hooks/useStreamingPlan';
import { useStreamingDayPlans } from '@/hooks/useStreamingDayPlans';
import { useUIStore } from '@/stores/uiStore';
import { useTripStore } from '@/stores/tripStore';
import { useAuthStore } from '@/stores/authStore';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { AlertCircle } from 'lucide-react';
import { ToastContainer } from '@/components/ui/toast';

/** Sub-component that loads a trip by URL param /trips/:id */
function TripLoader() {
  const { id } = useParams<{ id: string }>();
  const { journey } = useTripStore();
  const tripId = useTripStore((s) => s.tripId);
  const { phase } = useUIStore();
  const navigate = useNavigate();
  const [loadError, setLoadError] = useState(false);

  useEffect(() => {
    if (id && id !== tripId && phase !== 'input') {
      setLoadError(false);
      useTripStore.getState().loadTrip(id).then(() => {
        useUIStore.getState().setPhase('preview');
      }).catch(() => {
        setLoadError(true);
      });
    }
  }, [id, tripId, phase]);

  if (phase === 'planning') {
    return (
      <div key="planning" className="animate-fade-in-up">
        <PlanningDashboard onCancel={() => useUIStore.getState().setPhase('input')} />
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="text-center py-16 space-y-4">
        <p className="text-lg font-display font-semibold text-text-primary">Trip not found</p>
        <p className="text-sm text-text-muted">This trip doesn't exist or you don't have access to it.</p>
        <div className="flex items-center justify-center gap-3">
          <button
            type="button"
            onClick={() => {
              setLoadError(false);
              useTripStore.getState().loadTrip(id!).then(() => {
                useUIStore.getState().setPhase('preview');
              }).catch(() => {
                setLoadError(true);
              });
            }}
            className="px-4 py-2 text-sm font-medium bg-primary-600 text-white rounded-md hover:bg-primary-700"
          >
            Retry
          </button>
          <button
            type="button"
            onClick={() => {
              useUIStore.getState().resetUI();
              useTripStore.getState().reset();
              navigate('/');
            }}
            className="text-sm text-primary-600 dark:text-primary-400 hover:underline"
          >
            Go back to home
          </button>
        </div>
      </div>
    );
  }

  if (!journey) {
    return (
      <div className="text-center py-12 text-text-muted">
        Loading trip...
      </div>
    );
  }

  return null; // JourneyDashboard rendered by parent based on phase
}

function MainApp() {
  const { phase, isLoading, error, setError } = useUIStore();
  const showSignIn = useUIStore((s) => s.showSignIn);
  const closeSignIn = useUIStore((s) => s.closeSignIn);
  const { journey, tripId } = useTripStore();
  const { fetchUser, user } = useAuthStore();
  const { startPlanning, cancelPlanning } = useStreamingPlan();
  const { startGenerating, cancelGenerating } = useStreamingDayPlans();
  const navigate = useNavigate();
  const location = useLocation();

  // Restore session from sessionStorage on page refresh (only on root /)
  useEffect(() => {
    if (location.pathname !== '/') return;
    const wasPlanning = sessionStorage.getItem('tc_planning');
    if (wasPlanning) {
      sessionStorage.removeItem('tc_planning');
      setError('Your planning session was interrupted. Please try again.');
      return;
    }
    const savedTripId = sessionStorage.getItem('tc_tripId');
    const savedPhase = sessionStorage.getItem('tc_phase');
    if (savedTripId && savedPhase && savedPhase !== 'input' && savedPhase !== 'planning') {
      navigate(`/trips/${savedTripId}`, { replace: true });
    } else if (savedPhase === 'planning') {
      // Inconsistent state — clear everything
      sessionStorage.removeItem('tc_phase');
      sessionStorage.removeItem('tc_tripId');
      sessionStorage.removeItem('tc_planning');
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    fetchUser();
    const interval = setInterval(fetchUser, AUTH_REFRESH_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [fetchUser]);

  // Close sign-in modal when user signs in
  useEffect(() => {
    if (user && showSignIn) closeSignIn();
  }, [user, showSignIn, closeSignIn]);

  // Navigate to trip URL when planning completes
  useEffect(() => {
    if (phase === 'preview' && tripId && location.pathname === '/') {
      navigate(`/trips/${tripId}`, { replace: true });
    }
  }, [phase, tripId, location.pathname, navigate]);

  // Navigate home when phase resets to input
  useEffect(() => {
    if (phase === 'input' && location.pathname.startsWith('/trips/')) {
      navigate('/', { replace: true });
    }
  }, [phase, location.pathname, navigate]);

  const handleGenerateDayPlans = useCallback(() => {
    startGenerating();
  }, [startGenerating]);

  const handleOpenChat = useCallback(() => {
    useUIStore.getState().openChat('journey');
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

  const handleCancelPlanning = useCallback(() => {
    cancelPlanning();
  }, [cancelPlanning]);

  const errorBanner = error ? (
    <div className="max-w-lg mx-auto mb-4 animate-fade-in-up">
      <div role="alert" className="bg-red-50 dark:bg-red-950/50 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 px-4 py-3 rounded-lg flex items-start gap-3">
        <AlertCircle className="h-5 w-5 shrink-0 mt-0.5" />
        <div className="flex-1">
          <p className="text-sm">{error}</p>
          {(error.includes('Connection lost') || error.includes('try again') || error.includes('interrupted')) && (
            <button
              onClick={() => { setError(null); window.location.reload(); }}
              className="text-xs mt-1 underline text-red-600 dark:text-red-300 hover:text-red-800 dark:hover:text-red-100"
            >
              Retry
            </button>
          )}
        </div>
        <button
          onClick={() => setError(null)}
          className="text-red-400 hover:text-red-600 dark:hover:text-red-200 font-bold text-lg leading-none shrink-0"
          aria-label="Dismiss error"
        >
          &times;
        </button>
      </div>
    </div>
  ) : null;

  return (
    <>
      <Header />
      <PageContainer>
        {errorBanner}

        <Routes>
          <Route path="/" element={
            phase === 'planning' ? (
              <div key="planning" className="animate-fade-in-up">
                <PlanningDashboard onCancel={handleCancelPlanning} />
              </div>
            ) : (
              <div key="input" className="animate-fade-in-up">
                <WizardForm onSubmit={startPlanning} isLoading={isLoading} />
              </div>
            )
          } />
          <Route path="/trips/:id" element={
            <ErrorBoundary fallback={
              <div className="text-center py-16 space-y-4">
                <p className="text-lg font-display font-semibold text-text-primary">Something went wrong</p>
                <p className="text-sm text-text-muted">An error occurred while displaying this trip.</p>
                <a href="/" className="text-sm text-primary-600 dark:text-primary-400 hover:underline">Go back to home</a>
              </div>
            }>
              <>
                <TripLoader />
                {(phase === 'preview' || phase === 'day-plans') && journey && (
                  <div key="preview" className="animate-fade-in-up">
                    <JourneyDashboard
                      onGenerateDayPlans={handleGenerateDayPlans}
                      onCancelDayPlans={cancelGenerating}
                      onOpenChat={handleOpenChat}
                    />
                  </div>
                )}
              </>
            </ErrorBoundary>
          } />
        </Routes>
      </PageContainer>

      <ChatPanel />
    </>
  );
}

function App() {
  const showSignIn = useUIStore((s) => s.showSignIn);
  const closeSignIn = useUIStore((s) => s.closeSignIn);

  return (
    <div className="min-h-screen bg-surface-dim">
      <a href="#main-content" className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:bg-primary-600 focus:text-white focus:px-4 focus:py-2 focus:rounded-md focus:top-2 focus:left-2">
        Skip to content
      </a>
      <Routes>
        <Route path="/shared/:token" element={<SharedTrip />} />
        <Route path="/signin" element={<SignIn />} />
        <Route path="/*" element={<MainApp />} />
      </Routes>

      {showSignIn && <SignInModal onClose={closeSignIn} />}
      <ToastContainer />
    </div>
  );
}

export default App;
