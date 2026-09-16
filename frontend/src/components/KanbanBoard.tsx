import React, { useState, useEffect } from 'react';
import { Card, Tag, Button, Space, Typography, Modal, Form, Input, Select, message } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import type { University, WorkflowStage } from '../types';
import { universitiesApi, workflowApi } from '../api/client';

const { Title } = Typography;
const { TextArea } = Input;

interface KanbanBoardProps {
  // Пропсы для компонента
}

const KanbanBoard: React.FC<KanbanBoardProps> = () => {
  const [universities, setUniversities] = useState<University[]>([]);
  const [stages, setStages] = useState<WorkflowStage[]>([]);
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingUniversity, setEditingUniversity] = useState<University | null>(null);
  const [form] = Form.useForm();

  // Загрузка данных
  const loadData = async () => {
    try {
      setLoading(true);
      const [unisData, stagesData] = await Promise.all([
        universitiesApi.getAll(),
        workflowApi.getAll(),
      ]);
      setUniversities(unisData);
      setStages(stagesData.sort((a, b) => a.order - b.order));
    } catch (error) {
      console.error('Ошибка загрузки данных:', error);
      message.error('Не удалось загрузить данные');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Открытие модального окна создания/редактирования
  const openModal = (university?: University) => {
    if (university) {
      setEditingUniversity(university);
      form.setFieldsValue(university);
    } else {
      setEditingUniversity(null);
      form.resetFields();
    }
    setIsModalOpen(true);
  };

  // Создание или обновление вуза
  const handleSubmit = async (values: any) => {
    try {
      if (editingUniversity) {
        await universitiesApi.update(editingUniversity.id, values);
        message.success('Вуз успешно обновлён');
      } else {
        await universitiesApi.create(values);
        message.success('Вуз успешно создан');
      }
      setIsModalOpen(false);
      form.resetFields();
      loadData();
    } catch (error: any) {
      console.error('Ошибка сохранения:', error);
      message.error(error.response?.data?.detail || 'Ошибка сохранения');
    }
  };

  // Удаление вуза
  const handleDelete = async (id: number) => {
    Modal.confirm({
      title: 'Подтверждение удаления',
      content: 'Вы уверены, что хотите удалить этот вуз?',
      okText: 'Удалить',
      okType: 'danger',
      cancelText: 'Отмена',
      onOk: async () => {
        try {
          await universitiesApi.delete(id);
          message.success('Вуз успешно удалён');
          loadData();
        } catch (error: any) {
          console.error('Ошибка удаления:', error);
          message.error('Ошибка удаления');
        }
      },
    });
  };

  // Цвета для статусов
  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      'Поиск контактов': 'gray',
      'Коммуникация': 'blue',
      'Встреча': 'cyan',
      'Документы': 'orange',
      'Подписание': 'gold',
      'Внедрение': 'green',
      'Обучение': 'purple',
      'Ведение занятий': 'lime',
    };
    return colors[status] || 'default';
  };

  if (loading) {
    return <div style={{ textAlign: 'center', padding: 40 }}>Загрузка...</div>;
  }

  return (
    <div>
      <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between' }}>
        <Title level={3} style={{ margin: 0 }}>
          Kanban доска этапов
        </Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => openModal()}>
          Добавить вуз
        </Button>
      </div>

      {/* Сетка колонок */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: `repeat(${stages.length}, minmax(300px, 1fr))`,
          gap: 16,
          overflowX: 'auto',
          paddingBottom: 16,
        }}
      >
        {stages.map((stage) => {
          const stageUniversities = universities.filter(
            (u) => u.current_workflow_stage_id === stage.id
          );

          return (
            <div
              key={stage.id}
              style={{
                background: '#f5f5f5',
                borderRadius: 8,
                padding: 16,
                minHeight: 400,
              }}
            >
              <div style={{ marginBottom: 16 }}>
                <Title level={5} style={{ margin: 0 }}>
                  {stage.order}. {stage.name}
                </Title>
                <Tag color="blue" style={{ marginTop: 8 }}>
                  {stageUniversities.length} вузов
                </Tag>
              </div>

              {/* Карточки вузов в колонке */}
              <Space direction="vertical" style={{ width: '100%' }} size={12}>
                {stageUniversities.map((uni) => (
                  <Card
                    key={uni.id}
                    size="small"
                    hoverable
                    style={{ borderRadius: 6 }}
                    title={uni.name}
                    extra={
                      <Space>
                        <Button
                          type="text"
                          icon={<EditOutlined />}
                          onClick={() => openModal(uni)}
                        />
                        <Button
                          type="text"
                          danger
                          icon={<DeleteOutlined />}
                          onClick={() => handleDelete(uni.id)}
                        />
                      </Space>
                    }
                  >
                    <div style={{ marginBottom: 8 }}>
                      <Tag color={getStatusColor(uni.status)}>{uni.status}</Tag>
                    </div>
                    <div style={{ fontSize: 12, color: '#666', marginBottom: 4 }}>
                      <strong>Продукт:</strong> {uni.product || '—'}
                    </div>
                    <div style={{ fontSize: 12, color: '#666', marginBottom: 4 }}>
                      <strong>Менеджер:</strong> {uni.manager_name || '—'}
                    </div>
                    <div style={{ fontSize: 12, color: '#666' }}>
                      <strong>Ответственный:</strong> {uni.university_responsible || '—'}
                    </div>
                    {uni.comment && (
                      <div
                        style={{
                          marginTop: 8,
                          padding: 8,
                          background: '#fafafa',
                          borderRadius: 4,
                          fontSize: 12,
                        }}
                      >
                        {uni.comment}
                      </div>
                    )}
                  </Card>
                ))}
              </Space>
            </div>
          );
        })}
      </div>

      {/* Модальное окно создания/редактирования */}
      <Modal
        title={editingUniversity ? 'Редактировать вуз' : 'Новый вуз'}
        open={isModalOpen}
        onCancel={() => setIsModalOpen(false)}
        footer={null}
        width={700}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item
            name="name"
            label="Название вуза"
            rules={[{ required: true, message: 'Введите название вуза' }]}
          >
            <Input placeholder="МГУ им. М.В. Ломоносова" />
          </Form.Item>

          <Form.Item name="vendor" label="Вендор">
            <Input placeholder="Ростелеком" />
          </Form.Item>

          <Form.Item name="product" label="Продукт">
            <Input placeholder="DevOps, Python, QA" />
          </Form.Item>

          <Form.Item name="contract_number" label="Номер договора">
            <Input placeholder="РТК-2026-001" />
          </Form.Item>

          <Form.Item name="license_signed" label="Лицензия подписана" valuePropName="checked">
            <Select>
              <Select.Option value={true}>Да</Select.Option>
              <Select.Option value={false}>Нет</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item name="license_expiry_year" label="Год окончания лицензии">
            <Input type="number" placeholder="2027" />
          </Form.Item>

          <Form.Item
            name="status"
            label="Статус"
            rules={[{ required: true, message: 'Выберите статус' }]}
          >
            <Select placeholder="Выберите статус">
              <Select.Option value="Поиск контактов">Поиск контактов</Select.Option>
              <Select.Option value="Коммуникация">Коммуникация</Select.Option>
              <Select.Option value="Встреча">Встреча</Select.Option>
              <Select.Option value="Документы">Документы</Select.Option>
              <Select.Option value="Подписание">Подписание</Select.Option>
              <Select.Option value="Внедрение">Внедрение</Select.Option>
              <Select.Option value="Обучение">Обучение</Select.Option>
              <Select.Option value="Ведение занятий">Ведение занятий</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item name="manager_name" label="Менеджер Ростелекома">
            <Input placeholder="Иванов И.И." />
          </Form.Item>

          <Form.Item name="university_responsible" label="Ответственный в вузе">
            <Input placeholder="Петров П.П." />
          </Form.Item>

          <Form.Item
            name="current_workflow_stage_id"
            label="Этап воркфлоу"
            rules={[{ required: true, message: 'Выберите этап' }]}
          >
            <Select placeholder="Выберите этап" showSearch>
              {stages.map((stage) => (
                <Select.Option key={stage.id} value={stage.id}>
                  {stage.order}. {stage.name}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item name="comment" label="Комментарий">
            <TextArea rows={4} placeholder="Дополнительная информация..." />
          </Form.Item>

          <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
            <Space>
              <Button onClick={() => setIsModalOpen(false)}>Отмена</Button>
              <Button type="primary" htmlType="submit">
                {editingUniversity ? 'Сохранить' : 'Создать'}
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default KanbanBoard;
