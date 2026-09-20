import { useEffect, useState } from 'react';
import { Card, message, Spin } from 'antd';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, Legend,
  LineChart, Line,
} from 'recharts';
import { api } from '../api/client';
import { useDevice } from '../hooks/useDevice';
import EmptyState from '../components/EmptyState';
import MetricCard from '../components/dashboard/MetricCard';

interface ReportData {
  metrics: Array<{ key: string; label: string; value: number }>;
  stage_progress: Array<{ stage_code: string; stage_name: string; count: number }>;
  products?: Array<{ name: string; value: number }>;
  dynamics?: Array<{ date: string; count: number }>;
}

const COLORS = ['#6E41F2', '#8A63F5', '#A88BFA', '#C4B0FC', '#E0D5FE'];

export default function ReportPage() {
  const device = useDevice();
  const isMobile = device === 'mobile';
  const [data, setData] = useState<ReportData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/api/reports')
      .then((res) => setData(res.data))
      .catch(() => message.error('Не удалось загрузить отчёт'))
      .finally(() => setLoading(false));
  }, []);

  const handleExport = (format: 'xlsx' | 'xls' | 'pdf') => {
    window.open(
      `${import.meta.env.VITE_API_URL}/api/reports/${format}`,
      '_blank'
    );
  };

  if (loading) {
    return (
      <div style={{ padding: 40, textAlign: 'center' }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="page-container">
        <h1>Отчёты</h1>
        <EmptyState
          title="Нет данных"
          description="Не удалось загрузить отчёт"
        />
      </div>
    );
  }

  return (
    <div className="page-container">
      {/* Заголовок + кнопки экспорта */}
      <div className="page-header">
        <h1>Отчёты</h1>
        <div className="export-buttons">
          <button
            onClick={() => handleExport('xlsx')}
            className="btn-export"
          >
            Экспорт XLSX
          </button>
          <button
            onClick={() => handleExport('xls')}
            className="btn-export"
          >
            Экспорт XLS
          </button>
          <button
            onClick={() => handleExport('pdf')}
            className="btn-export"
          >
            Экспорт PDF
          </button>
        </div>
      </div>

      {/* KPI-карточки */}
      <div className="stats-grid" style={{ marginBottom: 24 }}>
        {data.metrics.map((m) => (
          <MetricCard
            key={m.key}
            label={m.label}
            value={m.value}
          />
        ))}
      </div>

      {/* График: Распределение по этапам */}
      <Card
        title="Распределение по этапам"
        style={{ borderRadius: 12, marginBottom: 24 }}
      >
        {data.stage_progress.length === 0 ? (
          <EmptyState title="Нет данных" />
        ) : (
          <div
            className="chart-container"
            style={{ height: isMobile ? 500 : 600 }}
          >
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={data.stage_progress}
                layout={isMobile ? "horizontal" : "vertical"}
                margin={{
                  top: 8,
                  right: 30,
                  left: isMobile ? 10 : 20,
                  bottom: isMobile ? 60 : 8,
                }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#EEEEF2" horizontal={isMobile} vertical={!isMobile} />
                {isMobile ? (
                  <>
                    <XAxis
                      dataKey="stage_name"
                      tick={{ fontSize: 10 }}
                      angle={-45}
                      textAnchor="end"
                      height={70}
                      interval={0}
                      tickFormatter={(v) =>
                        v && v.length > 18 ? v.slice(0, 16) + '…' : v
                      }
                    />
                    <YAxis
                      allowDecimals={false}
                      tick={{ fontSize: 10 }}
                      width={32}
                    />
                  </>
                ) : (
                  <>
                    <XAxis
                      type="number"
                      allowDecimals={false}
                      tick={{ fontSize: 12 }}
                    />
                    <YAxis
                      type="category"
                      dataKey="stage_name"
                      width={260}
                      tick={{ fontSize: 12 }}
                      tickFormatter={(v) =>
                        v && v.length > 35 ? v.slice(0, 33) + '…' : v
                      }
                    />
                  </>
                )}
                <Tooltip
                  contentStyle={{ fontSize: 12, borderRadius: 8 }}
                  formatter={(value) => [
                    Number(value ?? 0),
                    'Взаимодействий',
                  ]}
                />
                <Bar 
                  dataKey="count" 
                  fill="#6E41F2" 
                  radius={isMobile ? [6, 6, 0, 0] : [0, 6, 6, 0]} 
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </Card>

      {/* Два графика в ряд */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr',
          gap: 24,
        }}
      >
        {/* Доля продуктов */}
        <Card title="Доля продуктов" style={{ borderRadius: 12 }}>
          {!data.products || data.products.length === 0 ? (
            <EmptyState title="Нет данных" />
          ) : (
            <div className="chart-container" style={{ height: 320 }}>
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={data.products}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={90}
                    paddingAngle={2}
                  >
                    {data.products.map((_, i) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend
                    verticalAlign="bottom"
                    wrapperStyle={{ fontSize: 11 }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>

        {/* Динамика за 30 дней */}
        <Card title="Динамика за 30 дней" style={{ borderRadius: 12 }}>
          {!data.dynamics || data.dynamics.length === 0 ? (
            <EmptyState title="Нет данных" />
          ) : (
            <div className="chart-container" style={{ height: 320 }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data.dynamics}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#EEEEF2" />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: isMobile ? 10 : 11 }}
                    tickFormatter={(v) => v?.slice(5) || ''}
                  />
                  <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                  <Tooltip />
                  <Line
                    type="monotone"
                    dataKey="count"
                    stroke="#6E41F2"
                    strokeWidth={2}
                    dot={!isMobile}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
