import { App as AntApp, Button, Popconfirm, Space, Switch, Tag } from 'antd';
import { HolderOutlined } from '@ant-design/icons';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

interface SortableStageRowProps {
  stage: {
    id: number;
    code: string;
    name: string;
    order: number;
    color: string;
    is_active: boolean;
    interaction_count: number;
  };
  onEdit: (stage: typeof stage) => void;
  onDelete: (stage: typeof stage) => void;
  onToggle: (id: number, checked: boolean) => void;
  onDragStart?: () => void;
  onDragEnd?: () => void;
}

export default function SortableStageRow({
  stage,
  onEdit,
  onDelete,
  onToggle,
  onDragStart,
  onDragEnd,
}: SortableStageRowProps) {
  const { message } = AntApp.useApp();
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
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="sortable-stage-row"
      onMouseDown={onDragStart}
      onMouseUp={onDragEnd}
    >
      <Space size={12} style={{ width: '100%', alignItems: 'center' }}>
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
            background: stage.color,
            display: 'inline-block',
            flexShrink: 0,
          }}
        />
        <span style={{ flex: 1, minWidth: 0 }}>{stage.name}</span>
        <Tag>{stage.code}</Tag>
        <span style={{ minWidth: 60, textAlign: 'center' }}>{stage.order}</span>
        <Switch
          checked={stage.is_active}
          onChange={(checked) => onToggle(stage.id, checked)}
          size="small"
        />
        <Button type="link" size="small" onClick={() => onEdit(stage)}>
          Редактировать
        </Button>
        <Popconfirm
          title="Удалить этап?"
          disabled={stage.interaction_count > 0}
          onConfirm={() => onDelete(stage)}
        >
          <Button
            type="link"
            size="small"
            danger
            disabled={stage.interaction_count > 0}
          >
            Удалить
          </Button>
        </Popconfirm>
      </Space>
    </div>
  );
}
