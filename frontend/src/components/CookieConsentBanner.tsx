import { Button, Typography } from 'antd';
import { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';

import { buildConsent, readConsent, saveConsent } from '../lib/cookieConsent';
import CookieSettingsModal from './CookieSettingsModal';

export default function CookieConsentBanner() {
  const [visible, setVisible] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);

  useEffect(() => {
    setVisible(readConsent() === null);
  }, []);

  // Пока баннер виден, резервируем место внизу страницы: иначе fixed-баннер
  // перекрывает нижнюю навигацию и кнопки отправки в формах. Высоту измеряем,
  // а не хардкодим: на мобильных кнопки переносятся в столбик и баннер выше.
  const bannerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    document.body.classList.toggle('has-cookie-banner', visible);
    if (!visible) {
      document.body.style.removeProperty('--cookie-banner-h');
      return () => document.body.classList.remove('has-cookie-banner');
    }
    const el = bannerRef.current;
    if (!el) return;
    const apply = () =>
      document.body.style.setProperty('--cookie-banner-h', `${el.offsetHeight}px`);
    apply();
    const ro = new ResizeObserver(apply);
    ro.observe(el);
    window.addEventListener('orientationchange', apply);
    return () => {
      ro.disconnect();
      window.removeEventListener('orientationchange', apply);
      document.body.classList.remove('has-cookie-banner');
    };
  }, [visible]);

  useEffect(() => {
    const openSettings = () => setSettingsOpen(true);
    const syncVisibility = () => setVisible(readConsent() === null);
    window.addEventListener('rtk-cookie-settings-open', openSettings);
    window.addEventListener('rtk-cookie-consent-updated', syncVisibility);
    return () => {
      window.removeEventListener('rtk-cookie-settings-open', openSettings);
      window.removeEventListener('rtk-cookie-consent-updated', syncVisibility);
    };
  }, []);

  const acceptAll = useCallback(() => {
    saveConsent(buildConsent({ analytics: true, functional: true, marketing: true }));
    setVisible(false);
  }, []);

  const rejectAll = useCallback(() => {
    saveConsent(buildConsent({ analytics: false, functional: false, marketing: false }));
    setVisible(false);
  }, []);

  return (
    <>
      {visible && (
        <div
          role="dialog"
          aria-label="Согласие на использование файлов cookie"
          className="cookie-banner"
          ref={bannerRef}
        >
          <div className="cookie-banner__text">
            <Typography.Text strong>Мы используем файлы cookie</Typography.Text>
            <div>
              <Typography.Text type="secondary">
                Необходимые cookie обеспечивают вход и безопасность сессии,
                остальные включаются только с вашего согласия (152-ФЗ).{' '}
                <Link to="/cookie-policy">Политика обработки cookie</Link>
              </Typography.Text>
            </div>
          </div>
          <div className="cookie-banner__actions">
            <Button onClick={rejectAll}>Отклонить все</Button>
            <Button onClick={() => setSettingsOpen(true)}>Настроить</Button>
            <Button type="primary" onClick={acceptAll}>
              Принять все
            </Button>
          </div>
        </div>
      )}
      <CookieSettingsModal
        open={settingsOpen}
        onClose={() => {
          setSettingsOpen(false);
          setVisible(readConsent() === null);
        }}
      />
    </>
  );
}
