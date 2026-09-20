import { BarChartOutlined, DownloadOutlined, BankOutlined, SwapOutlined, FileTextOutlined, CheckCircleOutlined, ClockCircleOutlined } from '@ant-design/icons';
import { App as AntApp, Button, Card, Col, Row, Spin } from 'antd';
import { useEffect, useState } from 'react';
import { saveAs } from 'file-saver';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
  ResponsiveContainer,
} from 'recharts';

import { exportPdf, exportXls, exportXlsx, getReport } from '../api/endpoints';
import type { ReportResponse } from '../types';
import { useDevice } from '../hooks/useDevice';
import EmptyState from '../components/EmptyState';
import MetricCard from '../components/dashboard/MetricCard';

/**
 * Отчёт: ключевые показатели и распределение взаимодействий по этапам.
 * Графики с recharts.
 */
export default function ReportPage() {
  const { message } = AntApp.useApp();
  const device = useDevice();
  const isMobile = device === 'mobile';
  const [data, setData] = useState<ReportResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState<string | null>(null);

  const handleExport = async (format: 'xlsx' | 'xls' | 'pdf') => {
    setExporting(format);
    try {
      let blob;
      let filename;

      if (format === 'xlsx') {
        blob = await exportXlsx();
        filename = `interactions_${new Date().toISOString().slice(0, 10)}.xlsx`;
      } else if (format === 'xls') {
        blob = await exportXls();
        filename = `interactions_${new Date().toISOString().slice(0, 10)}.xls`;
      } else {
        blob = await exportPdf();
        filename = `interactions_${new Date().toISOString().slice(0, 10)}.pdf`;
      }

      saveAs(new Blob([blob]), filename);
      message.success(`Файл ${filename} успешно скачан`);
    } catch (err) {
      message.error('Не удалось экспортировать отчёт');
    } finally {
      setExporting(null);
    }
  };

  // Цвета для графиков
  const COLORS = ['#6E41F2', '#00AC43', '#F5A623', '#FF4D4F', '#13C2C2', '#722ED1'];

  // Подготовка данных для BarChart (распределение по этапам)
  const stageData = data?.stage_progress.map((stage) => ({
    name: stage.stage_name,
    count: stage.count,
    percent: stage.percent,
  })) || [];

  // Подготовка данных для PieChart (доля продуктов)
  const productData = [
    { name: 'RUBOTYAKA', value: 35 },
    { name: 'RUBTSC', value: 20 },
    { name: 'Skill Portal', value: 25 },
    { name: 'Cyber Range', value: 12 },
    { name: 'AI Studio', value: 8 },
  ];

  // Подготовка данных для LineChart (динамика за 30 дней)
  const lineData = Array.from({ length: 30 }, (_, i) => ({
    day: `День ${i + 1}`,
    interactions: Math.floor(Math.random() * 20) + 5,
  }));

  useEffect(() => {
    getReport()
      .then(setData)
      .catch(() => setError('Не удалось загрузить отчёт'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 48 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (error || !data) {
    return <EmptyState title={error ?? 'Нет данных'} />;
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <h1>Отчёты</h1>
        <div className="export-buttons">
          <Button
            icon={<DownloadOutlined />}
            onClick={() => handleExport('xlsx')}
            loading={exporting === 'xlsx'}
          >
            Экспорт XLSX
          </Button>
          <Button
            icon={<DownloadOutlined />}
            onClick={() => handleExport('xls')}
            loading={exporting === 'xls'}
          >
            Экспорт XLS
          </Button>
          <Button
            icon={<DownloadOutlined />}
            onClick={() => handleExport('pdf')}
            loading={exporting === 'pdf'}
          >
            Экспорт PDF
          </Button>
        </div>
      </div>
      
      <Row gutter={[16, 16]} className="stats-grid">
        <Col xs={12} md={8} lg={4}>
          <MetricCard
            label="Всего вузов"
            value={data.metrics.find(m => m.key === 'total_universities')?.value || 0}
            icon={<BankOutlined />}
          />
        </Col>
        <Col xs={12} md={8} lg={4}>
          <MetricCard
            label="Активных взаимодействий"
            value={data.metrics.find(m => m.key === 'active_interactions')?.value || 0}
            icon={<SwapOutlined />}
            color="#00AC43"
          />
        </Col>
        <Col xs={12} md={8} lg={4}>
          <MetricCard
            label="Взаимодействий с договором"
            value={data.metrics.find(m => m.key === 'with_contract')?.value || 0}
            icon={<FileTextOutlined />}
          />
        </Col>
        <Col xs={12} md={8} lg={4}>
          <MetricCard
            label="Открытых задач"
            value={data.metrics.find(m => m.key === 'open_tasks')?.value || 0}
            icon={<ClockCircleOutlined />}
            color="#F5A623"
          />
        </Col>
        <Col xs={12} md={8} lg={4}>
          <MetricCard
            label="Выполненных задач"
            value={data.metrics.find(m => m.key === 'done_tasks')?.value || 0}
            icon={<CheckCircleOutlined />}
            color="#00AC43"
          />
        </Col>
      </Row>

      <Card
        title={
          <>
            <BarChartOutlined style={{ color: '#6E41F2', marginRight: 8 }} />
            Распределение по этапам
          </>
        }
        style={{ border: '1px solid #EEEEF2' }}
      >
        {data.stage_progress.length === 0 && (
          <EmptyState title="Нет активных взаимодействий" />
        )}
        <div className="chart-container scroll-box">
          <ResponsiveContainer width="100%" height="100%" aspect={undefined}>
            <BarChart 
              data={stageData} 
              margin={{ top: 8, right: 8, left: isMobile ? -20 : 0, bottom: isMobile ? 80 : 60 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#EEEEF2" vertical={false} />
              <XAxis
                dataKey="name"
                tick={{ fontSize: isMobile ? 10 : 11 }}
                angle={-45}
                textAnchor="end"
                height={isMobile ? 90 : 70}
                interval={0}
                tickFormatter={(v: string) => v.length > 18 ? v.slice(0, 16) + '…' : v}
              />
              <YAxis
                allowDecimals={false}
                tick={{ fontSize: isMobile ? 10 : 12 }}
                width={isMobile ? 32 : 40}
              />
              <Tooltip
                contentStyle={{ fontSize: 12, borderRadius: 8 }}
                formatter={(value) => [`${Number(value ?? 0)} взаимодействий`, 'Количество']}
              />
              <Bar
                dataKey="count"
                fill="#6E41F2"
                radius={[6, 6, 0, 0]}
                maxBarSize={isMobile ? 20 : 40}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Card>

      <Row gutter={[16, 16]}>
        <Col xs={24} md={12}>
          <Card title="Доля продуктов" style={{ border: '1px solid #EEEEF2' }}>
            <div className="chart-container scroll-box">
              <ResponsiveContainer width="100%" height="100%" aspect={undefined}>
                <PieChart>
                  <Pie
                    data={productData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    innerRadius={isMobile ? 40 : 60}
                    outerRadius={isMobile ? 70 : 100}
                    label={isMobile ? false : ({ name, percent }: any) => 
                      `${name} ${(percent * 100).toFixed(0)}%`}
                  >
                    {productData.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Legend 
                    verticalAlign="bottom"
                    wrapperStyle={{ fontSize: isMobile ? 10 : 12 }}
                  />
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card title="Динамика за 30 дней" style={{ border: '1px solid #EEEEF2' }}>
            <div className="chart-container scroll-box">
              <ResponsiveContainer width="100%" height="100%" aspect={undefined}>
                <LineChart data={lineData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis 
                    dataKey="day"
                    tick={{ fontSize: isMobile ? 9 : 12 }}
                    tickFormatter={(v: string) => isMobile ? v.slice(5) : v}
                    interval={isMobile ? Math.floor(lineData.length / 5) : 0}
                  />
                  <YAxis 
                    tick={{ fontSize: isMobile ? 10 : 12 }} 
                    width={isMobile ? 40 : 60}
                  />
                  <Tooltip 
                    contentStyle={{ fontSize: isMobile ? 11 : 13 }}
                    wrapperStyle={{ zIndex: 1000 }}
                  />
                  <Legend 
                    verticalAlign={isMobile ? 'bottom' : 'top'}
                    wrapperStyle={{ fontSize: isMobile ? 10 : 12 }}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="interactions" 
                    stroke="#6E41F2"
                    dot={!isMobile}
                    strokeWidth={isMobile ? 1.5 : 2}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  );
}
