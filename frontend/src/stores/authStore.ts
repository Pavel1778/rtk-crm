import { create } from 'zustand';

import { login as apiLogin, me as apiMe } from '../api/endpoints';
import { setToken } from '../api/client';
import type { User, UserRole } from '../types';

interface AuthState {
  user: User | null;
  loading: boolean;
  initialized: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  restore: () => Promise<void>;
  signOut: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  loading: false,
  initialized: false,

  signIn: async (email, password) => {
    set({ loading: true });
    try {
      const token = await apiLogin(email, password);
      setToken(token.access_token);
      set({ user: token.user, loading: false });
    } catch (error) {
      set({ loading: false });
      throw error;
    }
  },

  restore: async () => {
    try {
      const user = await apiMe();
      set({ user, initialized: true });
    } catch {
      setToken(null);
      set({ user: null, initialized: true });
    }
  },

  signOut: () => {
    setToken(null);
    set({ user: null });
  },
}));

// Хук для получения роли пользователя
export const useRole = (): UserRole => {
  const user = useAuthStore((state) => state.user);
  return user?.role || 'user';
};
