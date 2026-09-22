export const COOKIE_CONSENT_KEY = 'rtk_cookie_consent';
export const COOKIE_CONSENT_VERSION = '1.0';

export interface CookieConsent {
  necessary: true;
  analytics: boolean;
  functional: boolean;
  marketing: boolean;
  timestamp: number;
  version: string;
}

export type CookieCategory = 'necessary' | 'analytics' | 'functional' | 'marketing';

export interface CookieCategoryInfo {
  key: CookieCategory;
  title: string;
  description: string;
  required: boolean;
}

export const COOKIE_CATEGORIES: CookieCategoryInfo[] = [
  {
    key: 'necessary',
    title: 'Необходимые',
    description:
      'JWT-токен авторизации, защита от CSRF, сохранение сессии. Без них вход в систему невозможен.',
    required: true,
  },
  {
    key: 'analytics',
    title: 'Аналитические',
    description:
      'Обезличенная статистика использования разделов CRM: какие страницы открывают, где возникают ошибки.',
    required: false,
  },
  {
    key: 'functional',
    title: 'Функциональные',
    description:
      'Пользовательские настройки интерфейса: выбранная тема, язык, фильтры доски и ширина колонок.',
    required: false,
  },
  {
    key: 'marketing',
    title: 'Маркетинговые',
    description:
      'Ретаргетинг и рекламные пиксели. В текущей версии CRM не используются.',
    required: false,
  },
];

export const CONSENT_UPDATED_EVENT = 'rtk-cookie-consent-updated';

export function buildConsent(
  choice: Omit<CookieConsent, 'necessary' | 'timestamp' | 'version'>
): CookieConsent {
  return {
    necessary: true,
    analytics: choice.analytics,
    functional: choice.functional,
    marketing: choice.marketing,
    timestamp: Date.now(),
    version: COOKIE_CONSENT_VERSION,
  };
}

export function readConsent(): CookieConsent | null {
  try {
    const raw = localStorage.getItem(COOKIE_CONSENT_KEY);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw) as Partial<CookieConsent>;
    if (parsed.version !== COOKIE_CONSENT_VERSION) {
      return null;
    }
    return {
      necessary: true,
      analytics: Boolean(parsed.analytics),
      functional: Boolean(parsed.functional),
      marketing: Boolean(parsed.marketing),
      timestamp: Number(parsed.timestamp) || Date.now(),
      version: COOKIE_CONSENT_VERSION,
    };
  } catch {
    return null;
  }
}

export function saveConsent(consent: CookieConsent): void {
  localStorage.setItem(COOKIE_CONSENT_KEY, JSON.stringify(consent));
  window.dispatchEvent(new CustomEvent(CONSENT_UPDATED_EVENT, { detail: consent }));
}

export function openCookieSettings(): void {
  window.dispatchEvent(new CustomEvent('rtk-cookie-settings-open'));
}
