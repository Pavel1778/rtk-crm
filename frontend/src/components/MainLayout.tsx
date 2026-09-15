import React, { useState, useEffect } from 'react';
import { Layout, Menu, Typography, Avatar, Dropdown } from 'antd';
import {
  DashboardOutlined,
  TeamOutlined,
  FileTextOutlined,
  SettingOutlined,
  UserOutlined,
  LogoutOutlined,
} from '@ant-design/icons';
import type { MenuProps } from 'antd';

const { Header, Sider, Content } = Layout;
const { Title } = Typography;

interface MainLayoutProps {
  children: React.ReactNode;
}

const MainLayout: React.FC<MainLayoutProps> = ({ children }) => {
  const [collapsed, setCollapsed] = useState(false);
  const [currentMenu, setCurrentMenu] = useState('dashboard');

  const menuItems: MenuProps['items'] = [
    {
      key: 'dashboard',
      icon: <DashboardOutlined />,
      label: 'Дашборд',
    },
    {
      key: 'universities',
      icon: <TeamOutlined />,
      label: 'Вузы',
    },
    {
      key: 'kanban',
      icon: <FileTextOutlined />,
      label: 'Kanban доска',
    },
    {
      key: 'reports',
      icon: <FileTextOutlined />,
      label: 'Отчёты',
    },
    {
      type: 'divider',
    },
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: 'Настройки',
    },
  ];

  const userMenuItems: MenuProps['items'] = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: 'Профиль',
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: 'Выйти',
      danger: true,
    },
  ];

  const handleMenuClick: MenuProps['onClick'] = (e) => {
    setCurrentMenu(e.key);
    // Здесь будет навигация по роутам
    console.log('Переход на:', e.key);
  };

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={(value) => setCollapsed(value)}
        theme="light"
        style={{
          boxShadow: '2px 0 8px rgba(0,0,0,0.05)',
          zIndex: 10,
        }}
      >
        <div
          style={{
            height: 64,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            borderBottom: '1px solid #f0f0f0',
          }}
        >
          {collapsed ? (
            <Avatar
              style={{ backgroundColor: '#0066CC' }}
              size={40}
              icon={<TeamOutlined />}
            />
          ) : (
            <Title level={4} style={{ margin: 0, color: '#0066CC' }}>
              RTK CRM
            </Title>
          )}
        </div>
        <Menu
          mode="inline"
          selectedKeys={[currentMenu]}
          items={menuItems}
          onClick={handleMenuClick}
          style={{ borderRight: 0 }}
        />
      </Sider>
      <Layout>
        <Header
          style={{
            padding: '0 24px',
            background: '#fff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            boxShadow: '0 2px 8px rgba(0,0,0,0.05)',
          }}
        >
          <Title level={4} style={{ margin: 0 }}>
            {currentMenu === 'dashboard' && 'Дашборд'}
            {currentMenu === 'universities' && 'Управление вузами'}
            {currentMenu === 'kanban' && 'Kanban доска'}
            {currentMenu === 'reports' && 'Отчёты'}
            {currentMenu === 'settings' && 'Настройки'}
          </Title>
          <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
            <Avatar
              style={{ backgroundColor: '#0066CC', cursor: 'pointer' }}
              size={40}
              icon={<UserOutlined />}
            />
          </Dropdown>
        </Header>
        <Content
          style={{
            margin: '24px 16px',
            padding: 24,
            background: '#fff',
            borderRadius: 8,
            minHeight: 280,
          }}
        >
          {children}
        </Content>
      </Layout>
    </Layout>
  );
};

export default MainLayout;
