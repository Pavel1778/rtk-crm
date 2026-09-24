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
  Segmented,
  Select,
  Space,
  Switch,
  Table,
  Tabs,
  Tag,
  Typography,
} from 'antd';
import { useEffect, useState } from 'react';

import { errorMessage } from '../api/client';
import {
  createStage,
  createUser,
  deleteUser,
  listStages,
  listUsers,
  updateStage,
  updateUser,
} from '../api/endpoints';
import type { User, UserRole, WorkflowScope, WorkflowStage } from '../types';
import { useAuthStore, useRole } from '../stores/authStore';

import StageTable from '../components/workflow/StageTable';
import DeleteStageModal from '../components/workflow/DeleteStageModal';
import { useDeleteStage } from '../hooks/useStages';

const ROLE_LABELS: Record<UserRole, string> = {
  admin: 'Администратор',
  manager: 'Руководитель',
  user: 'КАМ',
};

/**
 * Настройки администратора: управление пользователями и этапами воркфлоу.
 * Каждая вкладка доступна только администратору.
 */
export default function SettingsPage() {
  const role = useRole();

  if (role !== 'admin') {
    return (
      <Card>
        <p>Доступ запрещён. Только администраторы могут управлять настройками.</p>
      </Card>
    );
  }

  return (
    <Tabs
      items={[
        { key: 'users', label: 'Пользователи', children: <UsersPanel /> },
        { key: 'workflow', label: 'Этапы воркфлоу', children: <WorkflowPanel /> },
      ]}
    />
  );
}

function UsersPanel() {
  const { message } = AntApp.useApp();
  const currentUser = useAuthStore((s) => s.user);
  const screens = Grid.useBreakpoint();
  const isMobile = !screens.md;
  const [users, setUsers] = useState<User[]>([]);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();

  const load = () => {
    listUsers()
      .then(setUsers)
      .catch((e) => message.error(errorMessage(e)));
  };
  useEffect(load, []);

  const addUser = async () => {
    const values = await form.validateFields();
    setSaving(true);
    try {
      await createUser({
        email: values.email,
        full_name: values.full_name,
        password: values.password,
        role: values.role,
        is_admin: values.role === 'admin',
      });
      form.resetFields();
      message.success('Пользователь добавлен');
      load();
    } catch (e) {
      message.error(errorMessage(e, 'Не удалось добавить пользователя'));
    } finally {
      setSaving(false);
    }
  };

  const patch = async (id: number, payload: Record<string, unknown>, text: string) => {
    try {
      await updateUser(id, payload);
      message.success(text);
      load();
    } catch (e) {
      message.error(errorMessage(e, 'Не удалось сохранить'));
    }
  };

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Card title="Новый пользователь" style={{ border: '1px solid var(--atmr-border-soft)' }}>
        <Form form={form} layout={isMobile ? 'vertical' : 'inline'} className="responsive-form">
          <Form.Item
            name="full_name"
            rules={[{ required: true, message: 'Укажите имя' }]}
          >
            <Input
              id="settings-user-name"
              name="full_name"
              placeholder="ФИО"
              style={{ width: isMobile ? '100%' : 200 }}
              autoComplete="off"
            />
          </Form.Item>
          <Form.Item
            name="email"
            rules={[
              { required: true, message: 'Укажите email' },
              { type: 'email', message: 'Некорректный email' },
            ]}
          >
            <Input
              id="settings-user-email"
              name="email"
              placeholder="email@example.com"
              style={{ width: isMobile ? '100%' : 220 }}
              autoComplete="off"
            />
          </Form.Item>
          <Form.Item
            name="password"
            rules={[
              { required: true, message: 'Укажите пароль' },
              { min: 6, message: 'Минимум 6 символов' },
            ]}
          >
            <Input.Password
              id="settings-user-password"
              name="password"
              placeholder="Пароль"
              style={{ width: isMobile ? '100%' : 180 }}
              autoComplete="new-password"
            />
          </Form.Item>
          <Form.Item name="role" initialValue="user">
            <Select
              id="settings-user-role"
              style={{ width: isMobile ? '100%' : 160 }}
              options={[
                { value: 'user', label: ROLE_LABELS.user },
                { value: 'manager', label: ROLE_LABELS.manager },
                { value: 'admin', label: ROLE_LABELS.admin },
              ]}
            />
          </Form.Item>
          <Form.Item>
            <Button type="primary" onClick={addUser} loading={saving} block={isMobile}>
              Добавить
            </Button>
          </Form.Item>
        </Form>
      </Card>

      <Card title="Сотрудники" style={{ border: '1px solid var(--atmr-border-soft)' }}>
        <Table<User>
          rowKey="id"
          size="small"
          dataSource={users}
          pagination={false}
          scroll={{ x: 640 }}
          locale={{ emptyText: 'Пользователей нет' }}
          columns={[
            {
              title: 'ФИО',
              dataIndex: 'full_name',
              render: (name: string) => <Typography.Text strong>{name}</Typography.Text>,
            },
            { title: 'Email', dataIndex: 'email' },
            {
              title: 'Роль',
              dataIndex: 'role',
              render: (role: UserRole, record) => (
                <Select
                  size="small"
                  value={role}
                  style={{ width: 150 }}
                  disabled={record.id === currentUser?.id}
                  onChange={(next) =>
                    patch(
                      record.id,
                      { role: next, is_admin: next === 'admin' },
                      'Роль обновлена',
                    )
                  }
                  options={[
                    { value: 'user', label: ROLE_LABELS.user },
                    { value: 'manager', label: ROLE_LABELS.manager },
                    { value: 'admin', label: ROLE_LABELS.admin },
                  ]}
                />
              ),
            },
            {
              title: 'Активен',
              dataIndex: 'is_active',
              render: (active: boolean, record) => (
                <Switch
                  checked={active}
                  disabled={record.id === currentUser?.id}
                  onChange={(next) =>
                    patch(record.id, { is_active: next }, 'Статус обновлён')
                  }
                />
              ),
            },
            {
              title: 'Действия',
              key: 'actions',
              render: (_, record) => {
                if (record.id === currentUser?.id) {
                  return <Tag>Это вы</Tag>;
                }
                return (
                  <Popconfirm
                    title="Удалить пользователя?"
                    okText="Удалить"
                    cancelText="Отмена"
                    onConfirm={() =>
                      deleteUser(record.id)
                        .then(() => {
                          message.success('Пользователь удалён');
                          load();
                        })
                        .catch((e) => message.error(errorMessage(e)))
                    }
                  >
                    <Button danger size="small">
                      Удалить
                    </Button>
                  </Popconfirm>
                );
              },
            },
          ]}
        />
      </Card>
    </Space>
  );
}

