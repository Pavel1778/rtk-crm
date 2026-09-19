import {
  App as AntApp,
  Button,
  Card,
  ColorPicker,
  Form,
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

/**
 * Настройка воркфлоу: этапы можно добавлять, переименовывать,
 * менять цвет колонки и порядок. Удаление доступно, если на этапе
 * нет взаимодействий.
 */
export default function SettingsPage() {
  const { message } = AntApp.useApp();
  const [stages, setStages] = useState<WorkflowStage[]>([]);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();

  const load = () => {
    listStages()
      .then(setStages)
      .catch((e) => message.error(errorMessage(e)));
  };
  useEffect(load, []);

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
        <Form form={form} layout="inline">
          <Form.Item
            name="code"
            rules={[{ required: true, message: 'Код обязателен' }]}
          >
            <Input placeholder="Код (например, pilot)" style={{ width: 160 }} />
          </Form.Item>
          <Form.Item
            name="name"
            rules={[{ required: true, message: 'Название обязательно' }]}
          >
            <Input placeholder="Название этапа" style={{ width: 200 }} />
          </Form.Item>
          <Form.Item
            name="order"
            rules={[{ required: true, message: 'Порядок обязателен' }]}
          >
            <InputNumber placeholder="Порядок" min={1} style={{ width: 100 }} />
          </Form.Item>
          <Form.Item name="color" initialValue="#6E41F2">
            <ColorPicker showText format="hex" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" onClick={addStage} loading={saving}>
              Добавить
            </Button>
          </Form.Item>
        </Form>
      </Card>

      <Card title="Этапы воркфлоу" style={{ border: '1px solid #EEEEF2' }}>
        <Table<WorkflowStage>
          rowKey="id"
          dataSource={stages}
          pagination={false}
          size="small"
          columns={[
            { title: 'Порядок', dataIndex: 'order', width: 90 },
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
              width: 180,
              render: (code: string) => <Tag>{code}</Tag>,
            },
            {
              title: 'Взаимодействий',
              dataIndex: 'interaction_count',
              width: 140,
            },
            {
              title: 'Активен',
              dataIndex: 'is_active',
              width: 100,
              render: (active: boolean, record) => (
                <Switch
                  checked={active}
                  onChange={(checked) =>
                    updateStage(record.id, { is_active: checked })
                      .then(load)
                      .catch((e) => message.error(errorMessage(e)))
                  }
                />
              ),
            },
            {
              title: '',
              width: 90,
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
