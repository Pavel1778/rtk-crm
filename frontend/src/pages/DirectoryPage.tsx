import { useEffect, useRef, useState } from 'react';
import {
  App as AntApp,
  Button,
  Card,
  Descriptions,
  Empty,
  Grid,
  Input,
  Modal,
  Popconfirm,
  Select,
  Space,
  Spin,
  Table,
  Tag,
  Tabs,
} from 'antd';

import { errorMessage } from '../api/client';
import {
  createDirection,
  createProduct,
  createUniversity,
  deleteDirection,
  deleteProduct,
  deleteUniversity,
  listDirections,
  listProducts,
  listUniversities,
  executeCatalogImport,
  previewCatalogImport,
} from '../api/endpoints';
import type { ITDirection, ITProduct, University } from '../types';
import { useRole } from '../stores/authStore';

export default function DirectoryPage() {
  const role = useRole();
  return (
    <div className="page-container">
      <div className="page-header">
        <h1>Справочники</h1>
      </div>
      <div className="page-content">
        {role !== 'user' && <CatalogImportPanel />}
        <Tabs
          items={[
            { key: 'universities', label: 'Вузы', children: <UniversitiesTab /> },
            { key: 'products', label: 'Продукты', children: <ProductsTab /> },
            { key: 'directions', label: 'Направления', children: <DirectionsTab /> },
          ]}
        />
      </div>
    </div>
  );
}

const IMPORT_FIELDS = {
  universities: [
    ['name', 'Название ВУЗа', true],
    ['city', 'Город', false],
    ['contact_person', 'Ответственные от ВУЗа', false],
    ['contact_email', 'Email', false],
    ['contact_phone', 'Телефон', false],
  ],
  products: [
    ['name', 'Название продукта', true],
    ['direction', 'ИТ-направление', false],
  ],
} as const;

