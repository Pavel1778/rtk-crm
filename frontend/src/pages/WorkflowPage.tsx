import { App as AntApp, Button, Card, Segmented, Space, Spin } from 'antd';
import { PlusOutlined, UndoOutlined } from '@ant-design/icons';
import { useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';

import { errorMessage } from '../api/client';
import { createStage, reorderStages, updateStage } from '../api/endpoints';
import type { WorkflowScope, WorkflowStage } from '../types';
import { stagesKey, useDeleteStage, useStages } from '../hooks/useStages';
import { useRole } from '../stores/authStore';
import StageEditor from '../components/workflow/StageEditor';
import DeleteStageModal from '../components/workflow/DeleteStageModal';
import StageTable from '../components/workflow/StageTable';
import EmptyState from '../components/EmptyState';

export default function WorkflowPage() {
  const { message } = AntApp.useApp();
  const role = useRole();
  const qc = useQueryClient();
  const [funnel, setFunnel] = useState<WorkflowScope>('b2b');
  const { data: stages = [], isLoading } = useStages('all', funnel);
  const deleteStageMutation = useDeleteStage();
  const [editorOpen, setEditorOpen] = useState(false);
  const [editingStage, setEditingStage] = useState<WorkflowStage | undefined>();
  const [deletingStage, setDeletingStage] = useState<WorkflowStage | undefined>();

  const refresh = () => {
    void qc.invalidateQueries({ queryKey: ['stages'] });
    void qc.invalidateQueries({ queryKey: ['board'] });
  };

  if (role !== 'admin') {
    return (
      <Card>
        <p>Доступ запрещён. Только администраторы могут редактировать этапы воркфлоу.</p>
      </Card>
    );
  }

  const handleSaveStage = async (data: {
    code: string;
    name: string;
    order: number;
    color: string;
  }) => {
    try {
      if (editingStage?.id) {
        await updateStage(editingStage.id, data);
        message.success('Этап обновлён');
      } else {
        // Новый этап попадает в выбранную воронку, чтобы не смешивать B2B/B2C.
        await createStage({ ...data, scope: funnel });
        message.success('Этап создан');
      }
      setEditorOpen(false);
      setEditingStage(undefined);
      refresh();
    } catch (e) {
      message.error(errorMessage(e));
    }
  };

  const handleEdit = (stage: WorkflowStage) => {
    setEditingStage(stage);
    setEditorOpen(true);
  };

  const handleDeleteConfirm = async (targetStageId?: number) => {
    if (!deletingStage) return;
    try {
      await deleteStageMutation.mutateAsync({
        id: deletingStage.id,
        targetStageId,
      });
      setDeletingStage(undefined);
    } catch {
      // сообщение об ошибке показывает мутация
    }
  };

  const handleRestoreAll = async () => {
    const inactiveStages = stages.filter((s) => !s.is_active);
    try {
      for (const stage of inactiveStages) {
        await updateStage(stage.id, { is_active: true });
      }
      message.success(`Восстановлено ${inactiveStages.length} этапов`);
    } catch (e) {
      message.error(errorMessage(e));
    } finally {
      refresh();
    }
  };

  const handleDragEnd = async (reordered: WorkflowStage[]) => {
    qc.setQueryData(stagesKey('all', funnel), reordered);

    try {
      await reorderStages(reordered.map((s) => ({ id: s.id, order: s.order })));
    } catch (e) {
      message.error(errorMessage(e));
    } finally {
      refresh();
    }
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <h1>Конструктор воркфлоу</h1>
        <Space>
          <Segmented
            id="workflow-funnel"
            value={funnel}
            onChange={(value) => {
              setFunnel(value as WorkflowScope);
              setEditingStage(undefined);
            }}
            options={[
              { value: 'b2b', label: 'B2B' },
              { value: 'b2c', label: 'B2C' },
            ]}
          />
          {stages.some((s) => !s.is_active) && (
            <Button onClick={handleRestoreAll} icon={<UndoOutlined />}>
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

      {isLoading && (
        <div style={{ textAlign: 'center', padding: 48 }}>
          <Spin size="large" />
        </div>
      )}

      {!isLoading && stages.length === 0 && (
        <EmptyState
          title="Этапы не настроены"
          description="Добавьте хотя бы один этап для начала работы"
          actionLabel="Добавить этап"
          onAction={() => setEditorOpen(true)}
        />
      )}

      {!isLoading && stages.length > 0 && (
        <Card style={{ border: '1px solid var(--atmr-border-soft)' }}>
          <StageTable
            stages={stages}
            sortable
            onReorder={handleDragEnd}
            onEdit={handleEdit}
            onDelete={setDeletingStage}
          />
        </Card>
      )}

      <StageEditor
        open={editorOpen}
        stage={editingStage ? {
          id: editingStage.id,
          code: editingStage.code,
          name: editingStage.name,
          order: editingStage.order,
          color: editingStage.color ?? 'var(--atmr-accent-default)',
        } : undefined}
        onCancel={() => {
          setEditorOpen(false);
          setEditingStage(undefined);
        }}
        onSave={handleSaveStage}
      />

      <DeleteStageModal
        open={Boolean(deletingStage)}
        stageId={deletingStage?.id ?? null}
        onCancel={() => setDeletingStage(undefined)}
        onConfirm={handleDeleteConfirm}
        confirmLoading={deleteStageMutation.isPending}
      />
    </div>
  );
}
