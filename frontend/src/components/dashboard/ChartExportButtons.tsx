import { App as AntApp, Button, Space, Tooltip } from 'antd';
import { FileImageOutlined, FilePdfOutlined } from '@ant-design/icons';
import { useState } from 'react';

import { exportNodeAsPdf, exportNodeAsPng } from '../../utils/chartExport';

interface ChartExportButtonsProps {
  /** Узел диаграммы; null, если диаграмма ещё не отрисована. */
  target: () => HTMLElement | null;
  filename: string;
  title?: string;
}

/** Кнопки «Экспорт PNG»/«Экспорт PDF» для интерактивной диаграммы. */
export default function ChartExportButtons({
  target,
  filename,
  title,
}: ChartExportButtonsProps) {
  const { message } = AntApp.useApp();
  const [busy, setBusy] = useState<'png' | 'pdf' | null>(null);

  const run = async (format: 'png' | 'pdf') => {
    const node = target();
    if (!node) {
      message.warning('Диаграмма недоступна для экспорта');
      return;
    }
    setBusy(format);
    try {
      if (format === 'png') {
        await exportNodeAsPng(node, filename);
      } else {
        await exportNodeAsPdf(node, filename, title);
      }
      message.success(`Диаграмма сохранена в ${format.toUpperCase()}`);
    } catch (error) {
      message.error(
        error instanceof Error ? error.message : 'Не удалось экспортировать диаграмму'
      );
    } finally {
      setBusy(null);
    }
  };

  return (
    <Space size={4}>
      <Tooltip title="Экспорт PNG">
        <Button
          type="text"
          size="small"
          aria-label={`Экспорт ${filename} в PNG`}
          icon={<FileImageOutlined />}
          loading={busy === 'png'}
          onClick={() => void run('png')}
        />
      </Tooltip>
      <Tooltip title="Экспорт PDF">
        <Button
          type="text"
          size="small"
          aria-label={`Экспорт ${filename} в PDF`}
          icon={<FilePdfOutlined />}
          loading={busy === 'pdf'}
          onClick={() => void run('pdf')}
        />
      </Tooltip>
    </Space>
  );
}
