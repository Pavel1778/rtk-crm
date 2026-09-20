import { App as AntApp, Modal, Select, Space } from 'antd';
import { useState } from 'react';

interface DeleteStageModalProps {
  open: boolean;
  onCancel: () => void;
  onConfirm: (targetStageId: number) => void;
  stages: Array<{ id: number; name: string }>;
}

export default function DeleteStageModal({ open, onCancel, onConfirm, stages }: DeleteStageModalProps) {
  const { message } = AntApp.useApp();
  const [targetStageId, setTargetStageId] = useState<number | undefined>();

  const handleConfirm = () => {
    if (!targetStageId) {
      message.error('Выберите этап для переноса');
      return;
    }
    onConfirm(targetStageId);
    setTargetStageId(undefined);
  };

  return (
    <Modal
      title="Удалить этап"
      open={open}
      onCancel={onCancel}
      onOk={handleConfirm}
      okText="Удалить"
      cancelText="Отмена"
      okButtonProps={{ danger: true }}
    >
      <Space direction="vertical" size={16} style={{ width: '100%' }}>
        <p>Взаимодействия на этом этапе будут перенесены на выбранный этап.</p>
        <Select
          placeholder="Выберите этап для переноса"
          style={{ width: '100%' }}
          value={targetStageId}
          onChange={setTargetStageId}
          options={stages.map((s) => ({ value: s.id, label: s.name }))}
        />
      </Space>
    </Modal>
  );
}
