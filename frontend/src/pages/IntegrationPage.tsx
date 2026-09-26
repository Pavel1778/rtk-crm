import {
  App as AntApp,
  Alert,
  Button,
  Card,
  Col,
  Descriptions,
  Input,
  Row,
  Segmented,
  Space,
  Statistic,
  Table,
  Tag,
  Typography,
} from 'antd';
import { useEffect, useState } from 'react';

import { errorMessage } from '../api/client';
import {
  getIntegrationSchema,
  getOutboundPackage,
  importIntegration,
  previewIntegration,
  pullIntegration,
  type IntegrationSchema,
  type IntegrationSummary,
} from '../api/endpoints';
import { useRole } from '../stores/authStore';

const { Paragraph, Text } = Typography;

const SAMPLE_PAYLOAD = `[
  {
    "external_id": "LMS-3001",
    "university": "МГТУ им. Н. Э. Баумана",
    "product": "RUBOTYAKA",
    "direction": "Информационная безопасность",
    "stage_code": "meeting",
    "contract_number": "LMS-2026/3001",
    "university_specialist": "Иванов И. И.",
    "notes": "Пример пакета из LMS"
  }
]`;

type Source = 'lms' | 'cms';

/**
 * Интеграция с внешними системами заказчика (ФТ-5).
 *
 * Входящий поток: пакет JSON из LMS или CMS разбирается и раскладывается по
 * workflow. Есть dry-run, чтобы проверить пакет до записи. Исходящий поток:
 * выгрузка карточек с ключами связи БД и S3 для сопоставления на стороне
 * принимающей системы. Доступно руководителю и администратору.
 */
