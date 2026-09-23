import { App as AntApp, Card, Select, Space, Table, Tag, Typography } from 'antd';
import { useEffect, useState } from 'react';

import { errorMessage } from '../api/client';
import { listAuditEntityTypes, listAuditLogs } from '../api/endpoints';
import type { AuditLogEntry } from '../types';
import { useRole } from '../stores/authStore';

const ACTION_LABELS: Record<string, string> = {
  CREATE: 'Создание',
  UPDATE: 'Изменение',
  DELETE: 'Удаление',
};

const ACTION_COLORS: Record<string, string> = {
  CREATE: 'green',
  UPDATE: 'blue',
  DELETE: 'red',
};

const ENTITY_LABELS: Record<string, string> = {
  Interaction: 'Взаимодействие',
  University: 'Вуз',
  ITProduct: 'Продукт',
  ITDirection: 'Направление',
  WorkflowStageRef: 'Этап',
  Comment: 'Комментарий',
  Action: 'Задача',
  AttachedFile: 'Файл',
  User: 'Пользователь',
};

const PAGE_SIZE = 50;

/**
 * Журнал аудита действий для 152-ФЗ: кто, что и когда менял.
 * Доступен только администратору.
 */
export default function AuditLogPage() {
  const { message } = AntApp.useApp();
  const role = useRole();
  const [items, setItems] = useState<AuditLogEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [action, setAction] = useState<string | undefined>();
  const [entityType, setEntityType] = useState<string | undefined>();
  const [entityTypes, setEntityTypes] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (role === 'admin') {
      void listAuditEntityTypes().then(setEntityTypes).catch(() => undefined);
    }
  }, [role]);

  useEffect(() => {
    if (role !== 'admin') return;
    setLoading(true);
    listAuditLogs({
      action,
      entity_type: entityType,
      limit: PAGE_SIZE,
      offset: (page - 1) * PAGE_SIZE,
    })
      .then((data) => {
        setItems(data.items);
        setTotal(data.total);
      })
      .catch((e) => message.error(errorMessage(e, 'Не удалось загрузить журнал')))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [action, entityType, page, role]);

  if (role !== 'admin') {
    return (
      <Card>
        <p>Доступ запрещён. Журнал аудита доступен только администраторам.</p>
      </Card>
    );
  }

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Typography.Title level={4} style={{ margin: 0 }}>
        Журнал действий
      </Typography.Title>
      <Card style={{ border: '1px solid var(--atmr-border-soft)' }}>
        <Space wrap style={{ marginBottom: 16 }}>
          <Select
            allowClear
            placeholder="Действие"
            style={{ width: 180 }}
            value={action}
            onChange={(value) => {
              setAction(value);
              setPage(1);
            }}
            options={[
              { value: 'CREATE', label: ACTION_LABELS.CREATE },
              { value: 'UPDATE', label: ACTION_LABELS.UPDATE },
              { value: 'DELETE', label: ACTION_LABELS.DELETE },
            ]}
          />
          <Select
            allowClear
            placeholder="Сущность"
            style={{ width: 220 }}
            value={entityType}
            onChange={(value) => {
              setEntityType(value);
              setPage(1);
            }}
            options={entityTypes.map((value) => ({
              value,
              label: ENTITY_LABELS[value] ?? value,
            }))}
          />
        </Space>
        <Table<AuditLogEntry>
          rowKey="id"
          size="small"
          loading={loading}
          dataSource={items}
          scroll={{ x: 760 }}
          locale={{ emptyText: 'Записей нет' }}
          pagination={{
            current: page,
            pageSize: PAGE_SIZE,
            total,
            showSizeChanger: false,
            onChange: setPage,
          }}
          columns={[
            {
              title: 'Время',
              dataIndex: 'created_at',
              render: (value: string) => new Date(value).toLocaleString('ru-RU'),
            },
            {
              title: 'Сотрудник',
              dataIndex: 'user_name',
              render: (name: string | null) => name ?? '—',
            },
            {
              title: 'Действие',
              dataIndex: 'action',
              render: (value: string) => (
                <Tag color={ACTION_COLORS[value] ?? 'default'}>
                  {ACTION_LABELS[value] ?? value}
                </Tag>
              ),
            },
            {
              title: 'Сущность',
              dataIndex: 'entity_type',
              render: (value: string, record) =>
                `${ENTITY_LABELS[value] ?? value} #${record.entity_id}`,
            },
            { title: 'IP', dataIndex: 'ip_address', render: (v: string | null) => v ?? '—' },
          ]}
        />
      </Card>
    </Space>
  );
}
