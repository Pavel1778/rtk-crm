import React, { useState } from 'react';
import { Layout, Menu, Avatar, Dropdown, theme, Switch } from 'antd';
import {
  UserOutlined,
  DashboardOutlined,
  KanbanOutlined,
  FileTextOutlined,
  SettingOutlined,
  ImportOutlined,
  QuestionCircleOutlined,
  SunOutlined,
  MoonOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
} from '@ant-design/icons';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { useThemeStore } from '../stores/themeStore';

const { Header, Sider, Content } = Layout;

export const MainLayout: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuth();
  const { isDark, toggleTheme } = useThemeStore();
  const {
    token: { colorBgContainer, borderRadiusLG },
  } = theme.useToken();

  const menuItems = [
    {
      key: '/dashboard',
      icon: <DashboardOutlined />,
      label: 'Дашборд',
    },
    {
      key: '/kanban',
      icon: <KanbanOutlined />,
      label: 'Kanban',
    },
    {
      key: '/reports',
      icon: <FileTextOutlined />,
      label: 'Отчёты',
    },
    {
      key: '/workflow',
      icon: <SettingOutlined />,
      label: 'Workflow',
      labelOnlyAdmin: true,
    },
    {
      key: '/import',
      icon: <ImportOutlined />,
      label: 'Импорт',
      labelOnlyAdmin: true,
    },
    {
      key: '/help',
      icon: <QuestionCircleOutlined />,
      label: 'Помощь',
    },
  ];

  const userMenuItems = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: user?.full_name || user?.email,
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: 'Выйти',
      onClick: () => {
        logout();
        navigate('/login');
      },
    },
  ];

  const filteredMenuItems = menuItems.filter((item) => {
    if (item.labelOnlyAdmin && user?.role !== 'admin') {
      return false;
    }
    return true;
  });

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider 
        trigger={null} 
        collapsible 
        collapsed={collapsed}
        theme={isDark ? 'dark' : 'light'}
        width={240}
      >
        <div style={{ 
          height: 64, 
          margin: collapsed ? 8 : 16, 
          background: 'var(--atmr-accent-default)',
          borderRadius: 8,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'white',
          fontWeight: 'bold',
          fontSize: collapsed ? 0 : 16,
          overflow: 'hidden'
        }}>
          {!collapsed && 'RTK CRM'}
        </div>
        <Menu
          theme={isDark ? 'dark' : 'light'}
          mode="inline"
          selectedKeys={[location.pathname]}
          items={filteredMenuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header style={{ 
          padding: '0 16px', 
          background: colorBgContainer,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            {React.createElement(collapsed ? MenuUnfoldOutlined : MenuFoldOutlined, {
              className: 'trigger',
              onClick: () => setCollapsed(!collapsed),
              style: { fontSize: 18, cursor: 'pointer' }
            })}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <Switch
              checkedChildren={<SunOutlined />}
              unCheckedChildren={<MoonOutlined />}
              checked={isDark}
              onChange={toggleTheme}
            />
            <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
              <Avatar 
                style={{ backgroundColor: 'var(--atmr-accent-default)', cursor: 'pointer' }}
                icon={<UserOutlined />}
                size="large"
              />
            </Dropdown>
          </div>
        </Header>
        <Content
          style={{
            margin: '16px',
            padding: 24,
            minHeight: 280,
            background: colorBgContainer,
            borderRadius: borderRadiusLG,
            overflow: 'auto'
          }}
        >
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
};
