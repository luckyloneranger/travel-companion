import type { ReactNode } from 'react';

export function PageContainer({ children }: { children: ReactNode }) {
  return (
    <main className="max-w-6xl mx-auto px-6 py-8">
      {children}
    </main>
  );
}
