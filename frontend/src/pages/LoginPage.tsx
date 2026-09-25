import { LockOutlined, MailOutlined } from '@ant-design/icons';
import { App as AntApp, Button, Card, Form, Input, Typography } from 'antd';
import { useNavigate } from 'react-router-dom';

import { errorMessage } from '../api/client';
import { useAuthStore } from '../stores/authStore';

interface LoginForm {
  email: string;
  password: string;
}

export default function LoginPage() {
  const { message } = AntApp.useApp();
  const navigate = useNavigate();
  const signIn = useAuthStore((s) => s.signIn);
  const loading = useAuthStore((s) => s.loading);

  const onFinish = async (values: LoginForm) => {
    try {
      await signIn(values.email, values.password);
      navigate('/', { replace: true });
    } catch (error) {
      message.error(errorMessage(error, 'Не удалось войти'));
    }
  };

  return (
    <div
      className="auth-screen"
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'var(--atmr-bg-page)',
        padding: 16,
      }}
    >
      <Card style={{ width: 400, border: '1px solid var(--atmr-border-soft)' }}>
        <Typography.Title level={3} style={{ marginTop: 0 }}>
          Вход в RTK CRM
        </Typography.Title>
        <Typography.Paragraph type="secondary">
          Система сопровождения взаимодействия с вузами-партнёрами
        </Typography.Paragraph>
        <Form<LoginForm> layout="vertical" onFinish={onFinish}>
          <Form.Item
            name="email"
            label="Эл. почта"
            rules={[
              { required: true, message: 'Укажите эл. почту' },
              { type: 'email', message: 'Некорректный адрес' },
            ]}
          >
            <Input 
              id="login-email"
              name="email"
              prefix={<MailOutlined />} 
              placeholder="kam@rtk.ru" 
              size="large"
              autoComplete="email"
            />
          </Form.Item>
          <Form.Item
            name="password"
            label="Пароль"
            rules={[{ required: true, message: 'Укажите пароль' }]}
          >
            <Input.Password
              id="login-password"
              name="password"
              prefix={<LockOutlined />}
              placeholder="Пароль"
              size="large"
              autoComplete="current-password"
            />
          </Form.Item>
          <Form.Item style={{ marginBottom: 0 }}>
            <Button
              type="primary"
              htmlType="submit"
              block
              size="large"
              loading={loading}
            >
              Войти
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
}
