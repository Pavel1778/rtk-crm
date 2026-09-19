import {
  AppstoreOutlined,
  BarChartOutlined,
  DatabaseOutlined,
  LogoutOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import { Button, Grid, Layout, Menu, Space, Tooltip, Typography } from 'antd';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';

import { useAuthStore, useRole } from '../stores/authStore';

const { Header, Content } = Layout;

const MENU_ITEMS = [
  { key: '/', icon: <AppstoreOutlined />, label: 'Доска' },
  { key: '/reports', icon: <BarChartOutlined />, label: 'Отчёты' },
  { key: '/directories', icon: <DatabaseOutlined />, label: 'Справочники' },
];

const ADMIN_ITEM = {
  key: '/settings',
  icon: <SettingOutlined />,
  label: 'Пользователи',
};

export default function MainLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const user = useAuthStore((s) => s.user);
  const signOut = useAuthStore((s) => s.signOut);
  const role = useRole();
  const screens = Grid.useBreakpoint();

  const items = role === 'admin'
    ? [...MENU_ITEMS, ADMIN_ITEM]
    : MENU_ITEMS;

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 16,
          padding: screens.md ? '0 24px' : '0 12px',
          borderBottom: '1px solid #EEEEF2',
          position: 'sticky',
          top: 0,
          zIndex: 100,
        }}
      >
        <Typography.Text
          strong
          style={{ fontSize: 18, color: '#6E41F2', whiteSpace: 'nowrap' }}
        >
          RTK CRM
        </Typography.Text>
        <Menu
          mode="horizontal"
          selectedKeys={[location.pathname]}
          items={items}
          onClick={({ key }) => navigate(key)}
          style={{ flex: 1, borderBottom: 'none', minWidth: 0 }}
        />
        <Space>
          {screens.md && (
            <Typography.Text type="secondary">{user?.full_name}</Typography.Text>
          )}
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
      <Content style={{ padding: screens.md ? 24 : 12 }}>
        <Outlet />
      </Content>
    </Layout>
  );
}
