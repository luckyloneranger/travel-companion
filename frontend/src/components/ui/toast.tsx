import { useState, useEffect } from 'react';
import { X, CheckCircle, AlertCircle } from 'lucide-react';

interface Toast {
  id: number;
  message: string;
  type: 'success' | 'error';
}

let toastId = 0;
const listeners: Set<(toast: Toast) => void> = new Set();

export function showToast(message: string, type: 'success' | 'error' = 'success') {
  const toast: Toast = { id: ++toastId, message, type };
  listeners.forEach(fn => fn(toast));
}

export function ToastContainer() {
  const [toasts, setToasts] = useState<Toast[]>([]);

  useEffect(() => {
    const handler = (toast: Toast) => {
      setToasts(prev => [...prev, toast]);
      setTimeout(() => {
        setToasts(prev => prev.filter(t => t.id !== toast.id));
      }, 4000);
    };
    listeners.add(handler);
    return () => { listeners.delete(handler); };
  }, []);

  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 z-[60] space-y-2" aria-live="polite">
      {toasts.map(toast => (
        <div
          key={toast.id}
          className={`flex items-center gap-2 rounded-lg px-4 py-3 text-sm shadow-lg animate-fade-in-up ${
            toast.type === 'success'
              ? 'bg-green-700 dark:bg-green-600 text-white'
              : 'bg-red-700 dark:bg-red-600 text-white'
          }`}
        >
          {toast.type === 'success'
            ? <CheckCircle className="h-4 w-4 shrink-0" />
            : <AlertCircle className="h-4 w-4 shrink-0" />
          }
          <span>{toast.message}</span>
          <button
            type="button"
            onClick={() => setToasts(prev => prev.filter(t => t.id !== toast.id))}
            className="text-white/70 hover:text-white ml-2 shrink-0"
            aria-label="Dismiss"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      ))}
    </div>
  );
}
