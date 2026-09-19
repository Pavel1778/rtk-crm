import { useEffect, useState } from 'react';
import {
  App as AntApp,
  Button,
  Card,
  Input,
  Popconfirm,
  Select,
  Space,
  Table,
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
} from '../api/endpoints';
import type { ITDirection, ITProduct, University } from '../types';

export default function DirectoryPage() {
  return (
    <Card style={{ border: '1px solid #EEEEF2' }}>
      <Tabs
        items={[
          { key: 'universities', label: 'Вузы', children: <UniversitiesTab /> },
          { key: 'products', label: 'Продукты', children: <ProductsTab /> },
          { key: 'directions', label: 'Направления', children: <DirectionsTab /> },
        ]}
      />
    </Card>
  );
}

function UniversitiesTab() {
  const { message } = AntApp.useApp();
  const [rows, setRows] = useState<University[]>([]);
  const [name, setName] = useState('');
  const [city, setCity] = useState('');
  const [loading, setLoading] = useState(false);

  const load = () => {
    listUniversities()
      .then(setRows)
      .catch((e) => message.error(errorMessage(e)));
  };
  useEffect(load, []);

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
      <Space wrap>
        <Input
          placeholder="Название вуза"
          value={name}
          onChange={(e) => setName(e.target.value)}
          style={{ width: 260 }}
        />
        <Input
          placeholder="Город"
          value={city}
          onChange={(e) => setCity(e.target.value)}
          style={{ width: 160 }}
        />
        <Button type="primary" onClick={add} loading={loading}>
          Добавить
        </Button>
      </Space>
      <Table<University>
        rowKey="id"
        dataSource={rows}
        size="small"
        pagination={{ pageSize: 10 }}
        columns={[
          { title: 'Название', dataIndex: 'name' },
          { title: 'Город', dataIndex: 'city', width: 140 },
          { title: 'Контакт', dataIndex: 'contact_person', width: 180 },
          {
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
          },
        ]}
      />
    </Space>
  );
}

function DirectionsTab() {
  const { message } = AntApp.useApp();
  const [rows, setRows] = useState<ITDirection[]>([]);
  const [name, setName] = useState('');

  const load = () => {
    listDirections()
      .then(setRows)
      .catch((e) => message.error(errorMessage(e)));
  };
  useEffect(load, []);

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
      <Space>
        <Input
          placeholder="Название направления"
          value={name}
          onChange={(e) => setName(e.target.value)}
          style={{ width: 260 }}
          onPressEnter={add}
        />
        <Button type="primary" onClick={add}>
          Добавить
        </Button>
      </Space>
      <Table<ITDirection>
        rowKey="id"
        dataSource={rows}
        size="small"
        pagination={false}
        columns={[
          { title: 'Направление', dataIndex: 'name' },
          {
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
          },
        ]}
      />
    </Space>
  );
}

function ProductsTab() {
  const { message } = AntApp.useApp();
  const [rows, setRows] = useState<ITProduct[]>([]);
  const [directions, setDirections] = useState<ITDirection[]>([]);
  const [name, setName] = useState('');
  const [directionId, setDirectionId] = useState<number | undefined>();

  const load = () => {
    listProducts()
      .then(setRows)
      .catch((e) => message.error(errorMessage(e)));
    listDirections()
      .then(setDirections)
      .catch(() => undefined);
  };
  useEffect(load, []);

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
      <Space wrap>
        <Input
          placeholder="Название продукта"
          value={name}
          onChange={(e) => setName(e.target.value)}
          style={{ width: 220 }}
        />
        <Select
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
      <Table<ITProduct>
        rowKey="id"
        dataSource={rows}
        size="small"
        pagination={false}
        columns={[
          { title: 'Продукт', dataIndex: 'name' },
          { title: 'Направление', dataIndex: 'direction_name', width: 240 },
          {
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
          },
        ]}
      />
    </Space>
  );
}
