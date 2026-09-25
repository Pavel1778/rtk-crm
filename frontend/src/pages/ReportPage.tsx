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

/** Разбивает название этапа на строки по словам.
 *
 * На телефоне подпись оси обрезалась до 14 символов, и по «Коммуникация и…»
 * нельзя было понять этап. Перенос по словам сохраняет текст читаемым;
 * `…` остаётся только как крайняя мера, если строки не вмещают название. */
function wrapLabel(text: string, perLine: number, maxLines: number): string[] {
  const lines: string[] = [];
  let current = '';
  for (const word of text.split(' ')) {
    const candidate = current ? `${current} ${word}` : word;
    if (!current || candidate.length <= perLine) {
      current = candidate;
    } else {
      lines.push(current);
      current = word;
    }
  }
  if (current) lines.push(current);
  if (lines.length <= maxLines) return lines;
  const kept = lines.slice(0, maxLines);
  const last = kept[maxLines - 1];
  kept[maxLines - 1] = `${last.slice(0, Math.max(1, perLine - 1))}…`;
  return kept;
}

interface StageTickProps {
  x?: number;
  y?: number;
  payload?: { value?: string | number };
  lines: number;
  perLine: number;
}

/** Подпись этапа на оси Y: до `lines` строк по `perLine` символов. */
function StageTick({ x = 0, y = 0, payload, lines, perLine }: StageTickProps) {
  const parts = wrapLabel(String(payload?.value ?? ''), perLine, lines);
  const lineHeight = 14;
  const offset = ((parts.length - 1) * lineHeight) / 2;
  return (
    <text
      x={x}
      y={y}
      textAnchor="end"
      fill="var(--atmr-fg-subtle)"
      fontSize={12}
    >
      {parts.map((part, index) => (
        <tspan
          key={index}
          x={x}
          y={y - offset + index * lineHeight}
          dominantBaseline="central"
        >
          {part}
        </tspan>
      ))}
    </text>
  );
}

// Recharts подставляет собственные цвета осей (#666), не зная о теме: на
// тёмном фоне это 2.83:1. Задаём цвет явно токеном для обеих тем.
const AXIS_TICK = { fill: 'var(--atmr-fg-subtle)' } as const;
const AXIS_TICK_SMALL = { fill: 'var(--atmr-fg-subtle)', fontSize: 10 } as const;

// Тултип recharts по умолчанию — светлая карточка с тёмным текстом: на
// тёмной теме выпадал из палитры и слепил. Берём поверхности и текст темы.
const TOOLTIP_STYLE = {
  fontSize: 12,
  borderRadius: 8,
  background: 'var(--atmr-bg-elevated)',
  border: '1px solid var(--atmr-border-default)',
  color: 'var(--atmr-fg-default)',
} as const;

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
  // Планшет: сайдбар сужает колонку, поэтому узкая ось и перенос подписей
  // нужны не только на телефоне (на 768px подпись не вмещалась в 42 символа).
  const isCompactAxis = device !== 'desktop';
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
              height: isCompactAxis
                ? Math.max(420, data.by_stage.length * 62)
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
                <XAxis
                  type="number"
                  allowDecimals={false}
                  tick={AXIS_TICK_SMALL}
                  stroke="var(--atmr-border-default)"
                />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={isCompactAxis ? 128 : 240}
                  tick={
                    isCompactAxis ? (
                      <StageTick lines={4} perLine={18} />
                    ) : (
                      <StageTick lines={2} perLine={28} />
                    )
                  }
                  stroke="var(--atmr-border-default)"
                  interval={0}
                />
                <Tooltip
                  contentStyle={TOOLTIP_STYLE}
                  labelFormatter={(label) => String(label)}
                  formatter={(value) => [
                    Number(value ?? 0),
                    'Взаимодействий',
                  ]}
                />
                <Bar
                  dataKey="count"
                  fill="var(--atmr-accent-default)"
                  radius={[0, 6, 6, 0]}
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
                    contentStyle={TOOLTIP_STYLE}
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
                      // Recharts красит подпись легенды в цвет сектора; на
                      // светлой теме акценты дают 2-4:1. Возвращаем span с
                      // обычным цветом текста.
                      return (
                        <span style={{ color: 'var(--atmr-fg-default)' }}>
                          {value} — {pct}%
                        </span>
                      );
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
                    tick={{ ...AXIS_TICK, fontSize: isMobile ? 10 : 11 }}
                    stroke="var(--atmr-border-default)"
                    tickFormatter={(v) => v?.slice(5) || ''}
                    minTickGap={24}
                  />
                  <YAxis
                    tick={{ ...AXIS_TICK, fontSize: 11 }}
                    stroke="var(--atmr-border-default)"
                    allowDecimals={false}
                  />
                  <Tooltip
                    labelFormatter={(value) => `Дата: ${value}`}
                    contentStyle={TOOLTIP_STYLE}
                  />
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
