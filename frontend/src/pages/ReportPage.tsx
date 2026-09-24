import { useEffect, useRef, useState } from 'react';
import { Card, Empty, Result, Segmented, Skeleton, message } from 'antd';
import { useQuery } from '@tanstack/react-query';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, Legend,
  LineChart, Line,
} from 'recharts';
import { downloadBlob, errorMessage } from '../api/client';
import {
  downloadReport,
  getReport,
  getReportPreview,
  type ReportFilters,
} from '../api/endpoints';
import { useDevice } from '../hooks/useDevice';
import EmptyState from '../components/EmptyState';
import MetricCard from '../components/dashboard/MetricCard';
import ChartExportButtons from '../components/dashboard/ChartExportButtons';
import DateRangeFilter, { type DateRangeValue } from '../components/DateRangeFilter';
import ReportTable from '../components/report/ReportTable';
import type { ReportResponse, ReportTableRow, WorkflowScope } from '../types';

const COLORS = [
  'var(--atmr-accent-default)',
  'var(--atmr-success-default)',
  'var(--atmr-warning-default)',
  'var(--atmr-error-default)',
  'var(--atmr-info-default)',
  'var(--atmr-accent-muted)',
];

const RADIAN = Math.PI / 180;
// Сектора уже 5% слишком тонкие для подписи внутри — выносим их с выноской.
const SMALL_SLICE = 0.05;

function ProductSliceLabel({
  cx = 0, cy = 0, midAngle, innerRadius = 0, outerRadius = 0, percent, compact,
}: {
  cx?: number; cy?: number; midAngle?: number; innerRadius?: number;
  outerRadius?: number; percent?: number; compact: boolean;
}) {
  if (!percent || midAngle === undefined) return null;
  const pct = `${Math.round(percent * 100)}%`;
  const cos = Math.cos(-midAngle * RADIAN);
  const sin = Math.sin(-midAngle * RADIAN);
  const font = compact ? 10 : 11;

  if (percent >= SMALL_SLICE) {
    const r = innerRadius + (outerRadius - innerRadius) * 0.5;
    return (
      <text
        x={cx + r * cos}
        y={cy + r * sin}
        fill="var(--atmr-chart-label)"
        stroke="var(--atmr-chart-label-halo)"
        strokeWidth={2.5}
        paintOrder="stroke"
        fontSize={font}
        fontWeight={600}
        textAnchor="middle"
        dominantBaseline="central"
      >
        {pct}
      </text>
    );
  }

  const lead = compact ? 10 : 16;
  const sx = cx + (outerRadius + 1) * cos;
  const sy = cy + (outerRadius + 1) * sin;
  const ex = cx + (outerRadius + lead) * cos;
  const ey = cy + (outerRadius + lead) * sin;
  const right = cos >= 0;
  return (
    <g>
      <polyline
        points={`${sx},${sy} ${ex},${ey}`}
        stroke="var(--atmr-fg-subtle)"
        strokeWidth={1}
        fill="none"
      />
      <text
        x={ex + (right ? 4 : -4)}
        y={ey}
        fill="var(--atmr-fg-subtle)"
        fontSize={font}
        textAnchor={right ? 'start' : 'end'}
        dominantBaseline="central"
      >
        {pct}
      </text>
    </g>
  );
}

