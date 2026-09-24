import { create } from 'zustand';

export type ThemeMode = 'light' | 'dark';
/** Явный выбор пользователя; 'system' — следовать настройке ОС. */
export type ThemePreference = ThemeMode | 'system';

const STORAGE_KEY = 'rtk-theme-mode';

const SYSTEM_QUERY = '(prefers-color-scheme: dark)';

export function systemMode(): ThemeMode {
  if (typeof window === 'undefined' || !window.matchMedia) {
    return 'light';
  }
  return window.matchMedia(SYSTEM_QUERY).matches ? 'dark' : 'light';
}

function readStoredPreference(): ThemePreference {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === 'light' || stored === 'dark' || stored === 'system') {
      return stored;
    }
  } catch {
    // localStorage недоступен (приватный режим) — следуем системной теме.
  }
  return 'system';
}

function resolveMode(preference: ThemePreference): ThemeMode {
  return preference === 'system' ? systemMode() : preference;
}

interface ThemeState {
  preference: ThemePreference;
  /** Фактически применённая тема (учитывает системную настройку). */
  mode: ThemeMode;
  setPreference: (preference: ThemePreference) => void;
  toggle: () => void;
  syncSystem: (mode: ThemeMode) => void;
}

export const useThemeStore = create<ThemeState>((set, get) => ({
  preference: readStoredPreference(),
  mode: resolveMode(readStoredPreference()),

  setPreference: (preference) => {
    try {
      localStorage.setItem(STORAGE_KEY, preference);
    } catch {
      // Игнорируем: тема всё равно применится в текущей сессии.
    }
    set({ preference, mode: resolveMode(preference) });
  },

  toggle: () => get().setPreference(get().mode === 'dark' ? 'light' : 'dark'),

  syncSystem: (mode) => {
    if (get().preference === 'system') {
      set({ mode });
    }
  },
}));
