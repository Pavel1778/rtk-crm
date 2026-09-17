import type { ThemeConfig } from 'antd';

export const rostelecomTheme: ThemeConfig = {
  token: {
    // Основной акцент — Rostelecom Purple
    colorPrimary: '#7B1FA2',
    colorInfo: '#7B1FA2',
    colorLink: '#7B1FA2',
    
    // Радиусы скруглений — умеренные, как в Атомаро
    borderRadius: 8,
    borderRadiusLG: 12,
    borderRadiusSM: 6,
    
    // Типографика — системный стек
    fontFamily: 'system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", sans-serif',
    fontSize: 14,
    fontSizeHeading1: 32,
    fontSizeHeading2: 24,
    fontSizeHeading3: 20,
    
    // Фоны (светлый режим)
    colorBgContainer: '#FFFFFF',
    colorBgLayout: '#F5F5F7',
    colorBgElevated: '#FFFFFF',
    
    // Границы
    colorBorder: '#E0E0E5',
    colorBorderSecondary: '#EEEEF2',
    
    // Тени — мягкие
    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.06)',
    boxShadowSecondary: '0 4px 16px rgba(0, 0, 0, 0.08)',
  },
  components: {
    Button: {
      controlHeight: 40,
      controlHeightLG: 48,
      controlHeightSM: 32,
      paddingInline: 20,
      fontWeight: 500,
      primaryShadow: 'none',
    },
    Card: {
      borderRadiusLG: 12,
      paddingLG: 24,
      boxShadowTertiary: '0 2px 8px rgba(0, 0, 0, 0.06)',
    },
    Table: {
      headerBg: '#F5F5F7',
      headerColor: '#1A1A1A',
      rowHoverBg: '#F9F5FC',
      borderColor: '#EEEEF2',
      cellPaddingBlock: 14,
    },
    Menu: {
      itemSelectedBg: '#F3E5F5',
      itemSelectedColor: '#7B1FA2',
      itemBorderRadius: 8,
      itemHeight: 44,
      itemMarginInline: 8,
    },
    Modal: {
      borderRadiusLG: 16,
      paddingContentHorizontalLG: 32,
    },
    Tag: {
      borderRadiusSM: 6,
      defaultBg: '#F5F5F7',
    },
    Input: {
      controlHeight: 40,
      borderRadius: 8,
    },
    Select: {
      controlHeight: 40,
      borderRadius: 8,
    },
    Tabs: {
      itemSelectedColor: '#7B1FA2',
      inkBarColor: '#7B1FA2',
    },
  },
};
