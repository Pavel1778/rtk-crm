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
  // antd по умолчанию берёт description/placeholder из чёрного с альфой:
  // rgba(0,0,0,.45) даёт 3.35:1, rgba(0,0,0,.25) — 1.83:1. Оба ниже AA,
  // поэтому задаём плотный серый, читаемый и на белом, и на #F5F5F7.
  colorTextDescription: '#6B6B72',
  colorTextPlaceholder: '#6B6B72',
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
 * - фон не чистый чёрный: #131417 снижает контраст с текстом и усталость глаз;
 * - глубина передаётся светлотой поверхности (#131417 → #1B1C20 → #292A30),
 *   а не тенями, которые на тёмном фоне не читаются;
 * - акценты десатурированы, иначе неонят и «размываются» на тёмном фоне;
 * - текст и акценты проверены на контраст WCAG AA (≥ 4.5:1) от каждой
 *   поверхности, включая всплывающие слои (#292A30).
 *
 * Значения совпадают с CSS-переменными `:root[data-theme='dark']`,
 * чтобы antd-компоненты и собственные стили не расходились по палитре.
 */
export const darkPalette = {
  bgPage: '#131417',
  bgContainer: '#1B1C20',
  bgElevated: '#292A30',
  bgSoft: '#212227',
  text: '#E8E8ED',
  textSecondary: '#ABABB6',
  // Третичный/placeholder текст: производные токены antd по умолчанию остаются
  // светлыми (rgba(0,0,0,.45)) и на тёмном фоне не читаются.
  textTertiary: '#9494A0',
  border: '#36373E',
  borderSoft: '#2A2B31',
  // Рамка полей и кнопок: 3.3:1 к карточке — минимум WCAG 1.4.11.
  // Декоративные разделители остаются на borderSoft, он специально тише.
  borderControl: '#6B6D77',
  accent: '#A78BFA',
  accentHover: '#B9A5F5',
  accentSoft: '#2E2743',
  success: '#4FB477',
  warning: '#D9A441',
  error: '#E8808A',
  info: '#7FA6E8',
  // Текст на цветных заливках (основные кнопки, счётчики бейджей). Белый на
  // осветлённых акцентах даёт ~2.7:1, поэтому заливки подписываем тёмным.
  onSolid: '#131417',
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
    colorTextDescription: darkPalette.textTertiary,
    colorBorder: darkPalette.borderControl,
    colorBorderSecondary: darkPalette.borderSoft,
    colorBgLayout: darkPalette.bgPage,
    colorBgContainer: darkPalette.bgContainer,
    colorBgElevated: darkPalette.bgElevated,
    colorLink: darkPalette.accent,
    // colorTextLightSolid глобально не трогаем: светлый текст на тёмных
    // подложках ждут тултипы, badge, steps, switch и avatar — тёмный цвет
    // ломает их (подсказка становилась тёмной на тёмном, 1.83:1). Заливки
    // кнопок подписываем тёмным узко, через componentToken ниже.
  },
  components: {
    ...antTheme.components,
    // Основная кнопка заливается светлым акцентом: белый текст на #A78BFA
    // даёт 2.7:1, поэтому подпись тёмная. Задаём цвет именно кнопке, чтобы
    // не задеть тултипы и прочие компоненты, ждущие светлый colorTextLightSolid.
    Button: {
      ...antTheme.components?.Button,
      primaryColor: darkPalette.onSolid,
      fontWeight: 500,
      primaryShadow: 'none',
    },
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
