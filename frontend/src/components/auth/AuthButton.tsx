import { useAuthStore } from '@/stores/authStore';
import { Button } from '@/components/ui/button';
import { LogIn, LogOut } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

export function AuthButton() {
  const { user, isLoading, logout } = useAuthStore();

  if (isLoading) return null;

  if (!user) {
    return (
      <Button
        variant="outline"
        size="sm"
        onClick={() => {
          window.location.href = `${API_BASE}/api/auth/login/google`;
        }}
      >
        <LogIn className="h-4 w-4" />
        Sign In
      </Button>
    );
  }

  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-text-muted hidden sm:inline">{user.name}</span>
      <Button variant="ghost" size="sm" onClick={logout}>
        <LogOut className="h-4 w-4" />
        <span className="hidden sm:inline">Sign Out</span>
      </Button>
    </div>
  );
}
