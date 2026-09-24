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

/**
 * Тёмная вариация «Атомаро». Значения совпадают с CSS-переменными
 * `.Theme_root_rtk_purple_dark`, чтобы antd-компоненты и собственные
 * стили не расходились по палитре.
 */
export const antDarkTheme: ThemeConfig = {
  ...antTheme,
  token: {
    ...atmrTokens,
    colorPrimary: '#A88BFA',
    colorInfo: '#A88BFA',
    colorText: '#FFFFFF',
    colorTextSecondary: '#B8B8C0',
    colorBorder: '#474850',
    colorBorderSecondary: '#3A3B42',
    colorBgLayout: '#1C1D22',
    colorBgContainer: '#2A2B31',
    colorBgElevated: '#2A2B31',
  },
  components: {
    ...antTheme.components,
    Card: {
      boxShadowTertiary: 'none',
      colorBorderSecondary: '#3A3B42',
    },
    Table: {
      headerBg: '#33343B',
    },
    Layout: {
      headerBg: '#2A2B31',
      bodyBg: '#1C1D22',
    },
    Menu: {
      itemSelectedBg: '#3A2E5C',
      itemSelectedColor: '#A88BFA',
    },
  },
};
