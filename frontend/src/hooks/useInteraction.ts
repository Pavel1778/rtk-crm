import { App as AntApp } from 'antd';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { errorMessage } from '../api/client';
import {
  createAction,
  createComment,
  deleteAction,
  deleteComment,
  deleteFile,
  getInteraction,
  listActions,
  listComments,
  listFiles,
  listStages,
  listUsers,
  updateAction,
  updateInteraction,
  uploadFile,
} from '../api/endpoints';
import type {
  ActionItem,
  AttachedFile,
  CommentItem,
  Interaction,
  User,
  WorkflowStage,
} from '../types';
import {
  actionsKey,
  commentsKey,
  filesKey,
  interactionKey,
  usersKey,
} from './queryKeys';

export function useInteraction(id: number | null) {
  return useQuery<Interaction>({
    queryKey: interactionKey(id ?? 0),
    queryFn: () => getInteraction(id as number),
    enabled: id !== null,
  });
}

export function useActions(id: number | null) {
  return useQuery<ActionItem[]>({
    queryKey: actionsKey(id ?? 0),
    queryFn: () => listActions(id as number),
    enabled: id !== null,
  });
}

export function useComments(id: number | null) {
  return useQuery<CommentItem[]>({
    queryKey: commentsKey(id ?? 0),
    queryFn: () => listComments(id as number),
    enabled: id !== null,
  });
}

export function useFiles(id: number | null) {
  return useQuery<AttachedFile[]>({
    queryKey: filesKey(id ?? 0),
    queryFn: () => listFiles(id as number),
    enabled: id !== null,
  });
}

/** Активные этапы нужны для выбора этапа в карточке. Данные меняются редко,
 *  поэтому кэш общий с настройками воркфлоу. */
export function useStageOptions() {
  return useQuery<WorkflowStage[]>({
    queryKey: ['stages', 'all', 'all'],
    queryFn: () => listStages(),
  });
}

export function useUserOptions(enabled: boolean) {
  return useQuery<User[]>({
    queryKey: usersKey(),
    queryFn: listUsers,
    enabled,
  });
}

/** Правка полей карточки. Значение проставляется сразу, при ошибке —
 *  откат к снимку до изменения. */
export function useUpdateInteraction() {
  const { message } = AntApp.useApp();
  const qc = useQueryClient();

  return useMutation<
    Interaction,
    unknown,
    { id: number; payload: Record<string, unknown>; successText: string },
    { previous: Interaction | undefined }
  >({
    mutationFn: ({ id, payload }) => updateInteraction(id, payload),
    onMutate: async ({ id, payload }) => {
      await qc.cancelQueries({ queryKey: interactionKey(id) });
      const previous = qc.getQueryData<Interaction>(interactionKey(id));
      qc.setQueryData<Interaction>(interactionKey(id), (old) =>
        old ? { ...old, ...payload } : old
      );
      return { previous };
    },
    onError: (error, { id }, ctx) => {
      if (ctx?.previous) {
        qc.setQueryData(interactionKey(id), ctx.previous);
      }
      message.error(errorMessage(error, 'Не удалось сохранить'));
    },
    onSuccess: (_data, { successText }) => {
      message.success(successText);
    },
    onSettled: (_data, _error, { id }) => {
      void qc.invalidateQueries({ queryKey: interactionKey(id) });
      void qc.invalidateQueries({ queryKey: ['board'] });
    },
  });
}

/** Добавление задачи. Строка появляется в списке сразу с временным id. */
export function useCreateAction(id: number | null) {
  const { message } = AntApp.useApp();
  const qc = useQueryClient();

  return useMutation<
    ActionItem,
    unknown,
    { title: string; description?: string; due_date?: string },
    { previous: ActionItem[] | undefined }
  >({
    mutationFn: (payload) => createAction(id as number, payload),
    onMutate: async (payload) => {
      await qc.cancelQueries({ queryKey: actionsKey(id ?? 0) });
      const previous = qc.getQueryData<ActionItem[]>(actionsKey(id ?? 0));
      const optimistic: ActionItem = {
        id: -Date.now(),
        interaction_id: id ?? 0,
        title: payload.title,
        description: payload.description ?? null,
        due_date: payload.due_date ?? null,
        is_completed: false,
        author_name: null,
      };
      qc.setQueryData<ActionItem[]>(actionsKey(id ?? 0), (old) => [
        ...(old ?? []),
        optimistic,
      ]);
      return { previous };
    },
    onError: (error, _vars, ctx) => {
      if (ctx?.previous) {
        qc.setQueryData(actionsKey(id ?? 0), ctx.previous);
      }
      message.warning({
        content: errorMessage(error, 'Не удалось добавить задачу'),
        duration: 8,
      });
    },
    onSettled: () => {
      void qc.invalidateQueries({ queryKey: actionsKey(id ?? 0) });
      void qc.invalidateQueries({ queryKey: ['board'] });
    },
  });
}

