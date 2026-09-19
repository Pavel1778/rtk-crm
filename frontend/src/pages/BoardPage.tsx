import { useEffect, useState } from 'react';

import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useDraggable,
  useDroppable,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
} from '@dnd-kit/core';
import {
  App as AntApp,
  Badge,
  Button,
  Card,
  Col,
  Empty,
  Grid,
  Input,
  Row,
  Select,
  Space,
  Spin,
  Tag,
  Typography,
} from 'antd';
import {
  CalendarOutlined,
  CloseOutlined,
  CommentOutlined,
  PlusOutlined,
  ReloadOutlined,
} from '@ant-design/icons';

import { errorMessage } from '../api/client';
import {
  createInteraction,
  getBoard,
  listProducts,
  listUniversities,
  moveInteraction,
} from '../api/endpoints';
import type {
  BoardResponse,
  InteractionCard,
  ITProduct,
  University,
  WorkflowStage,
} from '../types';
import { useRole } from '../stores/authStore';
import InteractionDrawer from '../components/interaction/InteractionDrawer';
import MobileStageFilter from '../components/kanban/MobileStageFilter';

interface DragData {
  card: InteractionCard;
  stageId: number;
}

function KanbanCard({
  card,
  onOpen,
}: {
  card: InteractionCard;
  onOpen: (card: InteractionCard) => void;
}) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: card.id,
    data: { card } satisfies Pick<DragData, 'card'>,
  });

  return (
    <div
      ref={setNodeRef}
      {...listeners}
      {...attributes}
      onClick={() => onOpen(card)}
      style={{
        opacity: isDragging ? 0.4 : 1,
        cursor: 'grab',
        touchAction: 'none',
      }}
    >
      <Card size="small" style={{ border: '1px solid #E0E0E5' }}>
        <Typography.Text strong style={{ fontSize: 13 }}>
          {card.university_name ?? 'Без вуза'}
        </Typography.Text>
        <div style={{ marginTop: 4 }}>
          {card.product_name ? (
            <Tag color="purple" style={{ marginInlineEnd: 4 }}>
              {card.product_name}
            </Tag>
          ) : null}
          {card.contract_number ? (
            <Tag style={{ marginInlineEnd: 4 }}>{card.contract_number}</Tag>
          ) : null}
        </div>
        <Space size={12} style={{ marginTop: 6 }}>
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            <CalendarOutlined /> {card.university_specialist ?? '—'}
          </Typography.Text>
        </Space>
        <div style={{ marginTop: 6 }}>
          <Space size={8}>
            <Badge
              count={card.actions_open}
              showZero
              color={card.actions_open > 0 ? '#F5A623' : '#00AC43'}
              title="Открытые задачи"
            />
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              <CommentOutlined /> {card.comments_count}
            </Typography.Text>
          </Space>
        </div>
      </Card>
    </div>
  );
}

function KanbanColumn({
  stage,
  cards,
  onOpen,
}: {
  stage: WorkflowStage;
  cards: InteractionCard[];
  onOpen: (card: InteractionCard) => void;
}) {
  const { setNodeRef, isOver } = useDroppable({
    id: `stage-${stage.id}`,
    data: { stageId: stage.id },
  });

  return (
    <div
      ref={setNodeRef}
      style={{
        width: 280,
        flexShrink: 0,
        background: isOver ? '#F3E5F5' : '#F5F5F7',
        border: '1px solid #EEEEF2',
        borderRadius: 12,
        padding: 12,
        display: 'flex',
        flexDirection: 'column',
        gap: 8,
        maxHeight: 'calc(100vh - 180px)',
        transition: 'background 0.2s',
      }}
    >
      <Space align="center" style={{ justifyContent: 'space-between', width: '100%' }}>
        <Space size={8}>
          <span
            style={{
              width: 8,
              height: 8,
              borderRadius: 4,
              background: stage.color ?? '#6E41F2',
              display: 'inline-block',
            }}
          />
          <Typography.Text strong>{stage.name}</Typography.Text>
          <Badge count={cards.length} color="#6E41F2" showZero />
        </Space>
      </Space>
      <div style={{ overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 8 }}>
        {cards.map((card) => (
          <KanbanCard key={card.id} card={card} onOpen={onOpen} />
        ))}
        {cards.length === 0 && (
          <Typography.Text
            type="secondary"
            style={{ textAlign: 'center', padding: 16, fontSize: 12 }}
          >
            Нет взаимодействий
          </Typography.Text>
        )}
      </div>
    </div>
  );
}

