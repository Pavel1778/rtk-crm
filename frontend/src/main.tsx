import React, { useEffect } from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { App as AntApp, ConfigProvider } from 'antd';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ruRU from 'antd/locale/ru_RU';
import 'dayjs/locale/ru';
import './index.css';

import App from './App';
import { initKeycloak, isKeycloakMode } from './auth/keycloak';
import { antDarkTheme, antTheme } from './theme/theme';
import { useThemeStore } from './stores/themeStore';

/** Применяет тему к документу. Вызывается до первого рендера, чтобы не
 *  было вспышки светлой темы (FOUC) при загрузке. */
function applyTheme(mode: 'light' | 'dark') {
  document.documentElement.dataset.theme = mode;
  document.documentElement.style.colorScheme = mode;
}

applyTheme(useThemeStore.getState().mode);

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,
      gcTime: 10 * 60 * 1000,
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

function Root() {
  const mode = useThemeStore((s) => s.mode);
  const syncSystem = useThemeStore((s) => s.syncSystem);

  useEffect(() => {
    applyTheme(mode);
  }, [mode]);

  // Реагируем на смену темы ОС, пока пользователь не выбрал тему вручную.
  useEffect(() => {
    const media = window.matchMedia('(prefers-color-scheme: dark)');
    const handler = (event: MediaQueryListEvent) =>
      syncSystem(event.matches ? 'dark' : 'light');
    media.addEventListener('change', handler);
    return () => media.removeEventListener('change', handler);
  }, [syncSystem]);

  return (
    <ConfigProvider locale={ruRU} theme={mode === 'dark' ? antDarkTheme : antTheme}>
      <AntApp>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </AntApp>
    </ConfigProvider>
  );
}

const root = ReactDOM.createRoot(document.getElementById('root') as HTMLElement);

/** Рендерит приложение. Вызывается после инициализации Keycloak. */
function renderApp() {
  root.render(
    <React.StrictMode>
      <QueryClientProvider client={queryClient}>
        <Root />
      </QueryClientProvider>
    </React.StrictMode>
  );
}

if (isKeycloakMode) {
  // Инициализацию ждём до первого рендера: иначе App смонтируется без
  // токена, запрос /api/auth/me уйдёт без Authorization и вернёт 401 —
  // пользователь на мгновение увидит форму входа, хотя сессия есть.
  // При `login-required` браузер до разрешения промиса уходит на Keycloak.
  void initKeycloak().then(renderApp);
} else {
  renderApp();
}
