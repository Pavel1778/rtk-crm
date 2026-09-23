import { App as AntApp } from 'antd';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { errorMessage } from '../api/client';
import { deleteStage, listStages, stageImpact, updateStage } from '../api/endpoints';
import type { StageImpact, WorkflowScope, WorkflowStage } from '../types';

export type StageScope = 'all' | 'active';

export const stagesKey = (scope: StageScope, funnel: WorkflowScope | 'all' = 'all') =>
  ['stages', scope, funnel] as const;

export function useStages(
  scope: StageScope = 'all',
  funnel: WorkflowScope | 'all' = 'all'
) {
  return useQuery<WorkflowStage[]>({
    queryKey: stagesKey(scope, funnel),
    queryFn: () =>
      listStages(scope === 'all', funnel === 'all' ? undefined : funnel),
  });
}

export function useStageImpact(stageId: number | null) {
  return useQuery<StageImpact>({
    queryKey: ['stage-impact', stageId],
    queryFn: () => stageImpact(stageId as number),
    enabled: stageId !== null,
  });
}

export function useToggleStage(scope: StageScope = 'all') {
  const { message } = AntApp.useApp();
  const qc = useQueryClient();

  return useMutation<
    WorkflowStage,
    unknown,
    { id: number; isActive: boolean },
    { prev: WorkflowStage[] | undefined }
  >({
    mutationFn: ({ id, isActive }) => updateStage(id, { is_active: isActive }),
    onMutate: async ({ id, isActive }) => {
      await qc.cancelQueries({ queryKey: stagesKey(scope) });
      const prev = qc.getQueryData<WorkflowStage[]>(stagesKey(scope));
      qc.setQueryData<WorkflowStage[]>(stagesKey(scope), (old) =>
        (old ?? []).map((s) => (s.id === id ? { ...s, is_active: isActive } : s))
      );
      return { prev };
    },
    onError: (error, _vars, ctx) => {
      if (ctx?.prev) {
        qc.setQueryData(stagesKey(scope), ctx.prev);
      }
      message.warning({
        content: errorMessage(error, 'Не удалось изменить этап'),
        duration: 8,
      });
    },
    onSettled: () => {
      void qc.invalidateQueries({ queryKey: ['stages'] });
      void qc.invalidateQueries({ queryKey: ['board'] });
    },
  });
}

export function useDeleteStage() {
  const { message } = AntApp.useApp();
  const qc = useQueryClient();

  return useMutation<void, unknown, { id: number; targetStageId?: number }>({
    mutationFn: async ({ id, targetStageId }) => {
      await deleteStage(id, targetStageId);
    },
    onSuccess: () => {
      message.success('Этап удалён');
    },
    onError: (error) => {
      message.warning({
        content: errorMessage(error, 'Не удалось удалить этап'),
        duration: 8,
      });
    },
    onSettled: () => {
      void qc.invalidateQueries({ queryKey: ['stages'] });
      void qc.invalidateQueries({ queryKey: ['board'] });
    },
  });
}
