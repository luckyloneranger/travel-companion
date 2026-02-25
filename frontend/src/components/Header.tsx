import { Compass } from 'lucide-react';
import { brand, headerGradients } from '@/styles';

export function Header() {
  return (
    <header className="bg-white/80 backdrop-blur-sm border-b border-gray-100">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-center h-16">
          <div className="flex items-center gap-2">
            <Compass className="h-7 w-7" style={{ color: brand.primary }} />
            <span 
              className="text-xl font-bold bg-clip-text text-transparent"
              style={{ backgroundImage: `linear-gradient(to right, ${headerGradients.journey.from}, ${headerGradients.journey.to})` }}
            >
              Travel Companion
            </span>
          </div>
        </div>
      </div>
    </header>
  );
}
