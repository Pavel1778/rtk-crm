import {
  AppstoreOutlined,
  BarChartOutlined,
  BulbOutlined,
  DatabaseOutlined,
  HistoryOutlined,
  LogoutOutlined,
  MenuOutlined,
  QuestionCircleOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import { Button, Drawer, Grid, Layout, Menu, Space, Tooltip, Typography } from 'antd';
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useState } from 'react';

import { useAuthStore, useRole } from '../stores/authStore';
import { useThemeStore } from '../stores/themeStore';
import AppFooter from './AppFooter';

const { Header, Content } = Layout;

const MENU_ITEMS = [
  { key: '/', icon: <AppstoreOutlined />, label: 'Доска' },
  { key: '/reports', icon: <BarChartOutlined />, label: 'Отчёты' },
  { key: '/directories', icon: <DatabaseOutlined />, label: 'Справочники' },
  { key: '/help', icon: <QuestionCircleOutlined />, label: 'Помощь' },
];

const ADMIN_ITEM = {
  key: '/settings',
  icon: <SettingOutlined />,
  label: 'Пользователи',
};

const AUDIT_ITEM = {
  key: '/audit',
  icon: <HistoryOutlined />,
  label: 'Журнал',
};

export default function MainLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const user = useAuthStore((s) => s.user);
  const signOut = useAuthStore((s) => s.signOut);
  const role = useRole();
  const screens = Grid.useBreakpoint();
  const themeMode = useThemeStore((s) => s.mode);
  const themePreference = useThemeStore((s) => s.preference);
  const setThemePreference = useThemeStore((s) => s.setPreference);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Переключение по кругу: светлая → тёмная → системная.
  const themeTitle =
    themePreference === 'system'
      ? 'Как в системе'
      : themeMode === 'dark'
        ? 'Тёмная тема'
        : 'Светлая тема';
  const cycleTheme = () => {
    const next =
      themePreference === 'light'
        ? 'dark'
        : themePreference === 'dark'
          ? 'system'
          : 'light';
    setThemePreference(next);
  };

  const items = role === 'admin'
    ? [...MENU_ITEMS, ADMIN_ITEM, AUDIT_ITEM]
    : MENU_ITEMS;

  return (
    <Layout className="app-shell">
      <Header
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 16,
          padding: screens.md ? '0 24px' : '0 12px',
          borderBottom: '1px solid var(--atmr-border-soft)',
          position: 'sticky',
          top: 0,
          zIndex: 100,
        }}
      >
        {!screens.md && (
          <Button
            icon={<MenuOutlined />}
            onClick={() => setMobileMenuOpen(true)}
          />
        )}
        <Link to="/" style={{ textDecoration: 'none', color: 'inherit' }}>
          <Typography.Text
            strong
            style={{ fontSize: 18, color: 'var(--atmr-accent-default)', whiteSpace: 'nowrap' }}
          >
            RTK CRM
          </Typography.Text>
        </Link>
        {screens.md ? (
          <Menu
            mode="horizontal"
            selectedKeys={[location.pathname]}
            items={items}
            onClick={({ key }) => navigate(key)}
            style={{ flex: 1, borderBottom: 'none', minWidth: 0 }}
          />
        ) : null}
        <Space>
          {screens.md && (
            <Typography.Text type="secondary">{user?.full_name}</Typography.Text>
          )}
          <Tooltip title={`Тема: ${themeTitle}`}>
            <Button
              type="text"
              aria-label={`Тема: ${themeTitle}. Переключить`}
              icon={<BulbOutlined />}
              onClick={cycleTheme}
            />
          </Tooltip>
          <Tooltip title="Выйти">
            <Button
              type="text"
              icon={<LogoutOutlined />}
              onClick={() => {
                signOut();
                navigate('/login');
              }}
            />
          </Tooltip>
        </Space>
      </Header>

      <Drawer
        placement="left"
        open={mobileMenuOpen}
        onClose={() => setMobileMenuOpen(false)}
      >
        <Menu
          mode="vertical"
          selectedKeys={[location.pathname]}
          items={items}
          onClick={({ key }) => {
            navigate(key);
            setMobileMenuOpen(false);
          }}
        />
      </Drawer>
      <Content className="main-content" style={{ padding: screens.md ? 24 : 12 }}>
        <Outlet />
      </Content>
      <AppFooter />
    </Layout>
  );
}
