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
 * Инициализирует Keycloak и при отсутствии сессии уводит на форму входа.
 *
 * Возвращает `true`, если пользователь аутентифицирован. При
 * `onLoad: 'login-required'` неаутентифицированный браузер получает
 * редирект на Keycloak, поэтому в этом случае промис не разрешается до
 * возврата пользователя с токеном.
 *
 * Ошибка инициализации (Keycloak недоступен) не считается ошибкой входа:
 * промис разрешается `false`, и приложение показывает форму входа с
 * сообщением — иначе при недоступном Keycloak экран оставался бы пустым.
 */
export function initKeycloak(): Promise<boolean> {
  if (!isKeycloakMode) {
    return Promise.resolve(false);
  }
  if (!initPromise) {
    initPromise = keycloak
      .init({
        onLoad: 'login-required',
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
