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
  Grid,
  Input,
  Row,
  Segmented,
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
  listUsers,
  moveInteraction,
} from '../api/endpoints';
import type {
  BoardResponse,
  InteractionCard,
  ITProduct,
  University,
  User,
  WorkflowScope,
  WorkflowStage,
} from '../types';
import { useRole } from '../stores/authStore';
import InteractionDrawer from '../components/interaction/InteractionDrawer';
import DateRangeFilter, { type DateRangeValue } from '../components/DateRangeFilter';
import MobileStageFilter from '../components/kanban/MobileStageFilter';
import EmptyState from '../components/EmptyState';

const FILTER_DEBOUNCE_MS = 300;

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
      <Card size="small" style={{ border: '1px solid var(--atmr-border-default)' }}>
        <Typography.Text strong style={{ fontSize: 13 }}>
          {card.university_name ?? 'Без вуза'}
        </Typography.Text>
        <div style={{ marginTop: 4 }}>
          {card.product_name ? (
            <Tag className="tag-accent" style={{ marginInlineEnd: 4 }}>
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
          {card.assigned_kam_name && (
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              КАМ: {card.assigned_kam_name}
            </Typography.Text>
          )}
        </Space>
        <div style={{ marginTop: 6 }}>
          <Space size={8}>
            <Badge
              count={card.actions_open}
              showZero
              color={card.actions_open > 0 ? 'var(--atmr-badge-open-bg)' : 'var(--atmr-badge-done-bg)'}
              style={{ color: 'var(--atmr-badge-count-fg)' }}
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
      className="kanban-column"
      style={{
        width: 280,
        flexShrink: 0,
                background: isOver ? 'var(--atmr-bg-dropzone)' : 'var(--atmr-bg-soft)',
                border: '1px solid var(--atmr-border-soft)',
                borderRight: '2px solid var(--atmr-border-default)',
        borderRadius: 12,
        padding: 12,
        display: 'flex',
        flexDirection: 'column',
        gap: 8,
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
              background: stage.color ?? 'var(--atmr-accent-default)',
              display: 'inline-block',
            }}
          />
          <Typography.Text strong>{stage.name}</Typography.Text>
          <Badge
            count={cards.length}
            color="var(--atmr-accent-default)"
            style={{ color: 'var(--atmr-on-accent)' }}
            showZero
          />
        </Space>
      </Space>
      <div style={{ overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 8 }}>
        {cards.map((card) => (
          <KanbanCard key={card.id} card={card} onOpen={onOpen} />
        ))}
        {cards.length === 0 && (
          <div className="empty-column">
            <Typography.Text
              type="secondary"
              style={{ textAlign: 'center', padding: 16, fontSize: 12 }}
            >
              Нет взаимодействий
            </Typography.Text>
          </div>
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
  const [scope, setScope] = useState<WorkflowScope>('b2b');
  const [productFilter, setProductFilter] = useState<number | undefined>();
  const [dates, setDates] = useState<DateRangeValue>({});
  const [products, setProducts] = useState<ITProduct[]>([]);
  const [activeCard, setActiveCard] = useState<InteractionCard | null>(null);
  const [mobileStage, setMobileStage] = useState<number | undefined>();
  const [openCard, setOpenCard] = useState<InteractionCard | null>(null);
  const [creating, setCreating] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      setData(
        await getBoard({
          search: search || undefined,
          product_id: productFilter,
          scope,
          date_from: dates.date_from,
          date_to: dates.date_to,
        })
      );
    } catch (error) {
      message.error(errorMessage(error, 'Не удалось загрузить доску'));
    } finally {
      setLoading(false);
    }
  };

  // Раньше фильтры применялись через setTimeout(load, 0): замыкание load
  // захватывало старое значение search/productFilter, поэтому запрос уходил
  // без фильтров. Эффект с зависимостями пересоздаёт load с актуальными
  // значениями; debounce защищает от лишних запросов при быстрой смене.
  useEffect(() => {
    const timer = setTimeout(() => {
      void load();
    }, FILTER_DEBOUNCE_MS);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scope, search, productFilter, dates.date_from, dates.date_to]);

  useEffect(() => {
    void listProducts().then(setProducts).catch(() => undefined);
  }, []);

  // На телефоне показываем первый этап, а не «все»: одна колонка читается
  // лучше длинной простыни. Флаг touched не даёт вернуть выбор обратно,
  // если пользователь сам выбрал «Все этапы».
  const [stageTouched, setStageTouched] = useState(false);
  useEffect(() => {
    if (
      !screens.md &&
      !stageTouched &&
      (data?.columns.length ?? 0) > 0
    ) {
      setMobileStage(data!.columns[0].stage.id);
    }
  }, [screens.md, stageTouched, data]);

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
    <div className="page-container">
      <div className="page-header">
        <h1>Доска взаимодействий</h1>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => setCreating(true)}
          disabled={role === 'user'}
        >
          Создать взаимодействие
        </Button>
      </div>
      
      <div className="page-filters">
        <Row gutter={[12, 12]} align="middle" style={{ width: '100%' }}>
          <Col>
            <Segmented
              id="board-scope"
              value={scope}
              onChange={(value) => {
                setScope(value as WorkflowScope);
                setMobileStage(undefined);
              }}
              options={[
                { value: 'b2b', label: 'B2B' },
                { value: 'b2c', label: 'B2C' },
              ]}
            />
          </Col>
          <Col flex="auto" className="board-filter-search">
            <Input.Search
              id="board-search"
              name="search"
              placeholder="Поиск по вузу"
              allowClear
              className="board-search-input"
              autoComplete="off"
              onSearch={setSearch}
            />
          </Col>
          <Col className="board-filter-product">
            <Select
              id="board-product-filter"
              placeholder="Продукт"
              allowClear
              className="board-product-select"
              value={productFilter}
              onChange={setProductFilter}
              options={products.map((p) => ({ value: p.id, label: p.name }))}
            />
          </Col>
          <Col className="board-filter-dates">
            <DateRangeFilter
              id="board-date-range"
              value={dates}
              onChange={setDates}
              style={{ minWidth: 240 }}
            />
          </Col>
          {!screens.md && (
            <Col flex="auto" style={{ minWidth: 0 }}>
              <MobileStageFilter
                columns={columns}
                value={mobileStage}
                onChange={(next) => {
                  setStageTouched(true);
                  setMobileStage(next);
                }}
              />
            </Col>
          )}
          <Col>
            <Button icon={<ReloadOutlined />} onClick={load}>
              Обновить
            </Button>
          </Col>
        </Row>
      </div>

      {loading && (
        <div style={{ textAlign: 'center', padding: 48 }}>
          <Spin size="large" />
        </div>
      )}

      {!loading && columns.length === 0 && (
        <EmptyState 
          title="Воркфлоу не настроен"
          description="Добавьте этапы в разделе «Настройки»"
        />
      )}

      {!loading && columns.length > 0 && (
        <div className="page-content">
          <DndContext sensors={sensors} onDragStart={onDragStart} onDragEnd={onDragEnd}>
            <div className="scroll-box">
              <div
                className="kanban-board"
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
            </div>
            <DragOverlay>
              {activeCard && (
                <Card size="small" style={{ width: 260, border: '1px solid var(--atmr-accent-default)' }}>
                  <Typography.Text strong>
                    {activeCard.university_name ?? 'Без вуза'}
                  </Typography.Text>
                </Card>
              )}
            </DragOverlay>
          </DndContext>
        </div>
      )}

      <CreateInteractionModal
        open={creating}
        scope={scope}
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
  scope,
  onClose,
  onCreated,
}: {
  open: boolean;
  scope: WorkflowScope;
  onClose: () => void;
  onCreated: () => void;
}) {
  const { message } = AntApp.useApp();
  const role = useRole();
  const [universities, setUniversities] = useState<University[]>([]);
  const [products, setProducts] = useState<ITProduct[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [universityId, setUniversityId] = useState<number | null>(null);
  const [productId, setProductId] = useState<number | null>(null);
  const [kamId, setKamId] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);

  const canAssign = role === 'admin' || role === 'manager';

  useEffect(() => {
    if (open) {
      void listUniversities().then(setUniversities).catch(() => undefined);
      void listProducts().then(setProducts).catch(() => undefined);
      if (canAssign) {
        void listUsers().then(setUsers).catch(() => undefined);
      }
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
        assigned_kam_id: kamId,
        scope,
      });
      message.success('Взаимодействие создано');
      setUniversityId(null);
      setProductId(null);
      setKamId(null);
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
        boxShadow: 'var(--atmr-shadow-popover)',
      }}
    >
      <Space direction="vertical" size={12} style={{ width: '100%' }}>
        <Select
          id="drawer-university"
          showSearch
          placeholder="Вуз"
          style={{ width: '100%' }}
          value={universityId}
          onChange={setUniversityId}
          optionFilterProp="label"
          options={universities.map((u) => ({ value: u.id, label: u.name }))}
        />
        <Select
          id="drawer-product"
          showSearch
          allowClear
          placeholder="Продукт"
          style={{ width: '100%' }}
          value={productId}
          onChange={(value) => setProductId(value ?? null)}
          optionFilterProp="label"
          options={products.map((p) => ({ value: p.id, label: p.name }))}
        />
        {canAssign && (
          <Select
            id="drawer-kam"
            showSearch
            allowClear
            placeholder="Ответственный КАМ"
            style={{ width: '100%' }}
            value={kamId}
            onChange={(value) => setKamId(value ?? null)}
            optionFilterProp="label"
            options={users
              .filter((u) => u.role === 'user')
              .map((u) => ({ value: u.id, label: u.full_name }))}
          />
        )}
        <Button type="primary" block loading={saving} onClick={submit}>
          Создать
        </Button>
      </Space>
    </Card>
  );
}
