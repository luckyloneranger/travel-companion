import { useEffect, useState, type ReactNode } from 'react';

interface PhaseTransitionProps {
  children: ReactNode;
  phase: string;
  animation?: 'fade' | 'slide-right' | 'scale';
}

export function PhaseTransition({ children, phase, animation = 'fade' }: PhaseTransitionProps) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    setVisible(false);
    const timer = requestAnimationFrame(() => setVisible(true));
    return () => cancelAnimationFrame(timer);
  }, [phase]);

  const animationClass = visible
    ? animation === 'slide-right'
      ? 'animate-slide-in-right'
      : animation === 'scale'
      ? 'animate-scale-in'
      : 'animate-fade-in'
    : 'opacity-0';

  return (
    <div key={phase} className={animationClass}>
      {children}
    </div>
  );
}
