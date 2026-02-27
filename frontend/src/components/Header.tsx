import { Compass } from 'lucide-react';
import { headerGradients } from '@/styles';

export function Header() {
  return (
    <header className="glass-strong border-b border-white/60 sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-center h-16">
          <div className="flex items-center gap-2.5">
            <div className="p-1.5 rounded-xl bg-gradient-to-br from-primary-500 to-purple-600 shadow-md">
              <Compass className="h-5 w-5 text-white" aria-hidden="true" />
            </div>
            <span
              className="text-xl font-display font-bold bg-clip-text text-transparent"
              style={{ backgroundImage: `linear-gradient(135deg, ${headerGradients.journey.from}, ${headerGradients.journey.to})` }}
            >
              Travel Companion
            </span>
          </div>
        </div>
      </div>
    </header>
  );
}
