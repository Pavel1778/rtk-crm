import { useEffect, useState } from 'react';
import { Card, Empty, Result, Skeleton, message } from 'antd';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, Legend,
  LineChart, Line,
} from 'recharts';
import { api, downloadBlob, errorMessage } from '../api/client';
import { downloadReport } from '../api/endpoints';
import { useDevice } from '../hooks/useDevice';
import EmptyState from '../components/EmptyState';
import MetricCard from '../components/dashboard/MetricCard';
import type { ReportResponse } from '../types';

const COLORS = ['#6E41F2', '#00AC43', '#F5A623', '#E5484D', '#3B82F6', '#8B5CF6'];

export default function ReportPage() {
  const device = useDevice();
  const isMobile = device === 'mobile';
  const [data, setData] = useState<ReportResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [exporting, setExporting] = useState<string | null>(null);

  useEffect(() => {
    api.get('/api/reports')
      .then((res) => setData(res.data))
      .catch(() => {
        setError(true);
        message.error('Не удалось загрузить отчёт');
      })
      .finally(() => setLoading(false));
  }, []);

  const handleExport = async (format: 'xlsx' | 'xls' | 'pdf') => {
    setExporting(format);
    try {
      const result = await downloadReport(format);
      downloadBlob(result.blob, result.filename);
    } catch (error) {
      message.error(errorMessage(error, 'Не удалось скачать отчёт'));
    } finally {
      setExporting(null);
    }
  };

  if (loading) {
    return (
      <div className="page-container">
        <Skeleton active paragraph={{ rows: 12 }} />
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-container">
        <Result status="warning" title="Не удалось загрузить отчёт" />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="page-container">
        <h1>Отчёты</h1>
        <Empty description="Нет данных за выбранный период" />
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
            disabled={exporting !== null}
          >
            Экспорт XLSX
          </button>
          <button
            onClick={() => handleExport('xls')}
            className="btn-export"
            disabled={exporting !== null}
          >
            Экспорт XLS
          </button>
          <button
            onClick={() => handleExport('pdf')}
            className="btn-export"
            disabled={exporting !== null}
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
        {data.by_stage.length === 0 ? (
          <EmptyState title="Нет данных" />
        ) : (
          <div
            className="chart-container"
            style={{ height: isMobile ? 500 : 600 }}
          >
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={data.by_stage}
                layout="vertical"
                margin={{
                  top: 8,
                  right: 30,
                  left: 0,
                  bottom: 8,
                }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#EEEEF2" horizontal={isMobile} vertical={!isMobile} />
                <XAxis type="number" allowDecimals={false} />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={isMobile ? 150 : 220}
                  tick={{ fontSize: 12 }}
                  tickFormatter={(value: string) =>
                    value.length > 32 ? `${value.slice(0, 30)}…` : value
                  }
                />
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
          {data.by_product.length === 0 ? (
            <EmptyState title="Нет данных" />
          ) : (
            <div className="chart-container" style={{ height: 320 }}>
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={data.by_product}
                    dataKey="count"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={90}
                    paddingAngle={2}
                  >
                    {data.by_product.map((_, i) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value) => [value, 'Взаимодействий']} />
                  <Legend
                    verticalAlign="bottom"
                    wrapperStyle={{ fontSize: 11 }}
                    formatter={(value: string) =>
                      value.length > 24 ? `${value.slice(0, 22)}…` : value
                    }
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>

        {/* Динамика за 30 дней */}
        <Card title="Динамика за 30 дней" style={{ borderRadius: 12 }}>
          {data.dynamics.length === 0 ? (
            <EmptyState title="Нет данных" />
          ) : (
            <div className="chart-container" style={{ height: 320 }}>
              <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={data.dynamics} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#EEEEF2" />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: isMobile ? 10 : 11 }}
                    tickFormatter={(v) => v?.slice(5) || ''}
                    minTickGap={24}
                  />
                  <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                  <Tooltip labelFormatter={(value) => `Дата: ${value}`} />
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
