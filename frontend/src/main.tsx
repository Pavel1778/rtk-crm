import React, { useEffect } from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { App as AntApp, ConfigProvider } from 'antd';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ruRU from 'antd/locale/ru_RU';
import 'dayjs/locale/ru';
import './index.css';

import App from './App';
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

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <Root />
    </QueryClientProvider>
  </React.StrictMode>
);
