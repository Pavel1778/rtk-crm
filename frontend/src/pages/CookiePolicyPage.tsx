import { Button, Card, Table, Typography } from 'antd';
import { Link } from 'react-router-dom';

import { COOKIE_CATEGORIES, openCookieSettings } from '../lib/cookieConsent';

const { Paragraph, Title } = Typography;

const RETENTION: Record<string, string> = {
  necessary: 'до окончания сессии / 24 часа',
  analytics: '12 месяцев',
  functional: '12 месяцев',
  marketing: '6 месяцев',
};

export default function CookiePolicyPage() {
  return (
    <div className="page-container" style={{ paddingBlock: 24 }}>
      <Card className="policy-card" style={{ maxWidth: 900, margin: '0 auto' }}>
        <Title level={2}>Политика обработки файлов cookie</Title>
        <Paragraph type="secondary">Дата последнего обновления: сентябрь 2026</Paragraph>

        <Title level={4}>1. Что такое файлы cookie</Title>
        <Paragraph>
          Файлы cookie — небольшие текстовые файлы, которые сохраняются в браузере
          при работе с сайтом. Они позволяют распознавать сессию пользователя,
          сохранять настройки интерфейса и собирать обезличенную статистику.
          В CRM также используется локальное хранилище браузера (localStorage) —
          настоящая политика распространяется и на него.
        </Paragraph>

        <Title level={4}>2. Правовые основания</Title>
        <Paragraph>
          Обработка выполняется в соответствии с Федеральным законом от 27.07.2006
          № 152-ФЗ «О персональных данных». Cookie аналитических, функциональных
          и маркетинговых категорий устанавливаются только после отдельного явного
          согласия пользователя, которое можно отозвать в любой момент.
        </Paragraph>

        <Title level={4}>3. Какие категории используются</Title>
        <Table
          rowKey="key"
          pagination={false}
          size="small"
          className="policy-table"
          scroll={{ x: 640 }}
          style={{ marginBottom: 24 }}
          columns={[
            { title: 'Категория', dataIndex: 'title', width: 180 },
            { title: 'Назначение', dataIndex: 'description' },
            {
              title: 'Срок хранения',
              dataIndex: 'key',
              width: 200,
              render: (key: string) => RETENTION[key],
            },
            {
              title: 'Отключение',
              dataIndex: 'required',
              width: 130,
              render: (required: boolean) => (required ? 'Невозможно' : 'Доступно'),
            },
          ]}
          dataSource={COOKIE_CATEGORIES}
        />

        <Title level={4}>4. Как управлять согласием</Title>
        <Paragraph>
          Выбор сохраняется локально в браузере под ключом{' '}
          <code>rtk_cookie_consent</code> и не передаётся третьим лицам. Изменить
          решение можно в любой момент кнопкой ниже либо очисткой данных сайта в
          настройках браузера.
        </Paragraph>
        <Paragraph>
          <Button onClick={openCookieSettings}>Настроить cookie</Button>
        </Paragraph>

        <Title level={4}>5. Права пользователя</Title>
        <Paragraph>
          Пользователь вправе получить сведения об обработке своих персональных
          данных, требовать их уточнения, блокирования или уничтожения, а также
          отозвать согласие. Порядок описан в{' '}
          <Link to="/privacy">Политике обработки персональных данных</Link>.
        </Paragraph>

        <Title level={4}>6. Контакты оператора</Title>
        <Paragraph>
          Оператор: ИТ Школа ПАО «Ростелеком».
          <br />
          Электронная почта для обращений: privacy@rtk-crm.ru
        </Paragraph>

        <Paragraph>
          <Link to="/">Вернуться в систему</Link>
        </Paragraph>
      </Card>
    </div>
  );
}
