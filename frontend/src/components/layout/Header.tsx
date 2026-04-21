import { useCallback, useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Compass, Moon, Sun } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { AuthButton } from '@/components/auth/AuthButton';
import { useAuthStore } from '@/stores/authStore';

export function Header() {
  const [dark, setDark] = useState(() => {
    if (typeof window === 'undefined') return false;
    return document.documentElement.classList.contains('dark') ||
      (!localStorage.getItem('theme') && window.matchMedia('(prefers-color-scheme: dark)').matches);
  });

  const user = useAuthStore((s) => s.user);
  const location = useLocation();

  useEffect(() => {
    if (dark) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('theme', 'light');
    }
  }, [dark]);

  const toggleDark = useCallback(() => setDark((d) => !d), []);

  const navLinks = [
    { to: '/cities', label: 'Explore Cities' },
    { to: '/plan', label: 'Plan a Trip' },
    ...(user ? [{ to: '/journeys', label: 'My Trips' }] : []),
  ];

  return (
    <header className="border-b border-border-default bg-surface px-4 sm:px-6 py-3 sm:py-4">
      <div className="max-w-6xl mx-auto flex items-center justify-between">
        <div className="flex items-center gap-4 sm:gap-6 min-w-0">
          <Link
            to="/"
            className="flex items-center gap-2 sm:gap-3 min-w-0 hover:opacity-80 transition-opacity"
          >
            <Compass className="h-5 w-5 sm:h-6 sm:w-6 text-primary-600 shrink-0" />
            <h1 className="text-lg sm:text-xl font-display font-bold text-text-primary truncate">
              <span className="hidden sm:inline">Regular Everyday </span>
              <span className="sm:hidden">RET </span>
              Traveller
            </h1>
          </Link>

          <nav className="hidden sm:flex items-center gap-1">
            {navLinks.map((link) => (
              <Link
                key={link.to}
                to={link.to}
                className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  location.pathname.startsWith(link.to)
                    ? 'text-primary-600 bg-primary-50 dark:bg-primary-900/20 dark:text-primary-400'
                    : 'text-text-muted hover:text-text-primary hover:bg-surface-hover'
                }`}
              >
                {link.label}
              </Link>
            ))}
          </nav>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <AuthButton />
          <Button variant="ghost" size="icon-sm" onClick={toggleDark} aria-label="Toggle dark mode">
            {dark ? <Sun className="h-4 w-4 text-text-muted" /> : <Moon className="h-4 w-4 text-text-muted" />}
          </Button>
        </div>
      </div>

      {/* Mobile nav */}
      <nav className="sm:hidden flex items-center gap-1 mt-2 -mx-1 overflow-x-auto">
        {navLinks.map((link) => (
          <Link
            key={link.to}
            to={link.to}
            className={`px-3 py-1.5 rounded-md text-xs font-medium whitespace-nowrap transition-colors ${
              location.pathname.startsWith(link.to)
                ? 'text-primary-600 bg-primary-50 dark:bg-primary-900/20 dark:text-primary-400'
                : 'text-text-muted hover:text-text-primary'
            }`}
          >
            {link.label}
          </Link>
        ))}
      </nav>
    </header>
  );
}