export default function BoardPage() {
  const { message } = AntApp.useApp();
  const screens = Grid.useBreakpoint();
  const role = useRole();
  const [data, setData] = useState<BoardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [productFilter, setProductFilter] = useState<number | undefined>();
  const [products, setProducts] = useState<ITProduct[]>([]);
  const [activeCard, setActiveCard] = useState<InteractionCard | null>(null);
  const [mobileStage, setMobileStage] = useState<number | undefined>();
  const [openCard, setOpenCard] = useState<InteractionCard | null>(null);
  const [creating, setCreating] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      setData(await getBoard({ search: search || undefined, product_id: productFilter }));
    } catch (error) {
      message.error(errorMessage(error, 'Не удалось загрузить доску'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
    void listProducts().then(setProducts).catch(() => undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } })
  );

  const onDragStart = (event: DragStartEvent) => {
    const card = (event.active.data.current as { card: InteractionCard }).card;
    setActiveCard(card);
  };

  const onDragEnd = async (event: DragEndEvent) => {
    setActiveCard(null);
    const over = event.over;
    if (!over) return;
    const stageId = (over.data.current as { stageId: number }).stageId;
    const card = (event.active.data.current as { card: InteractionCard }).card;
    if (card.stage_id === stageId) return;
    try {
      await moveInteraction(card.id, stageId);
      await load();
      message.success('Взаимодействие перемещено');
    } catch (error) {
      message.error(errorMessage(error, 'Не удалось переместить'));
    }
  };

  const columns = data?.columns ?? [];
  const visibleColumns =
    !screens.md && mobileStage !== undefined
      ? columns.filter((c) => c.stage.id === mobileStage)
      : columns;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <Row gutter={[12, 12]} align="middle">
        <Col flex="auto">
          <Space wrap size={12}>
            <Input.Search
              placeholder="Поиск по вузу"
              allowClear
              style={{ width: 220 }}
              onSearch={(value) => {
                setSearch(value);
                setTimeout(load, 0);
              }}
            />
            <Select
              placeholder="Продукт"
              allowClear
              style={{ width: 180 }}
              value={productFilter}
              onChange={(value) => {
                setProductFilter(value);
                setTimeout(load, 0);
              }}
              options={products.map((p) => ({ value: p.id, label: p.name }))}
            />
            <Button icon={<ReloadOutlined />} onClick={load}>
              Обновить
            </Button>
          </Space>
        </Col>
        <Col>
          <Space>
            <MobileStageFilter
              columns={columns}
              value={mobileStage}
              onChange={setMobileStage}
            />
            {role !== 'user' && (
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => setCreating(true)}
              >
                Создать взаимодействие
              </Button>
            )}
          </Space>
        </Col>
      </Row>

      {loading && (
        <div style={{ textAlign: 'center', padding: 48 }}>
          <Spin size="large" />
        </div>
      )}

      {!loading && columns.length === 0 && (
        <Empty description="Воркфлоу не настроен. Добавьте этапы в разделе «Настройки»." />
      )}

      {!loading && columns.length > 0 && (
        <DndContext sensors={sensors} onDragStart={onDragStart} onDragEnd={onDragEnd}>
          <div
            style={{
              display: 'flex',
              gap: 12,
              overflowX: 'auto',
              paddingBottom: 8,
              alignItems: 'flex-start',
            }}
          >
            {visibleColumns.map((column) => (
              <KanbanColumn
                key={column.stage.id}
                stage={column.stage}
                cards={column.interactions}
                onOpen={setOpenCard}
              />
            ))}
          </div>
          <DragOverlay>
            {activeCard && (
              <Card size="small" style={{ width: 260, border: '1px solid #6E41F2' }}>
                <Typography.Text strong>
                  {activeCard.university_name ?? 'Без вуза'}
                </Typography.Text>
              </Card>
            )}
          </DragOverlay>
        </DndContext>
      )}

      <CreateInteractionModal
        open={creating}
        onClose={() => setCreating(false)}
        onCreated={async () => {
          setCreating(false);
          await load();
        }}
      />

      <InteractionDrawer
        card={openCard}
        onClose={() => setOpenCard(null)}
        onChanged={load}
      />
    </div>
  );
}

function CreateInteractionModal({
  open,
  onClose,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
}) {
  const { message } = AntApp.useApp();
  const [universities, setUniversities] = useState<University[]>([]);
  const [products, setProducts] = useState<ITProduct[]>([]);
  const [universityId, setUniversityId] = useState<number | null>(null);
  const [productId, setProductId] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) {
      void listUniversities().then(setUniversities).catch(() => undefined);
      void listProducts().then(setProducts).catch(() => undefined);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const submit = async () => {
    if (!universityId) {
      message.warning('Выберите вуз');
      return;
    }
    setSaving(true);
    try {
      await createInteraction({
        university_id: universityId,
        product_id: productId,
      });
      message.success('Взаимодействие создано');
      setUniversityId(null);
      setProductId(null);
      onCreated();
    } catch (error) {
      message.error(errorMessage(error, 'Не удалось создать'));
    } finally {
      setSaving(false);
    }
  };

  if (!open) {
    return null;
  }

  return (
    <Card
      title={
        <Space>
          <span>Новое взаимодействие</span>
          <Button
            type="text"
            size="small"
            icon={<CloseOutlined />}
            onClick={onClose}
          />
        </Space>
      }
      style={{
        position: 'fixed',
        top: 96,
        right: 24,
        width: 340,
        zIndex: 1000,
        boxShadow: '0 8px 24px rgba(28, 29, 34, 0.12)',
      }}
    >
      <Space direction="vertical" size={12} style={{ width: '100%' }}>
        <Select
          showSearch
          placeholder="Вуз"
          style={{ width: '100%' }}
          value={universityId}
          onChange={setUniversityId}
          optionFilterProp="label"
          options={universities.map((u) => ({ value: u.id, label: u.name }))}
        />
        <Select
          showSearch
          allowClear
          placeholder="Продукт"
          style={{ width: '100%' }}
          value={productId}
          onChange={(value) => setProductId(value ?? null)}
          optionFilterProp="label"
          options={products.map((p) => ({ value: p.id, label: p.name }))}
        />
        <Button type="primary" block loading={saving} onClick={submit}>
          Создать
        </Button>
      </Space>
    </Card>
  );
}
