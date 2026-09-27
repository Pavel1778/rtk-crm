import { create } from 'zustand';

import { login as apiLogin, me as apiMe } from '../api/endpoints';
import { setToken } from '../api/client';
import { isKeycloakMode, logoutKeycloak } from '../auth/keycloak';
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
    // В режиме Keycloak токен уже получен через keycloak-js и подставляется
    // перехватчиком axios. Здесь остаётся только узнать локальную учётную
    // запись — backend находит её по email из токена и создаёт при первом
    // входе, поэтому пользователю не нужен отдельный шаг регистрации.
    try {
      const user = await apiMe();
      set({ user, initialized: true });
    } catch {
      // В Keycloak-режиме localStorage не используется: чистка здесь
      // сбросила бы токен, которым управляет keycloak-js.
      if (!isKeycloakMode) {
        setToken(null);
      }
      set({ user: null, initialized: true });
    }
  },

  signOut: () => {
    setToken(null);
    set({ user: null });
    if (isKeycloakMode) {
      // Завершаем сессию в Keycloak, иначе login-required сразу вернёт
      // пользователя обратно без формы входа.
      void logoutKeycloak();
    }
  },
}));

// Хук для получения роли пользователя
export const useRole = (): UserRole => {
  const user = useAuthStore((state) => state.user);
  return user?.role || 'user';
};
