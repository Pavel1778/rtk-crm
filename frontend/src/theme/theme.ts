import type { ThemeConfig } from 'antd';
import { theme } from 'antd';

/**
 * Дизайн-система «Атомаро»: тема Rostelecom Purple.
 * Цвета задаются токенами Ant Design, HEX используется только здесь,
 * в единственном месте конфигурации.
 */

/** Цвет нового этапа workflow по умолчанию — значение данных, не темы:
 *  сохраняется в БД вместе с этапом, поэтому не зависит от светлой/тёмной. */
export const DEFAULT_STAGE_COLOR = '#6E41F2';

export const atmrTokens = {
  colorPrimary: '#6E41F2',
  colorInfo: '#6E41F2',
  colorSuccess: '#00AC43',
  colorWarning: '#F5A623',
  colorError: '#CC2936',
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
 * Тёмная вариация «Атомаро».
 *
 * Правила тёмной темы:
 * - фон не чистый чёрный: #17181C снижает контраст с текстом и усталость глаз;
 * - глубина передаётся светлотой поверхности (#17181C → #1F2025 → #2A2B32),
 *   а не тенями, которые на тёмном фоне не читаются;
 * - акценты десатурированы, иначе неонят и «размываются» на тёмном фоне;
 * - текст и акценты проверены на контраст WCAG AA (≥ 4.5:1) от каждой
 *   поверхности, включая всплывающие слои (#2A2B32).
 *
 * Значения совпадают с CSS-переменными `:root[data-theme='dark']`,
 * чтобы antd-компоненты и собственные стили не расходились по палитре.
 */
export const darkPalette = {
  bgPage: '#17181C',
  bgContainer: '#1F2025',
  bgElevated: '#2A2B32',
  bgSoft: '#26272E',
  text: '#E6E6EB',
  textSecondary: '#A9A9B4',
  // Третичный/placeholder текст: производные токены antd по умолчанию остаются
  // светлыми (rgba(0,0,0,.45)) и на тёмном фоне не читаются.
  textTertiary: '#9A9AA6',
  border: '#33343B',
  borderSoft: '#2C2D34',
  accent: '#A78BFA',
  accentHover: '#B9A5F5',
  accentSoft: '#2E2743',
  success: '#4FB477',
  warning: '#D9A441',
  error: '#E8808A',
  info: '#7FA6E8',
  // Текст на цветных заливках (основные кнопки, счётчики бейджей). Белый на
  // осветлённых акцентах даёт ~2.7:1, поэтому заливки подписываем тёмным.
  onSolid: '#17181C',
} as const;

export const antDarkTheme: ThemeConfig = {
  ...antTheme,
  algorithm: theme.darkAlgorithm,
  token: {
    ...atmrTokens,
    colorPrimary: darkPalette.accent,
    colorInfo: darkPalette.accent,
    colorSuccess: darkPalette.success,
    colorWarning: darkPalette.warning,
    colorError: darkPalette.error,
    colorText: darkPalette.text,
    colorTextSecondary: darkPalette.textSecondary,
    colorTextTertiary: darkPalette.textTertiary,
    colorTextQuaternary: darkPalette.textTertiary,
    colorTextPlaceholder: darkPalette.textTertiary,
    colorTextLightSolid: darkPalette.onSolid,
    colorBorder: darkPalette.border,
    colorBorderSecondary: darkPalette.borderSoft,
    colorBgLayout: darkPalette.bgPage,
    colorBgContainer: darkPalette.bgContainer,
    colorBgElevated: darkPalette.bgElevated,
    colorLink: darkPalette.accent,
  },
  components: {
    ...antTheme.components,
    Card: {
      boxShadowTertiary: 'none',
      colorBorderSecondary: darkPalette.borderSoft,
    },
    Table: {
      headerBg: darkPalette.bgSoft,
    },
    Layout: {
      headerBg: darkPalette.bgContainer,
      bodyBg: darkPalette.bgPage,
    },
    Menu: {
      itemSelectedBg: darkPalette.accentSoft,
      itemSelectedColor: darkPalette.accentHover,
    },
  },
};
