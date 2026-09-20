import { App as AntApp, Button, ColorPicker, Form, Input, InputNumber, Modal, Space } from 'antd';
import { useEffect } from 'react';

interface StageEditorProps {
  open: boolean;
  stage?: {
    id?: number;
    code: string;
    name: string;
    order: number;
    color: string;
  };
  onCancel: () => void;
  onSave: (data: { code: string; name: string; order: number; color: string }) => void;
}

export default function StageEditor({ open, stage, onCancel, onSave }: StageEditorProps) {
  const { message } = AntApp.useApp();
  const [form] = Form.useForm();

  useEffect(() => {
    if (open) {
      if (stage) {
        form.setFieldsValue(stage);
      } else {
        form.resetFields();
        form.setFieldsValue({ order: 1, color: '#6E41F2' });
      }
    }
  }, [open, stage, form]);

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      const color = typeof values.color === 'string' ? values.color : values.color?.toHexString?.();
      onSave({
        code: values.code,
        name: values.name,
        order: values.order,
        color: color ?? '#6E41F2',
      });
      form.resetFields();
    } catch (error) {
      message.error('Проверьте форму');
    }
  };

  return (
    <Modal
      title={stage?.id ? 'Редактировать этап' : 'Создать этап'}
      open={open}
      onCancel={onCancel}
      onOk={handleSave}
      width={480}
      okText="Сохранить"
      cancelText="Отмена"
    >
      <Form form={form} layout="vertical">
        <Form.Item
          name="code"
          label="Код"
          rules={[{ required: true, message: 'Код обязателен' }]}
        >
          <Input placeholder="Например: pilot" />
        </Form.Item>
        <Form.Item
          name="name"
          label="Название"
          rules={[{ required: true, message: 'Название обязательно' }]}
        >
          <Input placeholder="Например: Пилотный проект" />
        </Form.Item>
        <Form.Item
          name="order"
          label="Порядок"
          rules={[{ required: true, message: 'Порядок обязателен' }]}
        >
          <InputNumber min={1} style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="color" label="Цвет" initialValue="#6E41F2">
          <ColorPicker showText format="hex" />
        </Form.Item>
      </Form>
    </Modal>
  );
}
