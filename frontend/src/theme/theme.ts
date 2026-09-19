import type { ThemeConfig } from 'antd';

/**
 * Дизайн-система «Атомаро»: тема Rostelecom Purple.
 * Цвета задаются токенами Ant Design, HEX используется только здесь,
 * в единственном месте конфигурации.
 */

export const atmrTokens = {
  colorPrimary: '#6E41F2',
  colorInfo: '#6E41F2',
  colorSuccess: '#00AC43',
  colorWarning: '#F5A623',
  colorError: '#E5484D',
  colorText: '#1C1D22',
  colorTextSecondary: '#6B6B72',
  colorBorder: '#E0E0E5',
  colorBorderSecondary: '#EEEEF2',
  colorBgLayout: '#F5F5F7',
  borderRadius: 8,
  controlHeight: 36,
  fontFamily:
    "'Inter', -apple-system, 'Segoe UI', Roboto, Arial, sans-serif",
} as const;

export const antTheme: ThemeConfig = {
  token: atmrTokens,
  components: {
    Card: {
      // карточки внутри контейнера — без тени, только рамка
      boxShadowTertiary: 'none',
      colorBorderSecondary: atmrTokens.colorBorderSecondary,
    },
    Button: {
      fontWeight: 500,
      primaryShadow: 'none',
    },
    Table: {
      headerBg: '#F5F5F7',
    },
    Layout: {
      headerBg: '#FFFFFF',
      bodyBg: '#F5F5F7',
    },
    Menu: {
      itemSelectedBg: '#F3E5F5',
      itemSelectedColor: atmrTokens.colorPrimary,
    },
  },
};
