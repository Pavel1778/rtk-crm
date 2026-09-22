import { Button, Space, Typography } from 'antd';
import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { buildConsent, readConsent, saveConsent } from '../lib/cookieConsent';
import CookieSettingsModal from './CookieSettingsModal';

export default function CookieConsentBanner() {
  const [visible, setVisible] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);

  useEffect(() => {
    setVisible(readConsent() === null);
  }, []);

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
        >
          <div className="cookie-banner__text">
            <Typography.Text strong>Мы используем файлы cookie</Typography.Text>
            <div>
              <Typography.Text type="secondary" style={{ fontSize: 13 }}>
                Необходимые cookie обеспечивают вход в систему и безопасность
                сессии. Остальные категории включаются только с вашего согласия
                (152-ФЗ «О персональных данных»).{' '}
                <Link to="/cookie-policy">Политика обработки cookie</Link>
              </Typography.Text>
            </div>
          </div>
          <Space wrap className="cookie-banner__actions">
            <Button onClick={rejectAll}>Отклонить все</Button>
            <Button onClick={() => setSettingsOpen(true)}>Настроить</Button>
            <Button type="primary" onClick={acceptAll}>
              Принять все
            </Button>
          </Space>
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
