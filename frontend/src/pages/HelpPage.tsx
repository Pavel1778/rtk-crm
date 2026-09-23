import { App as AntApp, Card, Spin, Tabs, Typography } from 'antd';
import { useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const { Title } = Typography;

interface MarkdownContent {
  [key: string]: string;
}

export default function HelpPage() {
  const { message } = AntApp.useApp();
  const [content, setContent] = useState<MarkdownContent>({});
  const [loading, setLoading] = useState(true);

  const loadMarkdown = async (filename: string) => {
    try {
      const response = await fetch(`/docs/${filename}`);
      if (!response.ok) {
        throw new Error('Не удалось загрузить документ');
      }
      const text = await response.text();
      return text;
    } catch (error) {
      message.error('Не удалось загрузить документ');
      return '# Ошибка загрузки\n\nДокумент не найден.';
    }
  };

  useEffect(() => {
    const loadAll = async () => {
      setLoading(true);
      const [userGuide, adminGuide, security, architecture] = await Promise.all([
        loadMarkdown('USER_GUIDE.md'),
        loadMarkdown('ADMIN_GUIDE.md'),
        loadMarkdown('SECURITY.md'),
        loadMarkdown('ARCHITECTURE.md'),
      ]);
      setContent({
        userGuide,
        adminGuide,
        security,
        architecture,
      });
      setLoading(false);
    };
    void loadAll();
  }, []);

  const items = [
    {
      key: 'user',
      label: 'Руководство пользователя',
      children: [
        <div key="user" style={{ padding: 16 }}>
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{content.userGuide}</ReactMarkdown>
        </div>,
      ],
    },
    {
      key: 'admin',
      label: 'Руководство администратора',
      children: [
        <div key="admin" style={{ padding: 16 }}>
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{content.adminGuide}</ReactMarkdown>
        </div>,
      ],
    },
    {
      key: 'security',
      label: 'Безопасность',
      children: [
        <div key="security" style={{ padding: 16 }}>
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{content.security}</ReactMarkdown>
        </div>,
      ],
    },
    {
      key: 'architecture',
      label: 'Архитектура',
      children: [
        <div key="architecture" style={{ padding: 16 }}>
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{content.architecture}</ReactMarkdown>
        </div>,
      ],
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Title level={2}>Помощь</Title>
      <Card style={{ border: '1px solid var(--atmr-border-soft)' }}>
        {loading ? (
          <div style={{ textAlign: 'center', padding: 48 }}>
            <Spin size="large" />
          </div>
        ) : (
          <Tabs defaultActiveKey="user" items={items} />
        )}
      </Card>
    </div>
  );
}