/** Добавление комментария: текст появляется сразу, id — после ответа. */
export function useCreateComment(id: number | null, authorName: string | null) {
  const { message } = AntApp.useApp();
  const qc = useQueryClient();

  return useMutation<
    CommentItem,
    unknown,
    string,
    { previous: CommentItem[] | undefined }
  >({
    mutationFn: (text) => createComment(id as number, text),
    onMutate: async (text) => {
      await qc.cancelQueries({ queryKey: commentsKey(id ?? 0) });
      const previous = qc.getQueryData<CommentItem[]>(commentsKey(id ?? 0));
      const optimistic: CommentItem = {
        id: -Date.now(),
        interaction_id: id ?? 0,
        text,
        author_name: authorName,
        created_at: new Date().toISOString(),
      };
      qc.setQueryData<CommentItem[]>(commentsKey(id ?? 0), (old) => [
        ...(old ?? []),
        optimistic,
      ]);
      return { previous };
    },
    onError: (error, _vars, ctx) => {
      if (ctx?.previous) {
        qc.setQueryData(commentsKey(id ?? 0), ctx.previous);
      }
      message.warning({
        content: errorMessage(error, 'Не удалось добавить комментарий'),
        duration: 8,
      });
    },
    onSettled: () => {
      void qc.invalidateQueries({ queryKey: commentsKey(id ?? 0) });
      void qc.invalidateQueries({ queryKey: ['board'] });
    },
  });
}

/** Переключение и удаление задач/комментариев/файлов. Отдельные оптимизации
 *  здесь не нужны: списки короткие, а инвалидация обновляет и доску. */
export function useToggleAction(id: number | null) {
  const { message } = AntApp.useApp();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ actionId, isCompleted }: { actionId: number; isCompleted: boolean }) =>
      updateAction(actionId, { is_completed: isCompleted }),
    onMutate: async ({ actionId, isCompleted }) => {
      await qc.cancelQueries({ queryKey: actionsKey(id ?? 0) });
      const previous = qc.getQueryData<ActionItem[]>(actionsKey(id ?? 0));
      qc.setQueryData<ActionItem[]>(actionsKey(id ?? 0), (old) =>
        (old ?? []).map((a) =>
          a.id === actionId ? { ...a, is_completed: isCompleted } : a
        )
      );
      return { previous };
    },
    onError: (error, _vars, ctx) => {
      if (ctx?.previous) {
        qc.setQueryData(actionsKey(id ?? 0), ctx.previous);
      }
      message.warning({
        content: errorMessage(error, 'Не удалось изменить задачу'),
        duration: 8,
      });
    },
    onSettled: () => {
      void qc.invalidateQueries({ queryKey: actionsKey(id ?? 0) });
      void qc.invalidateQueries({ queryKey: ['board'] });
    },
  });
}

export function useDeleteAction(id: number | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (actionId: number) => deleteAction(actionId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: actionsKey(id ?? 0) });
      void qc.invalidateQueries({ queryKey: ['board'] });
    },
  });
}

export function useDeleteComment(id: number | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (commentId: number) => deleteComment(commentId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: commentsKey(id ?? 0) });
      void qc.invalidateQueries({ queryKey: ['board'] });
    },
  });
}

export function useUploadFile(id: number | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => uploadFile(id as number, file),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: filesKey(id ?? 0) });
      void qc.invalidateQueries({ queryKey: ['board'] });
    },
  });
}

export function useDeleteFile(id: number | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (fileId: number) => deleteFile(fileId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: filesKey(id ?? 0) });
      void qc.invalidateQueries({ queryKey: ['board'] });
    },
  });
}
