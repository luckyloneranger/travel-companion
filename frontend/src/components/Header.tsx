import { Compass } from 'lucide-react';

export function Header() {
  return (
    <header className="bg-[#FBF8F4] border-b border-[#E8E0D4] sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-center h-16">
          <div className="flex items-center gap-2.5">
            <div className="p-1.5 rounded-xl bg-[#C97B5A] shadow-md">
              <Compass className="h-5 w-5 text-white" aria-hidden="true" />
            </div>
            <span className="text-xl font-display font-bold text-[#3D3229]">
              Travel Companion
            </span>
          </div>
        </div>
      </div>
    </header>
  );
}