function WorkflowPanel() {
  const { message } = AntApp.useApp();
  const screens = Grid.useBreakpoint();
  const isMobile = !screens.md;
  const [stages, setStages] = useState<WorkflowStage[]>([]);
  const [saving, setSaving] = useState(false);
  const [togglingStageId, setTogglingStageId] = useState<number | null>(null);
  const [deletingStage, setDeletingStage] = useState<WorkflowStage | undefined>();
  const [funnel, setFunnel] = useState<WorkflowScope>('b2b');
  const [form] = Form.useForm();
  const deleteStageMutation = useDeleteStage();

  const load = () => {
    listStages(true)
      .then(setStages)
      .catch((e) => message.error(errorMessage(e)));
  };
  useEffect(load, []);

  const funnelStages = stages.filter((stage) => stage.scope === funnel);

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
        scope: funnel,
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
        <Card title="Воронка" style={{ border: '1px solid var(--atmr-border-soft)' }}>
          <Segmented
            id="settings-funnel"
            value={funnel}
            onChange={(value) => {
              setFunnel(value as WorkflowScope);
              form.resetFields();
            }}
            options={[
              { value: 'b2b', label: 'B2B' },
              { value: 'b2c', label: 'B2C' },
            ]}
          />
          <Typography.Text type="secondary" style={{ display: 'block', marginTop: 8 }}>
            Этапы, добавленные ниже, попадут в выбранную воронку.
          </Typography.Text>
        </Card>
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
          stages={funnelStages}
          onToggle={(stage, next) => toggleStage(stage.id, next)}
          togglingId={togglingStageId}
          onDelete={setDeletingStage}
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

      <DeleteStageModal
        open={Boolean(deletingStage)}
        stageId={deletingStage?.id ?? null}
        onCancel={() => setDeletingStage(undefined)}
        onConfirm={async (targetStageId) => {
          if (!deletingStage) return;
          try {
            await deleteStageMutation.mutateAsync({
              id: deletingStage.id,
              targetStageId,
            });
            setDeletingStage(undefined);
            load();
          } catch {
            // сообщение об ошибке показывает мутация
          }
        }}
        confirmLoading={deleteStageMutation.isPending}
      />
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
