import {
  App as AntApp,
  Button,
  DatePicker,
  Drawer,
  Empty,
  Form,
  Grid,
  Input,
  Select,
  Space,
  Spin,
  Table,
  Tabs,
  Timeline,
  Typography,
  Upload,
} from 'antd';
import {
  DeleteOutlined,
  DownloadOutlined,
  FileOutlined,
  InboxOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { isAxiosError } from 'axios';
import { useEffect, useState } from 'react';
import { saveAs } from 'file-saver';

import { errorMessage } from '../../api/client';
import { downloadFile, summarizeInteraction } from '../../api/endpoints';
import type {
  ActionItem,
  InteractionCard,
  InteractionSummary,
} from '../../types';
import { useAuthStore } from '../../stores/authStore';
import {
  useActions,
  useComments,
  useCreateAction,
  useCreateComment,
  useDeleteAction,
  useDeleteComment,
  useDeleteFile,
  useFiles,
  useInteraction,
  useStageOptions,
  useToggleAction,
  useUpdateInteraction,
  useUploadFile,
  useUserOptions,
} from '../../hooks/useInteraction';

interface DrawerProps {
  card: InteractionCard | null;
  onClose: () => void;
}

export default function InteractionDrawer({ card, onClose }: DrawerProps) {
  const { message, modal } = AntApp.useApp();
  const user = useAuthStore((s) => s.user);
  const screens = Grid.useBreakpoint();
  const isMobile = !screens.md;

  const interactionId = card?.id ?? null;
  const canAssign = user?.role === 'admin' || user?.role === 'manager';

  // Данные читаются из общего кэша: правка в карточке обновляет и доску,
  // и наоборот — отдельные load() больше не нужны.
  const interactionQuery = useInteraction(interactionId);
  const actionsQuery = useActions(interactionId);
  const commentsQuery = useComments(interactionId);
  const filesQuery = useFiles(interactionId);
  const stagesQuery = useStageOptions();
  const usersQuery = useUserOptions(!!canAssign);

  const full = interactionQuery.data ?? null;
  const actions = actionsQuery.data ?? [];
  const comments = commentsQuery.data ?? [];
  const files = filesQuery.data ?? [];
  const stages = stagesQuery.data ?? [];
  const users = usersQuery.data ?? [];
  const loading = interactionQuery.isLoading;

  const updateMutation = useUpdateInteraction();
  const createActionMutation = useCreateAction(interactionId);
  const createCommentMutation = useCreateComment(interactionId, user?.full_name ?? null);
  const toggleActionMutation = useToggleAction(interactionId);
  const deleteActionMutation = useDeleteAction(interactionId);
  const deleteCommentMutation = useDeleteComment(interactionId);
  const uploadMutation = useUploadFile(interactionId);
  const deleteFileMutation = useDeleteFile(interactionId);

  const [uploading, setUploading] = useState(false);
  const [commentText, setCommentText] = useState('');
  const [actionForm] = Form.useForm();
  const [summary, setSummary] = useState<InteractionSummary | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(false);
  // Функция выключена, если backend не настроен на GigaChat (ответ 503).
  const [summaryDisabled, setSummaryDisabled] = useState(false);

  const requestSummary = async () => {
    if (!card) return;
    setSummaryLoading(true);
    try {
      setSummary(await summarizeInteraction(card.id));
    } catch (error) {
      // 503 означает, что ключ GigaChat не задан: это не ошибка пользователя,
      // поэтому вкладка просто объясняет, что функция недоступна.
      if (isAxiosError(error) && error.response?.status === 503) {
        setSummaryDisabled(true);
      } else {
        message.error(errorMessage(error, 'Не удалось получить сводку'));
      }
    } finally {
      setSummaryLoading(false);
    }
  };

  useEffect(() => {
    // Сводка относится к конкретной карточке: при переключении сбрасываем,
    // чтобы не показать текст предыдущего взаимодействия.
    setSummary(null);
    setSummaryDisabled(false);
    setCommentText('');
  }, [interactionId]);

  useEffect(() => {
    if (interactionQuery.isError) {
      message.error(errorMessage(interactionQuery.error, 'Не удалось загрузить карточку'));
    }
  }, [interactionQuery.isError, interactionQuery.error, message]);

  const save = async (payload: Record<string, unknown>, successText: string) => {
    if (!card) return;
    try {
      await updateMutation.mutateAsync({ id: card.id, payload, successText });
    } catch {
      // Сообщение об ошибке и откат значения — в хуке мутации.
    }
  };

  const submitAction = async () => {
    if (!card) return;
    try {
      const values = await actionForm.validateFields();
      await createActionMutation.mutateAsync({
        title: values.title,
        description: values.description || undefined,
        due_date: values.due_date ? values.due_date.format('YYYY-MM-DD') : undefined,
      });
      actionForm.resetFields();
    } catch (error) {
      if (error instanceof Error) {
        message.error(errorMessage(error, 'Не удалось добавить задачу'));
      }
    }
  };

  const submitComment = async () => {
    if (!card || !commentText.trim()) return;
    const text = commentText.trim();
    setCommentText('');
    try {
      await createCommentMutation.mutateAsync(text);
    } catch {
      // Текст остался в поле ввода? Возвращаем, чтобы пользователь не потерял
      // набранное при откате оптимистичного комментария.
      setCommentText((current) => (current === '' ? text : current));
    }
  };

  const handleUpload = async (file: File) => {
    if (!card) return;

    // Валидация MIME-типов
    const allowedTypes = [
      'image/png',
      'image/jpeg',
      'application/pdf',
      'application/zip',
      'application/gzip',
      'application/x-rar-compressed',
      'application/msword',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'application/vnd.ms-excel',
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    ];

    if (!allowedTypes.includes(file.type)) {
      message.error('Недопустимый тип файла');
      return Upload.LIST_IGNORE;
    }

    // Валидация размера (50 МБ)
    const maxSize = 50 * 1024 * 1024;
    if (file.size > maxSize) {
      message.error('Файл слишком большой (максимум 50 МБ)');
      return Upload.LIST_IGNORE;
    }

    setUploading(true);
    try {
      await uploadMutation.mutateAsync(file);
      message.success('Файл загружен');
    } catch (error) {
      message.error(errorMessage(error, 'Не удалось загрузить файл'));
    } finally {
      setUploading(false);
    }

    return Upload.LIST_IGNORE;
  };

  const handleDownload = async (fileId: number, filename: string) => {
    try {
      const blob = await downloadFile(fileId);
      saveAs(blob, filename);
    } catch (error) {
      message.error(errorMessage(error, 'Не удалось скачать файл'));
    }
  };

  const handleDeleteFile = async (fileId: number) => {
    try {
      await deleteFileMutation.mutateAsync(fileId);
      message.success('Файл удалён');
    } catch (error) {
      message.error(errorMessage(error, 'Не удалось удалить файл'));
    }
  };

  return (
    <Drawer
      width={isMobile ? '100%' : 520}
      open={card !== null}
      onClose={onClose}
      title={
        full ? (
          <Space direction="vertical" size={0}>
            <Typography.Text strong style={{ fontSize: 16 }}>
              {full.university_name}
            </Typography.Text>
            <Typography.Text type="secondary">
              {full.product_name ?? 'Продукт не указан'}
            </Typography.Text>
          </Space>
        ) : (
          'Загрузка…'
        )
      }
      extra={
        full && (
          <Select
            size="small"
            style={{ width: 170 }}
            value={full.stage_id}
            onChange={(stageId) => save({ stage_id: stageId }, 'Этап изменён')}
            options={stages
              .filter((s) => s.is_active)
              .map((s) => ({ value: s.id, label: s.name }))}
          />
        )
      }
    >
      {loading && (
        <div style={{ textAlign: 'center', padding: 32 }}>
          <Spin />
        </div>
      )}
      {full && !loading && (
        <Tabs
          items={[
            {
              key: 'summary',
              label: 'Сводка',
              children: (
                <Space direction="vertical" size={12} style={{ width: '100%' }}>
                  {summaryDisabled ? (
                    <Typography.Text type="secondary">
                      Сводка недоступна: сервис GigaChat не настроен в этом
                      окружении. Задайте GIGACHAT_CREDENTIALS или включите
                      демо-режим (GIGACHAT_FALLBACK_ENABLED=true).
                    </Typography.Text>
                  ) : (
                    <>
                      <Button
                        type="primary"
                        loading={summaryLoading}
                        onClick={() => void requestSummary()}
                      >
                        {summary ? 'Обновить сводку' : 'Получить сводку'}
                      </Button>
                      {summary && (
                        <>
                          <Typography.Paragraph
                            style={{ whiteSpace: 'pre-wrap', marginBottom: 0 }}
                          >
                            {summary.summary}
                          </Typography.Paragraph>
                          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                            Модель: {summary.model} ·{' '}
                            {dayjs(summary.generated_at).format('DD.MM.YYYY HH:mm')}
                          </Typography.Text>
                        </>
                      )}
                    </>
                  )}
                </Space>
              ),
            },
            {
              key: 'info',
              label: 'Сведения',
              children: (
                <Space direction="vertical" size={12} style={{ width: '100%' }}>
                  <InfoField label="Вуз" value={full.university_name} />
                  <InfoField label="Продукт" value={full.product_name} />
                  <InfoField label="Этап" value={full.stage_name} />
                  <EditableField
                    label="Номер договора"
                    value={full.contract_number}
                    onSave={(value) =>
                      save({ contract_number: value }, 'Договор сохранён')
                    }
                  />
                  <EditableField
                    label="Дата договора"
                    value={full.contract_date}
                    onSave={(value) =>
                      save({ contract_date: value }, 'Дата сохранена')
                    }
                  />
                  <EditableField
                    label="Ответственный в вузе"
                    value={full.university_specialist}
                    onSave={(value) =>
                      save({ university_specialist: value }, 'Сохранено')
                    }
                  />
                  {(user?.role === 'admin' || user?.role === 'manager') ? (
                    <div>
                      <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                        КАМ
                      </Typography.Text>
                      <Select
                        id="interaction-kam"
                        style={{ width: '100%' }}
                        placeholder="Не назначен"
                        allowClear
                        value={full.assigned_kam_id ?? undefined}
                        onChange={(value) =>
                          save(
                            { assigned_kam_id: value ?? null },
                            'Ответственный обновлён',
                          )
                        }
                        options={users
                          .filter((u) => u.role === 'user')
                          .map((u) => ({ value: u.id, label: u.full_name }))}
                      />
                    </div>
                  ) : (
                    <InfoField label="КАМ" value={full.assigned_kam_name} />
                  )}
                  <EditableField
                    label="Примечание"
                    value={full.notes}
                    multiline
                    onSave={(value) => save({ notes: value }, 'Примечание сохранено')}
                  />
                </Space>
              ),
            },
            {
              key: 'actions',
              label: `Задачи (${actions.filter((a) => !a.is_completed).length})`,
              children: (
                <Space direction="vertical" size={12} style={{ width: '100%' }}>
                  <Form form={actionForm} layout="vertical">
                    <Form.Item
                      name="title"
                      rules={[{ required: true, message: 'Укажите название' }]}
                    >
                      <Input 
                        id="action-title"
                        name="title"
                        placeholder="Новая задача"
                        autoComplete="off"
                      />
                    </Form.Item>
                    <Space align="start" style={{ width: '100%' }}>
                      <Form.Item name="due_date" style={{ marginBottom: 0 }}>
                        <DatePicker 
                          id="action-due-date"
                          name="due_date"
                          placeholder="Срок" 
                          style={{ width: 140 }}
                          autoComplete="off"
                        />
                      </Form.Item>
                      <Button type="primary" onClick={submitAction}>
                        Добавить
                      </Button>
                    </Space>
                  </Form>
                  <Table<ActionItem>
                    size="small"
                    rowKey="id"
                    pagination={false}
                    dataSource={actions}
                    locale={{ emptyText: 'Задач нет' }}
                    columns={[
                      {
                        title: 'Задача',
                        dataIndex: 'title',
                        render: (title: string, record) => (
                          <Typography.Text
                            delete={record.is_completed}
                            type={record.is_completed ? 'secondary' : undefined}
                          >
                            {title}
                          </Typography.Text>
                        ),
                      },
                      {
                        title: 'Срок',
                        dataIndex: 'due_date',
                        width: 100,
                        render: (date: string | null) =>
                          date ? dayjs(date).format('DD.MM.YYYY') : '—',
                      },
                      {
                        title: '',
                        width: 120,
                        render: (_, record) => (
                          <Space>
                            <Button
                              type="text"
                              size="small"
                              onClick={() =>
                                toggleActionMutation.mutate({
                                  actionId: record.id,
                                  isCompleted: !record.is_completed,
                                })
                              }
                            >
                              {record.is_completed ? 'Вернуть' : 'Готово'}
                            </Button>
                            <Button
                              type="text"
                              size="small"
                              danger
                              onClick={() =>
                                modal.confirm({
                                  title: 'Удалить задачу?',
                                  onOk: () => deleteActionMutation.mutateAsync(record.id),
                                })
                              }
                            >
                              Удалить
                            </Button>
                          </Space>
                        ),
                      },
                    ]}
                  />
                </Space>
              ),
            },
            {
              key: 'comments',
              label: `Комментарии (${comments.length})`,
              children: (
                <Space direction="vertical" size={16} style={{ width: '100%' }}>
                  {comments.length === 0 && <Empty description="Комментариев нет" />}
                  <Timeline
                    items={comments.map((comment) => ({
                      color: 'var(--atmr-accent-default)',
                      children: (
                        <div>
                          <Space align="baseline">
                            <Typography.Text strong>
                              {comment.author_name ?? 'Автор'}
                            </Typography.Text>
                            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                              {dayjs(comment.created_at).format('DD.MM.YYYY HH:mm')}
                            </Typography.Text>
                          </Space>
                          <Typography.Paragraph style={{ marginBottom: 0 }}>
                            {comment.text}
                          </Typography.Paragraph>
                          {(user?.is_admin ||
                            comments.find((c) => c.id === comment.id)?.author_name ===
                              user?.full_name) && (
                            <Button
                              type="text"
                              size="small"
                              danger
                              onClick={() =>
                                modal.confirm({
                                  title: 'Удалить комментарий?',
                                  onOk: () => deleteCommentMutation.mutateAsync(comment.id),
                                })
                              }
                            >
                              Удалить
                            </Button>
                          )}
                        </div>
                      ),
                    }))}
                  />
                  <Space.Compact style={{ width: '100%' }}>
                    <Input
                      placeholder="Новый комментарий"
                      value={commentText}
                      onChange={(e) => setCommentText(e.target.value)}
                      onPressEnter={submitComment}
                    />
                    <Button type="primary" onClick={submitComment}>
                      Отправить
                    </Button>
                  </Space.Compact>
                </Space>
              ),
            },
            {
              key: 'files',
              label: `Файлы (${files.length})`,
              children: (
                <Space direction="vertical" size={16} style={{ width: '100%' }}>
                  <Upload.Dragger
                    name="file"
                    multiple={false}
                    beforeUpload={handleUpload}
                    showUploadList={false}
                    disabled={uploading}
                  >
                    <p className="ant-upload-drag-icon">
                      <InboxOutlined />
                    </p>
                    <p className="ant-upload-text">
                      {uploading ? 'Загрузка...' : 'Нажмите или перетащите файл'}
                    </p>
                    <p className="ant-upload-hint">
                      Разрешены: PNG, JPEG, PDF, ZIP, RAR, DOC, DOCX, XLS, XLSX (максимум 50 МБ)
                    </p>
                  </Upload.Dragger>
                  {files.length === 0 && <Empty description="Файлов нет" />}
                  <Space direction="vertical" size={8} style={{ width: '100%' }}>
                    {files.map((file) => (
                      <div
                        key={file.id}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          padding: '8px 12px',
                          border: '1px solid var(--atmr-border-default)',
                          borderRadius: 6,
                        }}
                      >
                        <Space align="center">
                          <FileOutlined style={{ color: 'var(--atmr-accent-default)' }} />
                          <div>
                            <Typography.Text style={{ fontSize: 13 }}>
                              {file.filename}
                            </Typography.Text>
                            <div>
                              <Typography.Text type="secondary" style={{ fontSize: 11 }}>
                                {(file.size / 1024).toFixed(1)} КБ • {file.uploader_name ?? 'Автор'}
                              </Typography.Text>
                            </div>
                          </div>
                        </Space>
                        <Space>
                          <Button
                            type="text"
                            size="small"
                            icon={<DownloadOutlined />}
                            onClick={() => handleDownload(file.id, file.filename)}
                          />
                          <Button
                            type="text"
                            size="small"
                            danger
                            icon={<DeleteOutlined />}
                            onClick={() =>
                              modal.confirm({
                                title: 'Удалить файл?',
                                onOk: () => handleDeleteFile(file.id),
                              })
                            }
                          />
                        </Space>
                      </div>
                    ))}
                  </Space>
                </Space>
              ),
            },
          ]}
        />
      )}
    </Drawer>
  );
}

