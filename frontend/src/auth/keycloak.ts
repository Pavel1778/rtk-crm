import Keycloak from 'keycloak-js';

/**
 * Режим аутентификации фронтенда.
 *
 * `keycloak` — вход через Keycloak (Authorization Code Flow + PKCE), токен
 * приходит от Keycloak и проверяется backend'ом по JWKS. `jwt` — локальный
 * вход по email/паролю, нужен для разработки без поднятого Keycloak.
 *
 * Режим задаётся при сборке (`VITE_AUTH_MODE`) и должен совпадать с
 * `AUTH_MODE` на backend: если backend ждёт RS256-токен Keycloak, а фронтенд
 * пришлёт локальный HS256, все запросы вернут 401.
 */
export const AUTH_MODE = (import.meta.env.VITE_AUTH_MODE ?? 'jwt').toLowerCase();
export const isKeycloakMode = AUTH_MODE === 'keycloak';

const KEYCLOAK_URL = import.meta.env.VITE_KEYCLOAK_URL ?? 'http://localhost:8080';
const KEYCLOAK_REALM = import.meta.env.VITE_KEYCLOAK_REALM ?? 'rtk-crm';
const KEYCLOAK_CLIENT_ID =
  import.meta.env.VITE_KEYCLOAK_CLIENT_ID ?? 'rtk-crm-frontend';

export const keycloak = new Keycloak({
  url: KEYCLOAK_URL,
  realm: KEYCLOAK_REALM,
  clientId: KEYCLOAK_CLIENT_ID,
});

/**
 * `init` вызывается один раз на всё приложение: повторный вызов в
 * React.StrictMode (двойной эффект в dev) ломает внутреннее состояние
 * keycloak-js и приводит к повторному редиректу.
 */
let initPromise: Promise<boolean> | null = null;

/**
 * Проверяет, отвечает ли Keycloak, до вызова `keycloak.init`.
 *
 * `keycloak-js` в режиме `check-sso` уводит верхнее окно на Keycloak, если
 * сервер не ответил (тихая проверка не удалась → полноценный редирект).
 * При недоступном Keycloak это оставляет пользователя на странице ошибки
 * браузера вместо формы входа, поэтому сначала убеждаемся, что сервер жив.
 */
async function isKeycloakReachable(timeoutMs: number): Promise<boolean> {
  const url = `${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/.well-known/openid-configuration`;
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, { signal: controller.signal });
    return response.ok;
  } catch {
    return false;
  } finally {
    window.clearTimeout(timer);
  }
}

/**
 * Инициализирует Keycloak, не уводя браузер на форму входа принудительно.
 *
 * Возвращает `true`, если сессия SSO уже есть. При `check-sso` вход
 * выполняется только по явному действию пользователя (кнопка на странице
 * входа): так остаётся доступна и форма email/пароль, а жюри может показать
 * вход через Keycloak из интерфейса, а не через автоматический редирект.
 *
 * Если Keycloak не отвечает, инициализация пропускается: показывается форма
 * входа, и браузер не уходит на недоступный сервер.
 */
export function initKeycloak(reachTimeoutMs = 4000): Promise<boolean> {
  if (!isKeycloakMode) {
    return Promise.resolve(false);
  }
  if (!initPromise) {
    initPromise = isKeycloakReachable(reachTimeoutMs).then((reachable) => {
      if (!reachable) {
        console.warn('Keycloak недоступен, показана форма входа');
        return false;
      }
      return keycloak
        .init({
          onLoad: 'check-sso',
          pkceMethod: 'S256',
          // Сторонние cookie в iframe блокируются браузерами по умолчанию,
          // а проверка через iframe не нужна: срок жизни токена отслеживает
          // updateToken перед каждым запросом.
          checkLoginIframe: false,
        })
        .catch((error: unknown) => {
          console.error('Не удалось инициализировать Keycloak', error);
          return false;
        });
    });
  }
  return initPromise;
}

/** Текущий access token Keycloak или `null`, если сессии нет. */
export function keycloakToken(): string | null {
  return keycloak.token ?? null;
}

/**
 * Обновляет токен, если до истечения осталось меньше `minValidity` секунд.
 *
 * Вызывается перед каждым запросом: access token живёт минуты, и без
 * обновления запросы начинают возвращать 401 после его истечения.
 * Возвращает актуальный токен либо `null`, если сессия завершена.
 */
export async function ensureFreshKeycloakToken(
  minValidity = 30
): Promise<string | null> {
  if (!isKeycloakMode || !keycloak.authenticated) {
    return keycloakToken();
  }
  try {
    await keycloak.updateToken(minValidity);
    return keycloakToken();
  } catch {
    // Refresh token истёк или отозван — сессия завершена.
    return null;
  }
}

/**
 * Завершает сессию в Keycloak и возвращает браузер на страницу входа.
 *
 * Локальный токен не трогаем: он используется только в режиме `jwt`.
 */
export async function logoutKeycloak(redirectPath = '/'): Promise<void> {
  if (!isKeycloakMode) {
    return;
  }
  await keycloak.logout({ redirectUri: window.location.origin + redirectPath });
}