export default function ReportPage() {
  const device = useDevice();
  const isMobile = device === 'mobile';
  const [exporting, setExporting] = useState<string | null>(null);
  const [draftDates, setDraftDates] = useState<DateRangeValue>({});
  const [filters, setFilters] = useState<ReportFilters>({});
  // Воронка — часть фильтра отчёта: у B2B и B2C разные наборы этапов,
  // и без явного scope график смешивал бы обе воронки.
  const [scope, setScope] = useState<WorkflowScope>('b2b');
  const stageChartRef = useRef<HTMLDivElement>(null);
  const productChartRef = useRef<HTMLDivElement>(null);
  const dynamicsChartRef = useRef<HTMLDivElement>(null);

  const appliedFilters: ReportFilters = { ...filters, scope };

  const reportQuery = useQuery<ReportResponse>({
    queryKey: ['report', appliedFilters],
    queryFn: () => getReport(appliedFilters),
  });
  const previewQuery = useQuery<ReportTableRow[]>({
    queryKey: ['report-preview', appliedFilters],
    queryFn: () => getReportPreview(appliedFilters),
  });
  const { data, isError: error, isLoading: loading } = reportQuery;
  const stageChartHeight = Math.max(
    360,
    data?.by_stage.length ? data.by_stage.length * 42 + 48 : 360,
  );
  const productTotal =
    data?.by_product.reduce((sum, p) => sum + p.count, 0) || 0;
  // Легенда recharts отдаёт имя продукта, а не исходный элемент — по имени
  // достаём count, чтобы посчитать долю. Имена продуктов уникальны.
  const legendByName = new Map(
    (data?.by_product ?? []).map((p) => [p.name, p]),
  );

  useEffect(() => {
    if (error) {
      message.error('Не удалось загрузить отчёт');
    }
  }, [error]);

  const handleExport = async (format: 'xlsx' | 'xls' | 'pdf') => {
    setExporting(format);
    try {
      const result = await downloadReport(format, appliedFilters);
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
      <div className="responsive-form report-filters" role="search" aria-label="Фильтры отчёта">
        <Segmented
          id="report-scope"
          value={scope}
          onChange={(value) => setScope(value as WorkflowScope)}
          options={[
            { value: 'b2b', label: 'B2B' },
            { value: 'b2c', label: 'B2C' },
          ]}
        />
        <DateRangeFilter
          id="report-date-range"
          value={draftDates}
          onChange={setDraftDates}
        />
        <button
          className="btn-export"
          onClick={() => setFilters({
            date_from: draftDates.date_from || undefined,
            date_to: draftDates.date_to || undefined,
          })}
        >
          Применить фильтры
        </button>
        <button
          className="btn-export"
          onClick={() => {
            setDraftDates({});
            setFilters({});
          }}
        >
          Сбросить
        </button>
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
        extra={
          data.by_stage.length > 0 && (
            <ChartExportButtons
              target={() => stageChartRef.current}
              filename="report-by-stage"
              title="Распределение взаимодействий по этапам"
            />
          )
        }
        style={{ borderRadius: 12, marginBottom: 24 }}
      >
        {data.by_stage.length === 0 ? (
          <EmptyState title="Нет данных" />
        ) : (
          <div
            ref={stageChartRef}
            data-chart-export="report-by-stage"
            className="chart-container report-stage-chart"
            style={{
              height: isMobile
                ? Math.max(420, data.by_stage.length * 38)
                : stageChartHeight,
              background: 'var(--atmr-bg-container)',
            }}
          >
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={data.by_stage}
                layout="vertical"
                margin={{
                  top: 8,
                  right: 20,
                  left: 8,
                  bottom: 8,
                }}
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="var(--atmr-border-default)"
                  horizontal
                  vertical={false}
                />
                <XAxis type="number" allowDecimals={false} />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={240}
                  tick={{ fontSize: 12 }}
                  tickFormatter={(value: string) =>
                    value.length > (isMobile ? 25 : 42)
                      ? `${value.slice(0, isMobile ? 23 : 40)}…`
                      : value
                  }
                />
                <Tooltip
                  contentStyle={{ fontSize: 12, borderRadius: 8 }}
                  labelFormatter={(label) => String(label)}
                  formatter={(value) => [
                    Number(value ?? 0),
                    'Взаимодействий',
                  ]}
                />
                <Bar 
                  dataKey="count" 
                  fill="var(--atmr-accent-default)"
                  radius={isMobile ? [6, 6, 0, 0] : [0, 6, 6, 0]} 
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </Card>

      {/* Два графика в ряд */}
      <div
        className="report-chart-grid"
      >
        {/* Доля продуктов */}
        <Card
          title="Доля продуктов"
          extra={
            data.by_product.length > 0 && (
              <ChartExportButtons
                target={() => productChartRef.current}
                filename="report-by-product"
                title="Доля продуктов"
              />
            )
          }
          style={{ borderRadius: 12 }}
        >
          {data.by_product.length === 0 ? (
            <EmptyState title="Нет активных взаимодействий с указанным продуктом" />
          ) : (
            <div
              ref={productChartRef}
              data-chart-export="report-by-product"
              className="chart-container"
              style={{ height: 320, background: 'var(--atmr-bg-container)' }}
            >
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={data.by_product}
                    dataKey="count"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={2}
                    labelLine={false}
                    label={(props) => (
                      <ProductSliceLabel {...props} compact={isMobile} />
                    )}
                  >
                    {data.by_product.map((_, i) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(value) => {
                      const n = Number(value);
                      const pct = productTotal
                        ? Math.round((n / productTotal) * 100)
                        : 0;
                      return [`${n} (${pct}%)`, 'Взаимодействий'];
                    }}
                  />
                  <Legend
                    layout={isMobile ? 'horizontal' : 'vertical'}
                    align={isMobile ? 'center' : 'right'}
                    verticalAlign={isMobile ? 'bottom' : 'middle'}
                    wrapperStyle={{ fontSize: 11 }}
                    formatter={(value: string) => {
                      const item = legendByName.get(value);
                      const pct = item
                        ? Math.round((item.count / productTotal) * 100)
                        : 0;
                      return `${value} — ${pct}%`;
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>

        {/* Динамика за 30 дней */}
        <Card
          title="Динамика за 30 дней"
          extra={
            data.dynamics.length > 0 && (
              <ChartExportButtons
                target={() => dynamicsChartRef.current}
                filename="report-dynamics"
                title="Динамика взаимодействий за 30 дней"
              />
            )
          }
          style={{ borderRadius: 12 }}
        >
          {data.dynamics.length === 0 ? (
            <EmptyState title="Нет данных за последние 30 дней" />
          ) : (
            <div
              ref={dynamicsChartRef}
              data-chart-export="report-dynamics"
              className="chart-container"
              style={{ height: 320, background: 'var(--atmr-bg-container)' }}
            >
              <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={data.dynamics} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--atmr-border-default)" />
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
                    stroke="var(--atmr-accent-default)"
                    strokeWidth={2}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>
      </div>

      {/* Таблица: те же строки и колонки, что в PDF/XLS-выгрузке */}
      <div style={{ marginTop: 24 }}>
        <ReportTable
          rows={previewQuery.data ?? []}
          loading={previewQuery.isLoading}
          title="Данные отчёта"
        />
      </div>
    </div>
  );
}
