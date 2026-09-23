import { useQuery } from '@tanstack/react-query';
import { Card, Empty, Skeleton, Table, Tooltip } from 'antd';

import { getReportColumns } from '../../api/endpoints';
import { useDevice } from '../../hooks/useDevice';
import type { ReportColumn, ReportTableRow } from '../../types';

interface ReportTableProps {
  rows: ReportTableRow[];
  loading?: boolean;
  title?: string;
}

/** Значения длиннее 40 символов обрезаем: полный текст — в подсказке. */
const TRUNCATE_AT = 40;

function renderCell(value: string | number | null | undefined) {
  const text = value === null || value === undefined || value === '' ? '—' : String(value);
  if (text.length <= TRUNCATE_AT) return text;
  return (
    <Tooltip title={text}>
      <span className="report-table__truncate">{text}</span>
    </Tooltip>
  );
}

/**
 * Предпросмотр таблицы отчёта. Колонки берутся из общего конфига
 * (config/report_columns.json через /api/reports/columns), поэтому состав
 * и порядок колонок совпадают с выгрузками PDF/XLSX/XLS.
 */
export default function ReportTable({ rows, loading, title = 'Предпросмотр отчёта' }: ReportTableProps) {
  const device = useDevice();
  const isMobile = device === 'mobile';

  const columnsQuery = useQuery<ReportColumn[]>({
    queryKey: ['report-columns'],
    queryFn: getReportColumns,
    staleTime: Infinity,
  });

  const columns = columnsQuery.data ?? [];

  const antColumns = columns.map((column) => ({
    title: isMobile ? column.short_label : column.label,
    dataIndex: column.key,
    key: column.key,
    width: column.width * 8,
    align: column.align as 'left' | 'center',
    render: renderCell,
  }));

  if (loading || columnsQuery.isLoading) {
    return (
      <Card title={title}>
        <Skeleton active paragraph={{ rows: 4 }} />
      </Card>
    );
  }

  if (columns.length === 0) {
    return (
      <Card title={title}>
        <Empty description="Колонки отчёта не настроены" />
      </Card>
    );
  }

  return (
    <Card title={title}>
      <div className="scroll-box">
        <Table<ReportTableRow>
          rowKey="id"
          size="small"
          dataSource={rows}
          columns={antColumns}
          pagination={rows.length > 20 ? { pageSize: 20 } : false}
          scroll={{ x: 'max-content' }}
          locale={{ emptyText: 'Нет данных за выбранный период' }}
        />
      </div>
    </Card>
  );
}
