import { useAuthStore } from '@/stores/authStore';
import { Button } from '@/components/ui/button';
import { LogIn, LogOut } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export function AuthButton() {
  const { user, isLoading, logout } = useAuthStore();
  const navigate = useNavigate();

  if (isLoading) return null;

  if (!user) {
    return (
      <Button
        variant="outline"
        size="sm"
        onClick={() => navigate('/signin')}
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
