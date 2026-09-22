import { Button, Layout, Space, Typography } from 'antd';
import { Link } from 'react-router-dom';

import { openCookieSettings } from '../lib/cookieConsent';

export default function AppFooter() {
  return (
    <Layout.Footer
      style={{
        borderTop: '1px solid #EEEEF2',
        background: 'transparent',
        padding: '16px 24px',
        minHeight: 'max-content',
        paddingBottom: 'calc(16px + env(safe-area-inset-bottom))',
      }}
    >
      <Space wrap size={12} style={{ justifyContent: 'center', width: '100%' }}>
        <Typography.Text type="secondary">
          ИТ Школа Ростелекома · RTK CRM
        </Typography.Text>
        <Link to="/cookie-policy">Политика обработки cookie</Link>
        <Link to="/privacy">Политика обработки персональных данных</Link>
        <Button type="link" size="small" onClick={openCookieSettings} style={{ padding: 0 }}>
          Настроить cookie
        </Button>
      </Space>
    </Layout.Footer>
  );
}
