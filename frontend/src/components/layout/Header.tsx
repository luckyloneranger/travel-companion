import { Compass } from 'lucide-react';

export function Header() {
  return (
    <header className="border-b border-border-default bg-surface px-6 py-4">
      <div className="max-w-6xl mx-auto flex items-center gap-3">
        <Compass className="h-6 w-6 text-primary-600" />
        <h1 className="text-xl font-display font-bold text-text-primary">
          Travel Companion
        </h1>
      </div>
    </header>
  );
}
