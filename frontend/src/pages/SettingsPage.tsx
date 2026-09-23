import {
  App as AntApp,
  Button,
  Card,
  ColorPicker,
  Form,
  Grid,
  Input,
  InputNumber,
  Space,
} from 'antd';
import { useEffect, useState } from 'react';

import { errorMessage } from '../api/client';
import {
  createStage,
  deleteStage,
  listStages,
  updateStage,
} from '../api/endpoints';
import type { WorkflowStage } from '../types';
import { useRole } from '../stores/authStore';

import StageTable from '../components/workflow/StageTable';

/**
 * Настройка воркфлоу: этапы можно добавлять, переименовывать,
 * менять цвет колонки и порядок. Удаление доступно, если на этапе
 * нет взаимодействий. Только для admin.
 */
export default function SettingsPage() {
  const { message } = AntApp.useApp();
  const role = useRole();
  const screens = Grid.useBreakpoint();
  const isMobile = !screens.md;
  const [stages, setStages] = useState<WorkflowStage[]>([]);
  const [saving, setSaving] = useState(false);
  const [togglingStageId, setTogglingStageId] = useState<number | null>(null);
  const [form] = Form.useForm();

  if (role !== 'admin') {
    return (
      <Card>
        <p>Доступ запрещён. Только администраторы могут редактировать этапы воркфлоу.</p>
      </Card>
    );
  }

  const load = () => {
    listStages(true)
      .then(setStages)
      .catch((e) => message.error(errorMessage(e)));
  };
  useEffect(load, []);

  const toggleStage = async (id: number, checked: boolean) => {
    setTogglingStageId(id);
    try {
      await updateStage(id, { is_active: checked });
      message.success('Этап обновлён');
      load();
    } catch (e) {
      message.error(errorMessage(e));
    } finally {
      setTogglingStageId(null);
    }
  };

  const addStage = async () => {
    const values = await form.validateFields();
    setSaving(true);
    try {
      const color =
        typeof values.color === 'string' ? values.color : values.color?.toHexString?.();
      await createStage({
        code: values.code,
        name: values.name,
        order: values.order,
        color: color ?? null,
      });
      form.resetFields();
      message.success('Этап добавлен');
      load();
    } catch (e) {
      if (e instanceof Error) message.error(errorMessage(e));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
        <Card title="Новый этап" style={{ border: '1px solid var(--atmr-border-soft)' }}>
        <Form form={form} layout={isMobile ? 'vertical' : 'inline'} className="responsive-form">
          <Form.Item
            name="code"
            rules={[{ required: true, message: 'Код обязателен' }]}
          >
            <Input 
              id="settings-stage-code"
              name="code"
              placeholder="Код (например, pilot)" 
              style={{ width: isMobile ? '100%' : 160 }}
              autoComplete="off"
            />
          </Form.Item>
          <Form.Item
            name="name"
            rules={[{ required: true, message: 'Название обязательно' }]}
          >
            <Input 
              id="settings-stage-name"
              name="name"
              placeholder="Название этапа" 
              style={{ width: isMobile ? '100%' : 200 }}
              autoComplete="off"
            />
          </Form.Item>
          <Form.Item
            name="order"
            rules={[{ required: true, message: 'Порядок обязателен' }]}
          >
            <InputNumber 
              id="settings-stage-order"
              name="order"
              placeholder="Порядок" 
              min={1} 
              style={{ width: isMobile ? '100%' : 100 }}
              autoComplete="off"
            />
          </Form.Item>
          <Form.Item name="color" initialValue="#6E41F2">
            <ColorPicker showText format="hex" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" onClick={addStage} loading={saving} block={isMobile}>
              Добавить
            </Button>
          </Form.Item>
        </Form>
      </Card>

      <Card title="Этапы воркфлоу" style={{ border: '1px solid var(--atmr-border-soft)' }}>
        <StageTable
          stages={stages}
          onToggle={(stage, next) => toggleStage(stage.id, next)}
          togglingId={togglingStageId}
          onDelete={(stage) => {
            void deleteStage(stage.id)
              .then(load)
              .catch((e) => message.error(errorMessage(e)));
          }}
          renderName={(stage) => (
            <EditableText
              value={stage.name}
              onSave={(value) =>
                updateStage(stage.id, { name: value })
                  .then(() => message.success('Название обновлено'))
                  .then(load)
                  .catch((e) => message.error(errorMessage(e)))
              }
            />
          )}
        />
      </Card>
    </Space>
  );
}

function EditableText({
  value,
  onSave,
}: {
  value: string;
  onSave: (value: string) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);

  useEffect(() => setDraft(value), [value]);

  if (!editing) {
    return (
      <Button type="text" size="small" onClick={() => setEditing(true)}>
        {value}
      </Button>
    );
  }
  return (
    <Space.Compact size="small">
      <Input
        size="small"
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        style={{ width: 180 }}
        onPressEnter={() => {
          onSave(draft);
          setEditing(false);
        }}
      />
      <Button
        size="small"
        type="primary"
        onClick={() => {
          onSave(draft);
          setEditing(false);
        }}
      >
        ОК
      </Button>
    </Space.Compact>
  );
}
