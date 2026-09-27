import { App as AntApp } from 'antd';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { errorMessage } from '../api/client';
import {
  createInteraction,
  getBoard,
  moveInteraction,
} from '../api/endpoints';
import type { BoardResponse, InteractionCard } from '../types';
import { boardKey, interactionKey, type BoardFilters } from './queryKeys';

/** Перемещает карточку между колонками кэша, сохраняя порядок.
 *  Экспортируется для проверки логики отката оптимистичных перемещений. */
export function moveCardInBoard(
  board: BoardResponse,
  cardId: number,
  toStageId: number
): BoardResponse {
  const card = board.columns
    .flatMap((c) => c.interactions)
    .find((i) => i.id === cardId);
  if (!card) {
    return board;
  }
  const target = board.columns.find((c) => c.stage.id === toStageId);
  if (!target) {
    return board;
  }
  const moved: InteractionCard = {
    ...card,
    stage_id: toStageId,
    stage_name: target.stage.name,
    stage_code: target.stage.code,
  };
  return {
    ...board,
    columns: board.columns.map((column) => {
      const rest = column.interactions.filter((i) => i.id !== cardId);
      if (column.stage.id !== toStageId) {
        return rest.length === column.interactions.length
          ? column
          : { ...column, interactions: rest };
      }
      return { ...column, interactions: [...rest, moved] };
    }),
  };
}

export function useBoard(filters: BoardFilters) {
  return useQuery<BoardResponse>({
    queryKey: boardKey(filters),
    queryFn: () =>
      getBoard({
        search: filters.search || undefined,
        product_id: filters.product_id,
        scope: filters.scope,
        date_from: filters.date_from,
        date_to: filters.date_to,
      }),
  });
}

/** Перетаскивание карточки. Карточка переезжает в колонку сразу, до ответа
 *  сервера; при ошибке возвращается на прежнее место. */
export function useMoveInteraction() {
  const { message } = AntApp.useApp();
  const qc = useQueryClient();

  return useMutation<
    unknown,
    unknown,
    { id: number; stageId: number },
    { snapshots: Array<[readonly unknown[], BoardResponse | undefined]> }
  >({
    mutationFn: ({ id, stageId }) => moveInteraction(id, stageId),
    onMutate: async ({ id, stageId }) => {
      await qc.cancelQueries({ queryKey: ['board'] });
      const snapshots = qc.getQueriesData<BoardResponse>({ queryKey: ['board'] });
      for (const [key, board] of snapshots) {
        if (board) {
          qc.setQueryData(key, moveCardInBoard(board, id, stageId));
        }
      }
      return { snapshots };
    },
    onError: (error, _vars, ctx) => {
      if (ctx) {
        for (const [key, board] of ctx.snapshots) {
          qc.setQueryData(key, board);
        }
      }
      message.error(errorMessage(error, 'Не удалось переместить'));
    },
    onSettled: () => {
      void qc.invalidateQueries({ queryKey: ['board'] });
      void qc.invalidateQueries({ queryKey: ['interaction'] });
    },
  });
}

/** Создание взаимодействия. Кэш доски не правим оптимистично: у новой
 *  карточки ещё нет серверного id, а колонка первого этапа определяется
 *  backend'ом. Вместо этого дожидаемся ответа и обновляем доску. */
export function useCreateInteraction() {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: createInteraction,
    onSuccess: (created) => {
      void qc.invalidateQueries({ queryKey: ['board'] });
      qc.setQueryData(interactionKey(created.id), created);
    },
  });
}