function CatalogImportPanel() {
  const { message } = AntApp.useApp();
  const inputRef = useRef<HTMLInputElement>(null);
  const [catalogType, setCatalogType] = useState<'universities' | 'products'>('universities');
  const [format, setFormat] = useState<'excel' | 'json'>('excel');
  const [file, setFile] = useState<File | null>(null);
  const [headers, setHeaders] = useState<string[]>([]);
  const [previewRows, setPreviewRows] = useState<Record<string, unknown>[]>([]);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  const fields = IMPORT_FIELDS[catalogType];
  const profileKey = `rtk-import-mapping:${catalogType}:${format}`;

  const selectFile = (nextFormat: 'excel' | 'json') => {
    setFormat(nextFormat);
    if (inputRef.current) {
      inputRef.current.accept = nextFormat === 'json' ? '.json,application/json' : '.xls,.xlsx';
      inputRef.current.value = '';
      inputRef.current.click();
    }
  };

  const onFile = async (selected: File | undefined) => {
    if (!selected) return;
    setFile(selected);
    setLoading(true);
    try {
      const saved = localStorage.getItem(profileKey);
      const savedMapping = saved ? JSON.parse(saved) as Record<string, string> : {};
      const result = await previewCatalogImport(catalogType, selected, savedMapping, format);
      setHeaders(result.headers);
      setPreviewRows(result.data.slice(0, 5));
      setMapping(savedMapping);
      setOpen(true);
      if (result.errors.length) message.warning(result.errors.join('; '));
    } catch (error) {
      message.error(errorMessage(error, 'Не удалось прочитать файл'));
    } finally {
      setLoading(false);
    }
  };

  const execute = async () => {
    if (!file) return;
    const requiredMissing = fields.some(([key, , required]) => required && !mapping[key]);
    if (requiredMissing) {
      message.error('Сопоставьте все обязательные поля');
      return;
    }
    setLoading(true);
    try {
      localStorage.setItem(profileKey, JSON.stringify(mapping));
      const result = await executeCatalogImport(catalogType, file, mapping, format);
      if (result.errors.length) message.warning(result.errors.join('; '));
      message.success(`Импортировано записей: ${result.created}`);
      setOpen(false);
    } catch (error) {
      message.error(errorMessage(error, 'Импорт не выполнен'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card
      size="small"
      title="Импорт справочников"
      extra={<Tag color="blue">XLS / XLSX / JSON</Tag>}
      style={{ marginBottom: 16 }}
    >
      <Space wrap>
        <Select
          value={catalogType}
          onChange={setCatalogType}
          options={[
            { value: 'universities', label: 'Вузы' },
            { value: 'products', label: 'Продукты' },
          ]}
          style={{ width: 180 }}
        />
        <Button onClick={() => selectFile('excel')} loading={loading}>
          Импорт XLS / XLSX
        </Button>
        <Button onClick={() => selectFile('json')} loading={loading}>
          Импорт JSON
        </Button>
      </Space>
      <input
        ref={inputRef}
        hidden
        type="file"
        onChange={(event) => void onFile(event.target.files?.[0])}
      />
      <Modal
        title={`Сопоставление полей: ${file?.name ?? ''}`}
        open={open}
        width={900}
        onCancel={() => setOpen(false)}
        onOk={() => void execute()}
        confirmLoading={loading}
        okText="Импортировать"
      >
        <Descriptions size="small" column={1} style={{ marginBottom: 16 }}>
          <Descriptions.Item label="Профиль">
            Схема сохраняется локально для повторного импорта этого типа файла.
          </Descriptions.Item>
        </Descriptions>
        <Space direction="vertical" style={{ width: '100%' }}>
          {fields.map(([key, label, required]) => (
            <Space key={key} style={{ width: '100%' }}>
              <Tag style={{ width: 190 }}>{label}{required ? ' *' : ''}</Tag>
              <Select
                allowClear
                placeholder="Выберите колонку"
                value={mapping[key]}
                onChange={(value) => setMapping((current) => ({ ...current, [key]: value ?? '' }))}
                options={headers.map((header) => ({ value: header, label: header }))}
                style={{ minWidth: 300 }}
              />
            </Space>
          ))}
        </Space>
        <Table
          size="small"
          style={{ marginTop: 20 }}
          pagination={false}
          scroll={{ x: 'max-content' }}
          dataSource={previewRows.map((row, index) => ({ ...row, key: index }))}
          columns={fields.map(([key, label]) => ({
            title: label,
            dataIndex: key,
            key,
          }))}
        />
      </Modal>
    </Card>
  );
}

function UniversitiesTab() {
  const { message } = AntApp.useApp();
  const role = useRole();
  const screens = Grid.useBreakpoint();
  const [rows, setRows] = useState<University[]>([]);
  const [name, setName] = useState('');
  const [city, setCity] = useState('');
  const [loading, setLoading] = useState(false);
  const [loadingRows, setLoadingRows] = useState(true);
  const [loadError, setLoadError] = useState(false);

  const load = async () => {
    setLoadingRows(true);
    setLoadError(false);
    try {
      setRows(await listUniversities());
    } catch (e) {
      setLoadError(true);
      message.error(errorMessage(e));
    } finally {
      setLoadingRows(false);
    }
  };
  useEffect(() => {
    void load();
  }, []);

  const add = async () => {
    if (!name.trim()) return;
    setLoading(true);
    try {
      await createUniversity({ name: name.trim(), city: city.trim() || null });
      setName('');
      setCity('');
      message.success('Вуз добавлен');
      load();
    } catch (e) {
      message.error(errorMessage(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Space direction="vertical" size={12} style={{ width: '100%' }}>
      {role !== 'user' && (
        <Space wrap className="responsive-form">
          <Input
            id="university-name"
            name="university_name"
            placeholder="Название вуза"
            value={name}
            onChange={(e) => setName(e.target.value)}
            style={{ width: 260 }}
            autoComplete="off"
          />
          <Input
            id="university-city"
            name="city"
            placeholder="Город"
            value={city}
            onChange={(e) => setCity(e.target.value)}
            style={{ width: 160 }}
            autoComplete="off"
          />
          <Button type="primary" onClick={add} loading={loading}>
            Добавить
          </Button>
        </Space>
      )}
      {loadingRows ? (
        <Spin tip="Загрузка вузов..." />
      ) : loadError ? (
        <Empty description="Не удалось загрузить вузы" />
      ) : rows.length === 0 ? (
        <Empty description="Вузов пока нет" />
      ) : (
        <div className="table-wrapper">
          <Table<University>
            rowKey="id"
            dataSource={rows}
            size={screens.md ? 'middle' : 'small'}
            scroll={{ x: 'max-content' }}
            pagination={{ pageSize: 10 }}
            columns={[
              { title: 'Название', dataIndex: 'name' },
              { title: 'Город', dataIndex: 'city', width: 140 },
              { title: 'Контакт', dataIndex: 'contact_person', width: 180 },
              role !== 'user' ? {
                title: '',
                width: 90,
                render: (_, r) => (
                  <Popconfirm
                    title="Удалить вуз?"
                    onConfirm={() =>
                      deleteUniversity(r.id)
                        .then(load)
                        .catch((e) => message.error(errorMessage(e)))
                    }
                  >
                    <Button type="text" size="small" danger>
                      Удалить
                    </Button>
                  </Popconfirm>
                ),
              } : { title: '', width: 0, render: () => null },
            ]}
          />
        </div>
      )}
    </Space>
  );
}

function DirectionsTab() {
  const { message } = AntApp.useApp();
  const role = useRole();
  const screens = Grid.useBreakpoint();
  const [rows, setRows] = useState<ITDirection[]>([]);
  const [name, setName] = useState('');
  const [loadingRows, setLoadingRows] = useState(true);
  const [loadError, setLoadError] = useState(false);

  const load = async () => {
    setLoadingRows(true);
    setLoadError(false);
    try {
      setRows(await listDirections());
    } catch (e) {
      setLoadError(true);
      message.error(errorMessage(e));
    } finally {
      setLoadingRows(false);
    }
  };
  useEffect(() => {
    void load();
  }, []);

  const add = async () => {
    if (!name.trim()) return;
    try {
      await createDirection(name.trim());
      setName('');
      message.success('Направление добавлено');
      load();
    } catch (e) {
      message.error(errorMessage(e));
    }
  };

  return (
    <Space direction="vertical" size={12} style={{ width: '100%' }}>
      {role !== 'user' && (
        <Space className="responsive-form">
          <Input
            id="direction-name"
            name="direction_name"
            placeholder="Название направления"
            value={name}
            onChange={(e) => setName(e.target.value)}
            style={{ width: 260 }}
            onPressEnter={add}
            autoComplete="off"
          />
          <Button type="primary" onClick={add}>
            Добавить
          </Button>
        </Space>
      )}
      {loadingRows ? (
        <Spin tip="Загрузка направлений..." />
      ) : loadError ? (
        <Empty description="Не удалось загрузить направления" />
      ) : rows.length === 0 ? (
        <Empty description="Направлений пока нет" />
      ) : (
        <div className="table-wrapper">
          <Table<ITDirection>
            rowKey="id"
            dataSource={rows}
            size={screens.md ? 'middle' : 'small'}
            scroll={{ x: 'max-content' }}
            pagination={false}
            columns={[
              { title: 'Направление', dataIndex: 'name' },
              role !== 'user' ? {
                title: '',
                width: 90,
                render: (_, r) => (
                  <Popconfirm
                    title="Удалить направление?"
                    description="Связанные продукты также будут удалены"
                    onConfirm={() =>
                      deleteDirection(r.id)
                        .then(load)
                        .catch((e) => message.error(errorMessage(e)))
                    }
                  >
                    <Button type="text" size="small" danger>
                      Удалить
                    </Button>
                  </Popconfirm>
                ),
              } : { title: '', width: 0, render: () => null },
            ]}
          />
        </div>
      )}
    </Space>
  );
}

function ProductsTab() {
  const { message } = AntApp.useApp();
  const role = useRole();
  const screens = Grid.useBreakpoint();
  const [rows, setRows] = useState<ITProduct[]>([]);
  const [directions, setDirections] = useState<ITDirection[]>([]);
  const [name, setName] = useState('');
  const [directionId, setDirectionId] = useState<number | undefined>();
  const [loadingRows, setLoadingRows] = useState(true);
  const [loadError, setLoadError] = useState(false);

  const load = async () => {
    setLoadingRows(true);
    setLoadError(false);
    try {
      const [products, availableDirections] = await Promise.all([
        listProducts(),
        listDirections(),
      ]);
      setRows(products);
      setDirections(availableDirections);
    } catch (e) {
      setLoadError(true);
      message.error(errorMessage(e));
    } finally {
      setLoadingRows(false);
    }
  };
  useEffect(() => {
    void load();
  }, []);

  const add = async () => {
    if (!name.trim()) return;
    try {
      await createProduct({
        name: name.trim(),
        direction_id: directionId ?? null,
      });
      setName('');
      setDirectionId(undefined);
      message.success('Продукт добавлен');
      load();
    } catch (e) {
      message.error(errorMessage(e));
    }
  };

  return (
    <Space direction="vertical" size={12} style={{ width: '100%' }}>
      {role !== 'user' && (
        <Space wrap className="responsive-form">
          <Input
            id="product-name"
            name="product_name"
            placeholder="Название продукта"
            value={name}
            onChange={(e) => setName(e.target.value)}
            style={{ width: 220 }}
            autoComplete="off"
          />
          <Select
            id="product-direction"
            placeholder="Направление"
            allowClear
            style={{ width: 220 }}
            value={directionId}
            onChange={setDirectionId}
            options={directions.map((d) => ({ value: d.id, label: d.name }))}
          />
          <Button type="primary" onClick={add}>
            Добавить
          </Button>
        </Space>
      )}
      {loadingRows ? (
        <Spin tip="Загрузка продуктов..." />
      ) : loadError ? (
        <Empty description="Не удалось загрузить продукты" />
      ) : rows.length === 0 ? (
        <Empty description="Продуктов пока нет" />
      ) : (
        <div className="table-wrapper">
          <Table<ITProduct>
            rowKey="id"
            dataSource={rows}
            size={screens.md ? 'middle' : 'small'}
            scroll={{ x: 'max-content' }}
            pagination={false}
            columns={[
              { title: 'Продукт', dataIndex: 'name' },
              { title: 'Направление', dataIndex: 'direction_name', width: 240 },
              role !== 'user' ? {
                title: '',
                width: 90,
                render: (_, r) => (
                  <Popconfirm
                    title="Удалить продукт?"
                    onConfirm={() =>
                      deleteProduct(r.id)
                        .then(load)
                        .catch((e) => message.error(errorMessage(e)))
                    }
                  >
                    <Button type="text" size="small" danger>
                      Удалить
                    </Button>
                  </Popconfirm>
                ),
              } : { title: '', width: 0, render: () => null },
            ]}
          />
        </div>
      )}
    </Space>
  );
}
