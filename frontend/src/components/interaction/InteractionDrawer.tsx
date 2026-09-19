import {
  App as AntApp,
  Button,
  DatePicker,
  Drawer,
  Empty,
  Form,
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
import { useEffect, useState } from 'react';
import { saveAs } from 'file-saver';

import { errorMessage } from '../../api/client';
import {
  createAction,
  createComment,
  deleteAction,
  deleteComment,
  deleteFile,
  downloadFile,
  getInteraction,
  listActions,
  listComments,
  listFiles,
  listStages,
  updateAction,
  updateInteraction,
  uploadFile,
} from '../../api/endpoints';
import type {
  ActionItem,
  AttachedFile,
  CommentItem,
  Interaction,
  InteractionCard,
  WorkflowStage,
} from '../../types';
import { useAuthStore } from '../../stores/authStore';

interface DrawerProps {
  card: InteractionCard | null;
  onClose: () => void;
  onChanged: () => void;
}

export default function InteractionDrawer({ card, onClose, onChanged }: DrawerProps) {
  const { message, modal } = AntApp.useApp();
  const user = useAuthStore((s) => s.user);
  const [full, setFull] = useState<Interaction | null>(null);
  const [actions, setActions] = useState<ActionItem[]>([]);
  const [comments, setComments] = useState<CommentItem[]>([]);
  const [files, setFiles] = useState<AttachedFile[]>([]);
  const [stages, setStages] = useState<WorkflowStage[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [commentText, setCommentText] = useState('');
  const [actionForm] = Form.useForm();

  const load = async () => {
    if (!card) return;
    setLoading(true);
    try {
      const [detail, acts, cmts, fls] = await Promise.all([
        getInteraction(card.id),
        listActions(card.id),
        listComments(card.id),
        listFiles(card.id),
      ]);
      setFull(detail);
      setActions(acts);
      setComments(cmts);
      setFiles(fls);
    } catch (error) {
      message.error(errorMessage(error, 'Не удалось загрузить карточку'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (card) {
      void load();
      void listStages().then(setStages).catch(() => undefined);
    } else {
      setFull(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [card?.id]);

  const save = async (payload: Record<string, unknown>, successText: string) => {
    if (!card) return;
    try {
      await updateInteraction(card.id, payload);
      message.success(successText);
      await load();
      onChanged();
    } catch (error) {
      message.error(errorMessage(error, 'Не удалось сохранить'));
    }
  };

  const submitAction = async () => {
    if (!card) return;
    try {
      const values = await actionForm.validateFields();
      await createAction(card.id, {
        title: values.title,
        description: values.description || undefined,
        due_date: values.due_date ? values.due_date.format('YYYY-MM-DD') : undefined,
      });
      actionForm.resetFields();
      await load();
      onChanged();
    } catch (error) {
      if (error instanceof Error) {
        message.error(errorMessage(error, 'Не удалось добавить задачу'));
      }
    }
  };

  const submitComment = async () => {
    if (!card || !commentText.trim()) return;
    try {
      await createComment(card.id, commentText.trim());
      setCommentText('');
      await load();
      onChanged();
    } catch (error) {
      message.error(errorMessage(error, 'Не удалось добавить комментарий'));
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
      await uploadFile(card.id, file);
      message.success('Файл загружен');
      await load();
      onChanged();
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
      await deleteFile(fileId);
      message.success('Файл удалён');
      await load();
      onChanged();
    } catch (error) {
      message.error(errorMessage(error, 'Не удалось удалить файл'));
    }
  };

  return (
    <Drawer
      width={520}
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
                  <InfoField label="КАМ" value={full.assigned_kam_name} />
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
                      <Input placeholder="Новая задача" />
                    </Form.Item>
                    <Space align="start" style={{ width: '100%' }}>
                      <Form.Item name="due_date" style={{ marginBottom: 0 }}>
                        <DatePicker placeholder="Срок" style={{ width: 140 }} />
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
                                updateAction(record.id, {
                                  is_completed: !record.is_completed,
                                }).then(load)
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
                                  onOk: () => deleteAction(record.id).then(load),
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
                      color: '#6E41F2',
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
                                  onOk: () => deleteComment(comment.id).then(load),
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
                          border: '1px solid #E0E0E5',
                          borderRadius: 6,
                        }}
                      >
                        <Space align="center">
                          <FileOutlined style={{ color: '#6E41F2' }} />
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
