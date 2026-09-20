import { App as AntApp, Button, Card, Space, Spin } from 'antd';
import { PlusOutlined, UndoOutlined } from '@ant-design/icons';
import { DndContext, closestCenter } from '@dnd-kit/core';
import { SortableContext, verticalListSortingStrategy, arrayMove } from '@dnd-kit/sortable';
import { useEffect, useState } from 'react';

import { errorMessage } from '../api/client';
import { createStage, deleteStage, listStages, updateStage } from '../api/endpoints';
import type { WorkflowStage } from '../types';
import { useRole } from '../stores/authStore';
import StageEditor from '../components/workflow/StageEditor';
import DeleteStageModal from '../components/workflow/DeleteStageModal';
import SortableStageRow from '../components/workflow/SortableStageRow';
import EmptyState from '../components/EmptyState';

export default function WorkflowPage() {
  const { message } = AntApp.useApp();
  const role = useRole();
  const [stages, setStages] = useState<WorkflowStage[]>([]);
  const [loading, setLoading] = useState(true);
  const [editorOpen, setEditorOpen] = useState(false);
  const [editingStage, setEditingStage] = useState<WorkflowStage | undefined>();
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [deletingStage, setDeletingStage] = useState<WorkflowStage | undefined>();

  if (role !== 'admin') {
    return (
      <Card>
        <p>Доступ запрещён. Только администраторы могут редактировать этапы воркфлоу.</p>
      </Card>
    );
  }

  const load = () => {
    setLoading(true);
    listStages()
      .then(setStages)
      .catch((e) => message.error(errorMessage(e)))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const handleSaveStage = async (data: { code: string; name: string; order: number; color: string }) => {
    try {
      if (editingStage?.id) {
        await updateStage(editingStage.id, data);
        message.success('Этап обновлён');
      } else {
        await createStage(data);
        message.success('Этап создан');
      }
      setEditorOpen(false);
      setEditingStage(undefined);
      load();
    } catch (e) {
      message.error(errorMessage(e));
    }
  };

  const handleEdit = (stage: WorkflowStage) => {
    setEditingStage(stage);
    setEditorOpen(true);
  };

  const handleDelete = (stage: WorkflowStage) => {
    setDeletingStage(stage);
    setDeleteModalOpen(true);
  };

  const handleDeleteConfirm = async (targetStageId: number) => {
    if (!deletingStage) return;
    try {
      await deleteStage(deletingStage.id, targetStageId);
      message.success('Этап удалён');
      setDeleteModalOpen(false);
      setDeletingStage(undefined);
      load();
    } catch (e) {
      message.error(errorMessage(e));
    }
  };

  const handleRestoreAll = async () => {
    try {
      const inactiveStages = stages.filter(s => !s.is_active);
      for (const stage of inactiveStages) {
        await updateStage(stage.id, { is_active: true });
      }
      message.success(`Восстановлено ${inactiveStages.length} этапов`);
      load();
    } catch (e) {
      message.error(errorMessage(e));
    }
  };

  const handleDragEnd = async (event: any) => {
    const { active, over } = event;
    if (active.id !== over?.id) {
      const oldIndex = stages.findIndex((i) => i.id === active.id);
      const newIndex = stages.findIndex((i) => i.id === over.id);
      const reordered = arrayMove(stages, oldIndex, newIndex);
      const updated = reordered.map((s, idx) => ({ ...s, order: idx + 1 }));
      setStages(updated);

      for (const stage of updated) {
        try {
          await updateStage(stage.id, { order: stage.order });
        } catch (e) {
          message.error(errorMessage(e));
        }
      }
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 48 }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <h1>Конструктор воркфлоу</h1>
        <Space>
          {stages.some(s => !s.is_active) && (
            <Button
              onClick={handleRestoreAll}
              icon={<UndoOutlined />}
            >
              Восстановить все
            </Button>
          )}
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setEditorOpen(true)}
          >
            Добавить этап
          </Button>
        </Space>
      </div>

      {loading && (
        <div style={{ textAlign: 'center', padding: 48 }}>
          <Spin size="large" />
        </div>
      )}

      {!loading && stages.length === 0 && (
        <EmptyState 
          title="Этапы не настроены"
          description="Добавьте хотя бы один этап для начала работы"
          actionLabel="Добавить этап"
          onAction={() => setEditorOpen(true)}
        />
      )}

      {!loading && stages.length > 0 && (
        <Card style={{ border: '1px solid #EEEEF2' }}>
          <DndContext collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
            <SortableContext items={stages.map(s => ({ id: s.id }))} strategy={verticalListSortingStrategy}>
              <Space direction="vertical" size={8} style={{ width: '100%' }}>
                {stages.map((stage) => (
                  <SortableStageRow
                    key={stage.id}
                    stage={stage}
                    onEdit={handleEdit}
                    onDelete={handleDelete}
                  />
                ))}
              </Space>
            </SortableContext>
          </DndContext>
        </Card>
      )}

      <StageEditor
        open={editorOpen}
        stage={editingStage ? {
          id: editingStage.id,
          code: editingStage.code,
          name: editingStage.name,
          order: editingStage.order,
          color: editingStage.color ?? '#6E41F2',
        } : undefined}
        onCancel={() => {
          setEditorOpen(false);
          setEditingStage(undefined);
        }}
        onSave={handleSaveStage}
      />

      <DeleteStageModal
        open={deleteModalOpen}
        onCancel={() => {
          setDeleteModalOpen(false);
          setDeletingStage(undefined);
        }}
        onConfirm={handleDeleteConfirm}
        stages={stages.filter((s) => s.id !== deletingStage?.id)}
      />
    </div>
  );
}
