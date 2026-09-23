import type { ReactNode } from 'react';
import { Button, Popconfirm, Space, Switch, Tag, Tooltip } from 'antd';
import { DeleteOutlined, HolderOutlined } from '@ant-design/icons';
import {
  DndContext,
  closestCenter,
  type DragEndEvent,
} from '@dnd-kit/core';
import {
  SortableContext,
  arrayMove,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

import type { WorkflowStage } from '../../types';
import { useDevice } from '../../hooks/useDevice';

interface StageTableProps {
  stages: WorkflowStage[];
  /** Включает перетаскивание строк для смены порядка этапов. */
  sortable?: boolean;
  onReorder?: (stages: WorkflowStage[]) => void;
  onEdit?: (stage: WorkflowStage) => void;
  onDelete?: (stage: WorkflowStage) => void;
  onToggle?: (stage: WorkflowStage, next: boolean) => void;
  togglingId?: number | null;
  /** Кастомный рендер названия (например, инлайн-редактирование). */
  renderName?: (stage: WorkflowStage) => ReactNode;
}

function StageColorDot({ color }: { color: string | null }) {
  return (
    <span
      className="stage-table__dot"
      style={{ background: color ?? 'var(--atmr-accent-default)' }}
    />
  );
}

function StageActions({
  stage,
  onEdit,
  onDelete,
  onToggle,
  togglingId,
}: Pick<StageTableProps, 'onEdit' | 'onDelete' | 'onToggle' | 'togglingId'> & {
  stage: WorkflowStage;
}) {
  return (
    <Space size={8} align="center" wrap>
      {onToggle && (
        <Tooltip title={stage.is_active ? 'Выключить этап' : 'Включить этап'}>
          <Switch
            checked={stage.is_active}
            loading={togglingId === stage.id}
            onChange={(next) => onToggle(stage, next)}
            aria-label={`Этап ${stage.name}: ${stage.is_active ? 'активен' : 'неактивен'}`}
          />
        </Tooltip>
      )}
      {onEdit && (
        <Button type="link" size="small" onClick={() => onEdit(stage)}>
          Редактировать
        </Button>
      )}
      {onDelete && (
        <Popconfirm
          title="Удалить этап?"
          description={
            stage.interaction_count > 0
              ? `На этапе ${stage.interaction_count} активных взаимодействий — потребуется перенос.`
              : undefined
          }
          okText="Продолжить"
          cancelText="Отмена"
          onConfirm={() => onDelete(stage)}
        >
          <Tooltip title="Удалить этап">
            <Button
              type="text"
              size="small"
              danger
              icon={<DeleteOutlined />}
              aria-label={`Удалить этап ${stage.name}`}
            />
          </Tooltip>
        </Popconfirm>
      )}
    </Space>
  );
}

function rowClassName(stage: WorkflowStage) {
  return stage.is_active ? '' : 'stage-table__row--disabled';
}

function StageName({ stage, renderName }: { stage: WorkflowStage; renderName?: StageTableProps['renderName'] }) {
  return (
    <span className="stage-table__name">
      <StageColorDot color={stage.color} />
      {renderName ? renderName(stage) : <span>{stage.name}</span>}
      {!stage.is_active && <Tag color="default">Неактивен</Tag>}
    </span>
  );
}

function SortableStageRow({
  stage,
  props,
}: {
  stage: WorkflowStage;
  props: StageTableProps;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: stage.id });

  return (
    <tr
      ref={setNodeRef}
      className={`stage-table__row ${rowClassName(stage)}`}
      style={{
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.5 : undefined,
      }}
    >
      <td className="stage-table__col-handle">
        <Button
          type="text"
          icon={<HolderOutlined />}
          size="small"
          className="stage-table__handle"
          aria-label={`Переместить этап ${stage.name}`}
          {...attributes}
          {...listeners}
        />
      </td>
      <td className="stage-table__col-order">{stage.order}</td>
      <td>
        <StageName stage={stage} renderName={props.renderName} />
      </td>
      <td>
        <Tag>{stage.code}</Tag>
      </td>
      <td className="stage-table__col-count">{stage.interaction_count}</td>
      <td>
        <StageActions stage={stage} {...props} />
      </td>
    </tr>
  );
}

function StaticStageRow({
  stage,
  props,
}: {
  stage: WorkflowStage;
  props: StageTableProps;
}) {
  return (
    <tr className={`stage-table__row ${rowClassName(stage)}`}>
      <td className="stage-table__col-handle" />
      <td className="stage-table__col-order">{stage.order}</td>
      <td>
        <StageName stage={stage} renderName={props.renderName} />
      </td>
      <td>
        <Tag>{stage.code}</Tag>
      </td>
      <td className="stage-table__col-count">{stage.interaction_count}</td>
      <td>
        <StageActions stage={stage} {...props} />
      </td>
    </tr>
  );
}

function StageCard({ stage, props }: { stage: WorkflowStage; props: StageTableProps }) {
  return (
    <div className={`stage-card ${rowClassName(stage)}`}>
      <div className="stage-card__head">
        <span className="stage-card__order">{stage.order}</span>
        <StageName stage={stage} renderName={props.renderName} />
      </div>
      <div className="stage-card__meta">
        <Tag>{stage.code}</Tag>
        <span className="stage-card__count">
          Взаимодействий: {stage.interaction_count}
        </span>
      </div>
      <div className="stage-card__actions">
        <StageActions stage={stage} {...props} />
      </div>
    </div>
  );
}

/** Единая таблица этапов workflow. На широких экранах это таблица,
 * на мобильных — набор карточек, чтобы не появлялся горизонтальный скролл. */
export default function StageTable(props: StageTableProps) {
  const { stages, sortable, onReorder } = props;
  const device = useDevice();
  const isMobile = device === 'mobile';

  if (isMobile) {
    return (
      <div className="stage-cards">
        {stages.map((stage) => (
          <StageCard key={stage.id} stage={stage} props={props} />
        ))}
      </div>
    );
  }

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id || !onReorder) return;
    const oldIndex = stages.findIndex((s) => s.id === active.id);
    const newIndex = stages.findIndex((s) => s.id === over.id);
    onReorder(
      arrayMove(stages, oldIndex, newIndex).map((s, idx) => ({ ...s, order: idx + 1 }))
    );
  };

  const body = (
    <table className="stage-table">
      <thead>
        <tr>
          {sortable && <th className="stage-table__col-handle" aria-label="Порядок перетаскиванием" />}
          <th className="stage-table__col-order">Порядок</th>
          <th>Этап</th>
          <th>Код</th>
          <th className="stage-table__col-count">Взаимодействий</th>
          <th>Действия</th>
        </tr>
      </thead>
      <tbody>
        {stages.map((stage) =>
          sortable ? (
            <SortableStageRow key={stage.id} stage={stage} props={props} />
          ) : (
            <StaticStageRow key={stage.id} stage={stage} props={props} />
          )
        )}
      </tbody>
    </table>
  );

  if (!sortable) return <div className="scroll-box">{body}</div>;

  return (
    <DndContext collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
      <SortableContext items={stages.map((s) => s.id)} strategy={verticalListSortingStrategy}>
        <div className="scroll-box">{body}</div>
      </SortableContext>
    </DndContext>
  );
}
