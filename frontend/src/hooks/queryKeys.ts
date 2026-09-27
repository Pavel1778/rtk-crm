import type { WorkflowScope } from '../types';

export interface BoardFilters {
  scope: WorkflowScope;
  search?: string;
  product_id?: number;
  date_from?: string;
  date_to?: string;
}

/** Ключ доски. Фильтры входят в ключ, поэтому каждая комбинация кэшируется
 *  отдельно, а инвалидация по префиксу `['board']` задевает все сразу. */
export const boardKey = (filters: BoardFilters) => ['board', filters] as const;

/** Ключ карточки. Дочерние списки (задачи, комментарии, файлы) вложены в
 *  префикс, поэтому `invalidateQueries(['interaction', id])` обновляет их все. */
export const interactionKey = (id: number) => ['interaction', id] as const;
export const actionsKey = (id: number) => ['interaction', id, 'actions'] as const;
export const commentsKey = (id: number) => ['interaction', id, 'comments'] as const;
export const filesKey = (id: number) => ['interaction', id, 'files'] as const;
export const usersKey = () => ['users'] as const;
