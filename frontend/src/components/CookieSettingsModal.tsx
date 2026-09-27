import { Modal, Space, Switch, Typography } from 'antd';
import { useEffect, useState } from 'react';

import {
  COOKIE_CATEGORIES,
  buildConsent,
  readConsent,
  saveConsent,
  type CookieCategory,
} from '../lib/cookieConsent';

interface CookieSettingsModalProps {
  open: boolean;
  onClose: () => void;
}

type Choice = Record<Exclude<CookieCategory, 'necessary'>, boolean>;

const DEFAULT_CHOICE: Choice = {
  analytics: false,
  functional: false,
  marketing: false,
};

export default function CookieSettingsModal({ open, onClose }: CookieSettingsModalProps) {
  const [choice, setChoice] = useState<Choice>(DEFAULT_CHOICE);

  useEffect(() => {
    if (!open) {
      return;
    }
    const saved = readConsent();
    setChoice(
      saved
        ? {
            analytics: saved.analytics,
            functional: saved.functional,
            marketing: saved.marketing,
          }
        : DEFAULT_CHOICE
    );
  }, [open]);

  const handleSave = () => {
    saveConsent(buildConsent(choice));
    onClose();
  };

  return (
    <Modal
      title="Настройки файлов cookie"
      open={open}
      onCancel={onClose}
      onOk={handleSave}
      okText="Сохранить выбор"
      cancelText="Отмена"
      width={560}
      rootClassName="cookie-settings-modal"
      style={{ maxWidth: 'calc(100vw - 24px)' }}
    >
      <Space direction="vertical" size={16} style={{ width: '100%' }}>
        <Typography.Text type="secondary">
          Отключение категорий не влияет на работу необходимых cookie — они
          обеспечивают вход в систему и безопасность сессии.
        </Typography.Text>
        {COOKIE_CATEGORIES.map((category) => (
          <div
            key={category.key}
            className="cookie-settings-row"
            style={{
              display: 'flex',
              gap: 16,
              alignItems: 'flex-start',
              justifyContent: 'space-between',
            }}
          >
            <div style={{ flex: 1, minWidth: 0 }}>
              <Typography.Text strong>{category.title}</Typography.Text>
              <div>
                <Typography.Text type="secondary" style={{ fontSize: 13 }}>
                  {category.description}
                </Typography.Text>
              </div>
            </div>
            <Switch
              checked={
                category.required
                  ? true
                  : choice[category.key as Exclude<CookieCategory, 'necessary'>]
              }
              disabled={category.required}
              onChange={(next) =>
                setChoice((prev) => ({ ...prev, [category.key]: next }))
              }
              aria-label={`Cookie: ${category.title}`}
            />
          </div>
        ))}
      </Space>
    </Modal>
  );
}
