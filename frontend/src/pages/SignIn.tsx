import { useEffect, useRef } from 'react';
import { MapPin, Plane, X } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { useAuthStore } from '@/stores/authStore';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';
const WIZARD_STATE_KEY = 'tc_wizard_state';

function GoogleIcon() {
  return (
    <svg className="h-5 w-5" viewBox="0 0 24 24">
      <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" />
      <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
      <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
      <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
    </svg>
  );
}

function GitHubIcon() {
  return (
    <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
      <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z" />
    </svg>
  );
}

/** Save current wizard form state to sessionStorage before OAuth redirect. */
function saveWizardState() {
  const state = sessionStorage.getItem('tc_phase');
  if (state === 'input' || !state) {
    sessionStorage.setItem(WIZARD_STATE_KEY, 'preserve');
  }
}

function SignInButtons() {
  return (
    <div className="space-y-4">
      <p className="text-center text-sm text-text-secondary mb-2">
        Sign in to save trips, share plans, and export itineraries
      </p>

      <Button
        variant="outline"
        className="w-full h-11 justify-start gap-3 text-sm font-medium"
        onClick={() => { saveWizardState(); window.location.href = `${API_BASE}/api/auth/login/google`; }}
      >
        <GoogleIcon />
        Continue with Google
      </Button>

      <Button
        variant="outline"
        className="w-full h-11 justify-start gap-3 text-sm font-medium"
        onClick={() => { saveWizardState(); window.location.href = `${API_BASE}/api/auth/login/github`; }}
      >
        <GitHubIcon />
        Continue with GitHub
      </Button>
    </div>
  );
}

/** Full-page sign-in (for /signin route). */
export function SignIn() {
  const { user } = useAuthStore();
  const navigate = useNavigate();

  useEffect(() => {
    if (user) navigate('/', { replace: true });
  }, [user, navigate]);

  return (
    <div className="min-h-screen bg-surface-dim flex items-center justify-center px-4">
      <div className="w-full max-w-sm space-y-8">
        <div className="text-center space-y-3">
          <div className="inline-flex items-center justify-center h-14 w-14 rounded-2xl bg-primary-600 text-white mx-auto">
            <Plane className="h-7 w-7" />
          </div>
          <h1 className="text-2xl font-display font-bold text-text-primary">
            Regular Everyday Traveller
          </h1>
          <p className="text-sm text-text-muted">
            AI-powered multi-city travel planning
          </p>
        </div>

        <Card>
          <CardContent className="pt-6">
            <SignInButtons />
            <div className="relative py-3">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-border-default" />
              </div>
              <div className="relative flex justify-center">
                <span className="bg-surface px-3 text-xs text-text-muted">or</span>
              </div>
            </div>
            <Button
              variant="ghost"
              className="w-full text-sm text-text-muted"
              onClick={() => { window.location.href = '/'; }}
            >
              <MapPin className="h-4 w-4" />
              Browse without signing in
            </Button>
          </CardContent>
        </Card>

        <p className="text-center text-xs text-text-muted">
          By signing in, you agree to our terms of service and privacy policy.
        </p>
      </div>
    </div>
  );
}

/** Modal overlay sign-in (opened from anywhere without losing page state). */
export function SignInModal({ onClose }: { onClose: () => void }) {
  const modalRef = useRef<HTMLDivElement>(null);

  // Trap focus and handle ESC
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [onClose]);

  // Focus trap
  useEffect(() => {
    const modal = modalRef.current;
    if (!modal) return;
    const focusableElements = modal.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    const first = focusableElements[0];
    const last = focusableElements[focusableElements.length - 1];
    first?.focus();

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Tab') {
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last?.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first?.focus();
        }
      }
    };
    modal.addEventListener('keydown', handleKeyDown);
    return () => modal.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" role="dialog" aria-modal="true" aria-label="Sign in">
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />
      <div ref={modalRef} className="relative w-full max-w-sm mx-4 animate-fade-in-up">
        <Card>
          <CardContent className="pt-6">
            <button
              onClick={onClose}
              className="absolute top-3 right-3 text-text-muted hover:text-text-primary"
              aria-label="Close"
            >
              <X className="h-5 w-5" />
            </button>
            <div className="text-center mb-4">
              <div className="inline-flex items-center justify-center h-12 w-12 rounded-xl bg-primary-600 text-white mx-auto mb-3">
                <Plane className="h-6 w-6" />
              </div>
              <h2 className="text-lg font-display font-bold text-text-primary">
                Sign in to continue
              </h2>
            </div>
            <SignInButtons />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
