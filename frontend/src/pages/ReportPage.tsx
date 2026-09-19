import { BarChartOutlined, DownloadOutlined } from '@ant-design/icons';
import { Button, Card, Col, Empty, Progress, Row, Space, Spin, Statistic, Typography } from 'antd';
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

import { errorMessage } from '../api/client';
import { exportPdf, exportXls, exportXlsx, getReport } from '../api/endpoints';
import type { ReportResponse } from '../types';

/**
 * Отчёт: ключевые показатели и распределение взаимодействий по этапам.
 * Графики с recharts.
 */
export default function ReportPage() {
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

      saveAs(blob, filename);
    } catch (err) {
      errorMessage(err, 'Не удалось экспортировать отчёт');
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
      .catch((err) => setError(errorMessage(err, 'Не удалось загрузить отчёт')))
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
    return <Empty description={error ?? 'Нет данных'} image={Empty.PRESENTED_IMAGE_SIMPLE} />;
  }

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Row justify="end">
        <Space>
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
        </Space>
      </Row>
      <Row gutter={[16, 16]}>
        {data.metrics.map((metric) => (
          <Col key={metric.key} xs={12} md={8} lg={4}>
            <Card style={{ border: '1px solid #EEEEF2' }}>
              <Statistic
                title={metric.label}
                value={metric.value}
                valueStyle={{ color: '#6E41F2' }}
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
          <Empty description="Нет активных взаимодействий" />
        )}
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={stageData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" angle={-45} textAnchor="end" height={100} />
            <YAxis />
            <Tooltip />
            <Legend />
            <Bar dataKey="count" fill="#6E41F2" />
          </BarChart>
        </ResponsiveContainer>
      </Card>

      <Row gutter={[16, 16]}>
        <Col xs={24} md={12}>
          <Card title="Доля продуктов" style={{ border: '1px solid #EEEEF2' }}>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={productData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {productData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card title="Динамика за 30 дней" style={{ border: '1px solid #EEEEF2' }}>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={lineData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="day" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="interactions" stroke="#6E41F2" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </Card>
        </Col>
      </Row>
    </Space>
  );
}
