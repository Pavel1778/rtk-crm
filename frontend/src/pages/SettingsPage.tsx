import {
  App as AntApp,
  Button,
  Card,
  ColorPicker,
  Form,
  Grid,
  Input,
  InputNumber,
  Popconfirm,
  Space,
  Switch,
  Table,
  Tag,
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
      <Card title="Новый этап" style={{ border: '1px solid #EEEEF2' }}>
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

      <Card title="Этапы воркфлоу" style={{ border: '1px solid #EEEEF2' }}>
        <div className="scroll-box">
          <Table<WorkflowStage>
            rowKey="id"
            dataSource={stages}
            pagination={false}
            size="small"
            scroll={{ x: 'max-content' }}
            columns={[
              { title: 'Порядок', dataIndex: 'order', width: 80 },
              {
                title: 'Этап',
                dataIndex: 'name',
                render: (name: string, record) => (
                  <Space>
                    <span
                      style={{
                        width: 10,
                        height: 10,
                        borderRadius: 5,
                        background: record.color ?? '#6E41F2',
                        display: 'inline-block',
                      }}
                    />
                    <EditableText
                      value={name}
                      onSave={(value) =>
                        updateStage(record.id, { name: value })
                          .then(() => message.success('Название обновлено'))
                          .then(load)
                          .catch((e) => message.error(errorMessage(e)))
                      }
                    />
                  </Space>
                ),
              },
              {
                title: 'Код',
                dataIndex: 'code',
                width: 150,
                render: (code: string) => <Tag>{code}</Tag>,
              },
              {
                title: 'Взаимодействий',
                dataIndex: 'interaction_count',
                width: 120,
              },
              {
                title: 'Активен',
                dataIndex: 'is_active',
                width: 100,
                render: (active: boolean, record) => (
                  <Switch
                    checked={active}
                    loading={togglingStageId === record.id}
                    onChange={(checked) => toggleStage(record.id, checked)}
                  />
                ),
              },
              {
                title: '',
                width: 80,
                render: (_, record) => (
                  <Popconfirm
                    title="Удалить этап?"
                    disabled={record.interaction_count > 0}
                    onConfirm={() =>
                      deleteStage(record.id)
                        .then(load)
                        .catch((e) => message.error(errorMessage(e)))
                    }
                  >
                    <Button
                      type="text"
                      size="small"
                      danger
                      disabled={record.interaction_count > 0}
                    >
                      Удалить
                    </Button>
                  </Popconfirm>
                ),
              },
            ]}
          />
        </div>
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
