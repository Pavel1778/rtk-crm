import { BarChartOutlined, DownloadOutlined } from '@ant-design/icons';
import { App as AntApp, Button, Card, Col, Row, Spin, Statistic } from 'antd';
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
        {data.metrics.map((metric) => (
          <Col key={metric.key} xs={12} md={8} lg={4}>
            <Card className="stat-card" style={{ border: '1px solid #EEEEF2', textAlign: 'center' }}>
              <Statistic
                title={metric.label}
                value={metric.value}
                valueStyle={{ color: '#6E41F2', fontSize: 28, fontWeight: 600 }}
              />
            </Card>
          </Col>
        ))}
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
            <BarChart data={stageData} layout="vertical" margin={{ left: isMobile ? 180 : 200, right: 20, top: 20, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                type="number" 
                tick={{ fontSize: isMobile ? 10 : 12 }}
                allowDecimals={false}
              />
              <YAxis 
                dataKey="name" 
                type="category" 
                width={isMobile ? 180 : 200} 
                tick={{ fontSize: isMobile ? 10 : 12 }}
                tickFormatter={(v: string) => v.length > 15 ? v.slice(0, 12) + '…' : v}
              />
              <Tooltip 
                contentStyle={{ 
                  borderRadius: 8,
                  boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                  border: '1px solid #EEEEF2',
                  fontSize: isMobile ? 11 : 13,
                }}
                wrapperStyle={{ zIndex: 1000 }}
              />
              <Legend 
                verticalAlign={isMobile ? 'bottom' : 'top'}
                height={isMobile ? 60 : 36}
                wrapperStyle={{ fontSize: isMobile ? 10 : 12 }}
              />
              <Bar 
                dataKey="count" 
                fill="#6E41F2" 
                radius={[0, 4, 4, 0]}
                maxBarSize={isMobile ? 24 : 48}
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
