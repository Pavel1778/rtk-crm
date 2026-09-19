import { BarChartOutlined, DownloadOutlined } from '@ant-design/icons';
import { Button, Card, Col, Empty, Progress, Row, Space, Spin, Statistic, Typography } from 'antd';
import { useEffect, useState } from 'react';
import { saveAs } from 'file-saver';

import { errorMessage } from '../api/client';
import { exportPdf, exportXls, exportXlsx, getReport } from '../api/endpoints';
import type { ReportResponse } from '../types';

/**
 * Отчёт: ключевые показатели и распределение взаимодействий по этапам.
 * Горизонтальные полосы вместо графика — без лишних зависимостей.
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
        <Space direction="vertical" size={12} style={{ width: '100%' }}>
          {data.stage_progress.map((stage) => (
            <div key={stage.stage_code}>
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  marginBottom: 4,
                }}
              >
                <Typography.Text>{stage.stage_name}</Typography.Text>
                <Typography.Text type="secondary">
                  {stage.count} ({stage.percent}%)
                </Typography.Text>
              </div>
              <Progress
                percent={stage.percent}
                showInfo={false}
                strokeColor="#6E41F2"
                trailColor="#EEEEF2"
              />
            </div>
          ))}
        </Space>
      </Card>
    </Space>
  );
}