export default function IntegrationPage() {
  const { message } = AntApp.useApp();
  const role = useRole();
  const [source, setSource] = useState<Source>('lms');
  const [schema, setSchema] = useState<IntegrationSchema | null>(null);
  const [payload, setPayload] = useState(SAMPLE_PAYLOAD);
  const [summary, setSummary] = useState<IntegrationSummary | null>(null);
  const [busy, setBusy] = useState<'preview' | 'import' | 'pull' | 'outbound' | null>(null);

  const canManage = role === 'admin' || role === 'manager';

  useEffect(() => {
    void getIntegrationSchema().then(setSchema).catch(() => undefined);
  }, []);

  const parsePayload = (): unknown | null => {
    try {
      return JSON.parse(payload);
    } catch {
      message.error('Пакет не является корректным JSON');
      return null;
    }
  };

  const runPreview = async () => {
    const data = parsePayload();
    if (data === null) return;
    setBusy('preview');
    try {
      const result = await previewIntegration(data, source);
      setSummary(result);
      message.success(`Разобрано записей: ${result.total}`);
    } catch (error) {
      message.error(errorMessage(error));
    } finally {
      setBusy(null);
    }
  };

  const runImport = async () => {
    const data = parsePayload();
    if (data === null) return;
    setBusy('import');
    try {
      const result = await importIntegration(data, source);
      setSummary(result);
      message.success(
        `Создано: ${result.created}, обновлено: ${result.updated}, пропущено: ${result.skipped}`,
      );
    } catch (error) {
      message.error(errorMessage(error));
    } finally {
      setBusy(null);
    }
  };

  const runPull = async () => {
    setBusy('pull');
    try {
      const result = await pullIntegration(source);
      setSummary(result);
      message.success(
        `Загружено из ${source.toUpperCase()}: создано ${result.created}, обновлено ${result.updated}`,
      );
    } catch (error) {
      message.error(errorMessage(error));
    } finally {
      setBusy(null);
    }
  };

  const runOutbound = async () => {
    setBusy('outbound');
    try {
      const result = await getOutboundPackage();
      message.success(`Исходящий пакет: ${result.total} записей для ${result.targets.join(', ')}`);
    } catch (error) {
      message.error(errorMessage(error));
    } finally {
      setBusy(null);
    }
  };

  if (!canManage) {
    return (
      <Card>
        <Alert
          type="info"
          showIcon
          message="Раздел доступен руководителю и администратору"
        />
      </Card>
    );
  }

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Card>
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <Typography.Title level={4} style={{ margin: 0 }}>
            Интеграция с LMS и CMS
          </Typography.Title>
          <Paragraph type="secondary" style={{ margin: 0 }}>
            Входящий пакет JSON из внешней системы раскладывается по этапам
            workflow. Перед записью можно выполнить проверку без сохранения.
            Повторный импорт обновляет карточку по номеру договора, а не
            создаёт дубль.
          </Paragraph>
        </Space>
      </Card>

      {schema && (
        <Card title="Контракт обмена" size="small">
          <Descriptions column={1} size="small">
            <Descriptions.Item label="Обязательные поля">
              <Space wrap>
                {schema.required.map((field) => (
                  <Tag key={field} color="red">
                    {field}
                  </Tag>
                ))}
              </Space>
            </Descriptions.Item>
            <Descriptions.Item label="Необязательные поля">
              <Space wrap>
                {schema.optional.map((field) => (
                  <Tag key={field}>{field}</Tag>
                ))}
              </Space>
            </Descriptions.Item>
            <Descriptions.Item label="Воронки">
              <Space wrap>
                {schema.scope_values.map((scope) => (
                  <Tag key={scope} color="blue">
                    {scope.toUpperCase()}
                  </Tag>
                ))}
              </Space>
            </Descriptions.Item>
          </Descriptions>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {schema.notes}
          </Text>
        </Card>
      )}

      <Card
        title="Входящий поток"
        size="small"
        extra={
          <Segmented
            value={source}
            onChange={(value) => setSource(value as Source)}
            options={[
              { label: 'LMS', value: 'lms' },
              { label: 'CMS', value: 'cms' },
            ]}
          />
        }
      >
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <Input.TextArea
            value={payload}
            onChange={(event) => setPayload(event.target.value)}
            autoSize={{ minRows: 8, maxRows: 16 }}
            spellCheck={false}
          />
          <Space wrap>
            <Button onClick={() => void runPreview()} loading={busy === 'preview'}>
              Проверить без записи
            </Button>
            <Button type="primary" onClick={() => void runImport()} loading={busy === 'import'}>
              Импортировать
            </Button>
            <Button onClick={() => void runPull()} loading={busy === 'pull'}>
              Загрузить из {source.toUpperCase()}
            </Button>
          </Space>
          <Text type="secondary" style={{ fontSize: 12 }}>
            Кнопка «Загрузить из {source.toUpperCase()}» читает заглушку внешней
            системы: контракт от заказчика ещё не предоставлен, разбор и запись
            при этом настоящие.
          </Text>
        </Space>
      </Card>

      {summary && (
        <Card title="Результат" size="small">
          <Row gutter={16}>
            <Col span={6}>
              <Statistic title="Всего записей" value={summary.total} />
            </Col>
            <Col span={6}>
              <Statistic title="Создано" value={summary.created} valueStyle={{ color: '#3f8600' }} />
            </Col>
            <Col span={6}>
              <Statistic title="Обновлено" value={summary.updated} valueStyle={{ color: '#1677ff' }} />
            </Col>
            <Col span={6}>
              <Statistic title="Пропущено" value={summary.skipped} valueStyle={{ color: '#cf1322' }} />
            </Col>
          </Row>

          {summary.errors.length > 0 && (
            <Alert
              type="error"
              showIcon
              style={{ marginTop: 16 }}
              message="Ошибки"
              description={
                <ul style={{ margin: 0, paddingLeft: 18 }}>
                  {summary.errors.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              }
            />
          )}

          {summary.warnings.length > 0 && (
            <Alert
              type="warning"
              showIcon
              style={{ marginTop: 16 }}
              message="Предупреждения"
              description={
                <ul style={{ margin: 0, paddingLeft: 18 }}>
                  {summary.warnings.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              }
            />
          )}
        </Card>
      )}

      <Card title="Исходящий поток" size="small">
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <Paragraph type="secondary" style={{ margin: 0 }}>
            Выгрузка карточек для LMS и CMS содержит данные взаимодействий и
            ключи связи: id записей, внешние ключи и список файлов в S3. По этим
            ключам принимающая система сопоставляет объекты со своими записями.
          </Paragraph>
          <Button onClick={() => void runOutbound()} loading={busy === 'outbound'}>
            Сформировать пакет
          </Button>
        </Space>
      </Card>

      {summary && summary.created_ids.length > 0 && (
        <Card title="Созданные взаимодействия" size="small">
          <Table
            size="small"
            rowKey="id"
            pagination={false}
            dataSource={summary.created_ids.map((id) => ({ id }))}
            columns={[
              { title: 'ID', dataIndex: 'id', key: 'id' },
              { title: 'Источник', dataIndex: 'id', key: 'source', render: () => source.toUpperCase() },
            ]}
          />
        </Card>
      )}
    </Space>
  );
}