function InfoField({ label, value }: { label: string; value: string | null }) {
  return (
    <div>
      <Typography.Text type="secondary" style={{ fontSize: 12 }}>
        {label}
      </Typography.Text>
      <div>{value ?? <Typography.Text type="secondary">Не указано</Typography.Text>}</div>
    </div>
  );
}

function EditableField({
  label,
  value,
  onSave,
  multiline,
}: {
  label: string;
  value: string | null;
  onSave: (value: string | null) => void;
  multiline?: boolean;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value ?? '');

  useEffect(() => {
    setDraft(value ?? '');
  }, [value]);

  if (!editing) {
    return (
      <div>
        <Space align="baseline">
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            {label}
          </Typography.Text>
          <Button type="link" size="small" onClick={() => setEditing(true)}>
            Изменить
          </Button>
        </Space>
        <div>
          {value ?? <Typography.Text type="secondary">Не указано</Typography.Text>}
        </div>
      </div>
    );
  }

  return (
    <div>
      <Typography.Text type="secondary" style={{ fontSize: 12 }}>
        {label}
      </Typography.Text>
      {multiline ? (
        <Input.TextArea
          autoSize={{ minRows: 2, maxRows: 6 }}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
        />
      ) : (
        <Input value={draft} onChange={(e) => setDraft(e.target.value)} />
      )}
      <Space style={{ marginTop: 8 }}>
        <Button
          type="primary"
          size="small"
          onClick={() => {
            onSave(draft || null);
            setEditing(false);
          }}
        >
          Сохранить
        </Button>
        <Button size="small" onClick={() => setEditing(false)}>
          Отмена
        </Button>
      </Space>
    </div>
  );
}
