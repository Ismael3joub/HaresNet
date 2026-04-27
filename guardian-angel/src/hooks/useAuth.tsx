import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { authApi } from '@/lib/api';

interface User {
  id: number;
  username: string;
}

interface LoginResult {
  requires2fa: boolean;
  tempToken?: string;
  maskedEmail?: string;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<LoginResult>;
  verify2fa: (code: string, tempToken: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      setIsLoading(false);
      return;
    }

    try {
      const data = await authApi.status();
      setUser(data.user);
    } catch {
      localStorage.removeItem('access_token');
    } finally {
      setIsLoading(false);
    }
  };

  const login = async (username: string, password: string): Promise<LoginResult> => {
    const data = await authApi.login(username, password);

    if (data['2fa_required']) {
      return {
        requires2fa: true,
        tempToken: data.temp_token,
        maskedEmail: data.masked_email
      };
    }

    // No 2FA — direct login (Blynk disabled fallback)
    localStorage.setItem('access_token', data.access_token);
    setUser(data.user);
    return { requires2fa: false };
  };

  const verify2fa = async (code: string, tempToken: string) => {
    const data = await authApi.verify2fa(code, tempToken);
    localStorage.setItem('access_token', data.access_token);
    setUser(data.user);
  };

  const logout = async () => {
    try {
      await authApi.logout();
    } finally {
      localStorage.removeItem('access_token');
      setUser(null);
    }
  };

  return (
    <AuthContext.Provider value={{
      user,
      isAuthenticated: !!user,
      isLoading,
      login,
      verify2fa,
      logout,
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

