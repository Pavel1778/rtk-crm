import React, { useState } from 'react';
import MainLayout from './components/MainLayout';
import KanbanBoard from './components/KanbanBoard';
import { Typography, Card, Row, Col, Statistic, Progress } from 'antd';
import {
  TeamOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  FileTextOutlined,
} from '@ant-design/icons';

const { Title, Paragraph } = Typography;

// Заглушка данных для дашборда (в реальности будет API)
const dashboardStats = {
  totalUniversities: 42,
  activeContracts: 28,
  pendingStages: 14,
  completedThisMonth: 7,
};

const App: React.FC = () => {
  const [currentView, setCurrentView] = useState<'dashboard' | 'kanban'>('dashboard');

  const renderContent = () => {
    if (currentView === 'kanban') {
      return <KanbanBoard />;
    }

    return (
      <div>
        <Title level={2}>Добро пожаловать в RTK CRM</Title>
        <Paragraph style={{ fontSize: 16, color: '#666', marginBottom: 32 }}>
          Система управления взаимодействием с вузами ИТ Школы Ростелекома
        </Paragraph>

        {/* Статистика */}
        <Row gutter={[16, 16]} style={{ marginBottom: 32 }}>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="Всего вузов"
                value={dashboardStats.totalUniversities}
                prefix={<TeamOutlined />}
                valueStyle={{ color: '#0066CC' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="Активные договоры"
                value={dashboardStats.activeContracts}
                prefix={<CheckCircleOutlined />}
                valueStyle={{ color: '#52c41a' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="В работе"
                value={dashboardStats.pendingStages}
                prefix={<ClockCircleOutlined />}
                valueStyle={{ color: '#faad14' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="Завершено за месяц"
                value={dashboardStats.completedThisMonth}
                prefix={<FileTextOutlined />}
                valueStyle={{ color: '#722ed1' }}
              />
            </Card>
          </Col>
        </Row>

        {/* Прогресс по этапам */}
        <Card title="Прогресс внедрения" style={{ marginBottom: 24 }}>
          <div style={{ marginBottom: 16 }}>
            <div style={{ marginBottom: 8 }}>Общий прогресс</div>
            <Progress percent={67} status="active" />
          </div>
          <div style={{ marginBottom: 16 }}>
            <div style={{ marginBottom: 8 }}>Подписание договоров</div>
            <Progress percent={85} strokeColor="#52c41a" />
          </div>
          <div>
            <div style={{ marginBottom: 8 }}>Обучение преподавателей</div>
            <Progress percent={45} strokeColor="#faad14" />
          </div>
        </Card>

        {/* Быстрый доступ */}
        <Row gutter={[16, 16]}>
          <Col xs={24} md={12}>
            <Card
              hoverable
              onClick={() => setCurrentView('kanban')}
              style={{ cursor: 'pointer', height: '100%' }}
            >
              <Title level={4} style={{ marginTop: 0 }}>
                📋 Kanban доска
              </Title>
              <Paragraph>
                Визуализация всех этапов работы с вузами. Перетаскивайте карточки между колонками,
                отслеживайте прогресс.
              </Paragraph>
            </Card>
          </Col>
          <Col xs={24} md={12}>
            <Card hoverable style={{ cursor: 'pointer', height: '100%' }}>
              <Title level={4} style={{ marginTop: 0 }}>
                📊 Отчёты
              </Title>
              <Paragraph>
                Генерация отчётов в форматах PDF и XLSX. Статистика по вузам, менеджерам и этапам.
              </Paragraph>
            </Card>
          </Col>
        </Row>
      </div>
    );
  };

  return <MainLayout>{renderContent()}</MainLayout>;
};

export default App;
