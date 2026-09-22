import { Button, Popconfirm, Space, Tag, Tooltip } from 'antd';
import { DeleteOutlined, HolderOutlined } from '@ant-design/icons';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import StageToggle from './StageToggle';

interface StageData {
  id: number;
  code: string;
  name: string;
  order: number;
  color: string | null;
  is_active: boolean;
  interaction_count: number;
}

interface SortableStageRowProps {
  stage: StageData;
  onEdit: (stage: StageData) => void;
  onDelete: (stage: StageData) => void;
  onDragStart?: () => void;
  onDragEnd?: () => void;
}

export default function SortableStageRow({
  stage,
  onEdit,
  onDelete,
  onDragStart,
  onDragEnd,
}: SortableStageRowProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: stage.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : undefined,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={
        stage.is_active
          ? 'sortable-stage-row'
          : 'sortable-stage-row workflow-row--disabled'
      }
      onMouseDown={onDragStart}
      onMouseUp={onDragEnd}
    >
      <Space size={12} style={{ width: '100%', alignItems: 'center', justifyContent: 'space-between' }}>
        <Space size={12} style={{ alignItems: 'center', flex: 1, minWidth: 0 }}>
          <Button
            type="text"
            icon={<HolderOutlined />}
            size="small"
            style={{ cursor: 'grab' }}
            {...attributes}
            {...listeners}
          />
          <span
            style={{
              width: 12,
              height: 12,
              borderRadius: 6,
              background: stage.color ?? '#6E41F2',
              display: 'inline-block',
              flexShrink: 0,
            }}
          />
          <span style={{ flex: 1, minWidth: 0 }}>{stage.name}</span>
          <Tag>{stage.code}</Tag>
          {!stage.is_active && <Tag color="default">Неактивен</Tag>}
        </Space>
        <Space size={12} style={{ alignItems: 'center', flexShrink: 0 }}>
          <span style={{ minWidth: 60, textAlign: 'center' }}>{stage.order}</span>
          <StageToggle stageId={stage.id} isActive={stage.is_active} />
          <Button type="link" size="small" onClick={() => onEdit(stage)}>
            Редактировать
          </Button>
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
              <Button type="text" size="small" danger icon={<DeleteOutlined />} />
            </Tooltip>
          </Popconfirm>
        </Space>
      </Space>
    </div>
  );
}
