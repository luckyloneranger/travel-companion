import type { ReactNode } from 'react';

export function PageContainer({ children }: { children: ReactNode }) {
  return (
    <main id="main-content" className="max-w-6xl mx-auto px-4 sm:px-6 py-4 sm:py-8">
      {children}
    </main>
  );
}
