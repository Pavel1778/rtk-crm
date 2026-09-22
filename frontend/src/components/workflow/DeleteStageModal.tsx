import { Alert, App as AntApp, Modal, Select, Space, Spin, Typography } from 'antd';
import { useEffect, useState } from 'react';

import { useStageImpact } from '../../hooks/useStages';

interface DeleteStageModalProps {
  open: boolean;
  stageId: number | null;
  onCancel: () => void;
  onConfirm: (targetStageId?: number) => void;
  confirmLoading?: boolean;
}

export default function DeleteStageModal({
  open,
  stageId,
  onCancel,
  onConfirm,
  confirmLoading,
}: DeleteStageModalProps) {
  const { message } = AntApp.useApp();
  const [targetStageId, setTargetStageId] = useState<number | undefined>();
  const { data: impact, isLoading } = useStageImpact(open ? stageId : null);

  useEffect(() => {
    if (!open) {
      setTargetStageId(undefined);
    }
  }, [open]);

  const needsTransfer = (impact?.total_count ?? 0) > 0;

  const handleConfirm = () => {
    if (needsTransfer && !targetStageId) {
      message.error('Выберите этап для переноса');
      return;
    }
    onConfirm(targetStageId);
  };

  return (
    <Modal
      title={impact ? `Удалить этап «${impact.name}»` : 'Удалить этап'}
      open={open}
      onCancel={onCancel}
      onOk={handleConfirm}
      okText="Удалить"
      cancelText="Отмена"
      okButtonProps={{ danger: true }}
      confirmLoading={confirmLoading}
    >
      {isLoading || !impact ? (
        <Spin />
      ) : (
        <Space direction="vertical" size={16} style={{ width: '100%' }}>
          <Typography.Text>
            Взаимодействий на этапе: {impact.total_count} (активных{' '}
            {impact.active_count}).
          </Typography.Text>
          {needsTransfer ? (
            <>
              <Alert
                type="warning"
                showIcon
                message="Все взаимодействия будут перенесены на выбранный этап."
              />
              <Select
                placeholder="Выберите этап для переноса"
                style={{ width: '100%' }}
                value={targetStageId}
                onChange={setTargetStageId}
                options={impact.transfer_options.map((s) => ({
                  value: s.id,
                  label: s.name,
                }))}
              />
            </>
          ) : (
            <Typography.Text type="secondary">
              Этап пуст — перенос не требуется.
            </Typography.Text>
          )}
        </Space>
      )}
    </Modal>
  );
}
