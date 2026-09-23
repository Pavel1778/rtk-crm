import { api } from './client';
import type {
  ActionItem,
  BoardResponse,
  CommentItem,
  ITDirection,
  ITProduct,
  Interaction,
  ReportColumn,
  ReportResponse,
  ReportTableRow,
  StageImpact,
  Token,
  University,
  User,
  WorkflowScope,
  WorkflowStage,
} from '../types';

// --- Аутентификация ---
export const login = (email: string, password: string) =>
  api.post<Token>('/api/auth/login', { email, password }).then((r) => r.data);

export const me = () => api.get<User>('/api/auth/me').then((r) => r.data);

export const listUsers = () =>
  api.get<User[]>('/api/auth/users').then((r) => r.data);

// --- Взаимодействия и доска ---
export const getBoard = (params?: {
  search?: string;
  product_id?: number;
  scope?: WorkflowScope;
}) => api.get<BoardResponse>('/api/interactions/board', { params }).then((r) => r.data);

export const getInteraction = (id: number) =>
  api.get<Interaction>(`/api/interactions/${id}`).then((r) => r.data);

export const createInteraction = (payload: {
  university_id: number;
  product_id?: number | null;
  stage_id?: number | null;
  assigned_kam_id?: number | null;
  scope?: WorkflowScope;
}) => api.post<Interaction>('/api/interactions', payload).then((r) => r.data);

export const updateInteraction = (
  id: number,
  payload: Record<string, unknown>
) =>
  api
    .patch<Interaction>(`/api/interactions/${id}`, payload)
    .then((r) => r.data);

export const deleteInteraction = (id: number) =>
  api.delete(`/api/interactions/${id}`);

export const moveInteraction = (id: number, stageId: number) =>
  api
    .post<Interaction>(`/api/interactions/${id}/move?stage_id=${stageId}`)
    .then((r) => r.data);

export const listActions = (interactionId: number) =>
  api
    .get<ActionItem[]>(`/api/interactions/${interactionId}/actions`)
    .then((r) => r.data);

export const createAction = (
  interactionId: number,
  payload: { title: string; description?: string; due_date?: string }
) =>
  api
    .post<ActionItem>(`/api/interactions/${interactionId}/actions`, payload)
    .then((r) => r.data);

export const updateAction = (id: number, payload: Record<string, unknown>) =>
  api.patch<ActionItem>(`/api/interactions/actions/${id}`, payload).then((r) => r.data);

export const deleteAction = (id: number) =>
  api.delete(`/api/interactions/actions/${id}`);

export const listComments = (interactionId: number) =>
  api
    .get<CommentItem[]>(`/api/interactions/${interactionId}/comments`)
    .then((r) => r.data);

export const createComment = (interactionId: number, text: string) =>
  api
    .post<CommentItem>(`/api/interactions/${interactionId}/comments`, { text })
    .then((r) => r.data);

export const deleteComment = (id: number) =>
  api.delete(`/api/interactions/comments/${id}`);

// --- Файлы ---
export const listFiles = (interactionId: number) =>
  api.get(`/api/files/interactions/${interactionId}`).then((r) => r.data);

export const uploadFile = (interactionId: number, file: File) => {
  const formData = new FormData();
  formData.append('file', file);
  // Content-Type выставляет интерцептор: ручное значение ломает boundary.
  return api.post(`/api/files/interactions/${interactionId}/upload`, formData).then((r) => r.data);
};

export const downloadFile = (fileId: number) =>
  api.get(`/api/files/${fileId}/download`, {
    responseType: 'blob',
  }).then((r) => r.data);

export const deleteFile = (fileId: number) =>
  api.delete(`/api/files/${fileId}`);

// --- Справочники ---
export const listUniversities = (search?: string) =>
  api
    .get<University[]>('/api/universities', { params: { search } })
    .then((r) => r.data);

export const createUniversity = (payload: Record<string, unknown>) =>
  api.post<University>('/api/universities', payload).then((r) => r.data);

export const updateUniversity = (id: number, payload: Record<string, unknown>) =>
  api
    .patch<University>(`/api/universities/${id}`, payload)
    .then((r) => r.data);

export const deleteUniversity = (id: number) =>
  api.delete(`/api/universities/${id}`);

export const listDirections = () =>
  api.get<ITDirection[]>('/api/directions').then((r) => r.data);

export const createDirection = (name: string) =>
  api.post<ITDirection>('/api/directions', { name }).then((r) => r.data);

export const deleteDirection = (id: number) =>
  api.delete(`/api/directions/${id}`);

export const listProducts = () =>
  api.get<ITProduct[]>('/api/products').then((r) => r.data);

export const createProduct = (payload: { name: string; direction_id?: number | null }) =>
  api.post<ITProduct>('/api/products', payload).then((r) => r.data);

export const deleteProduct = (id: number) =>
  api.delete(`/api/products/${id}`);

export type ImportIssue = {
  row: number | null;
  field: string;
  problem: string;
  severity: 'error' | 'warning' | 'ok';
  value: string | null;
};

export type CatalogImportResult = {
  success: boolean;
  headers: string[];
  data: Record<string, unknown>[];
  errors: string[];
  count: number;
  created?: number;
  total?: number;
  issues?: ImportIssue[];
  summary?: {
    total_rows: number;
    valid_rows: number;
    warning_rows: number;
    error_rows: number;
    error_count: number;
    warning_count: number;
  };
};

export const previewCatalogImport = (
  catalogType: 'universities' | 'products',
  file: File,
  mapping: Record<string, string>,
  format: 'excel' | 'json' = 'excel',
) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('mapping', JSON.stringify(mapping));
  return api
    .post<CatalogImportResult>(
      `/api/catalogs/import/${format === 'json' ? 'json/' : ''}preview`,
      formData,
      { params: { catalog_type: catalogType } },
    )
    .then((r) => r.data);
};

export const executeCatalogImport = (
  catalogType: 'universities' | 'products',
  file: File,
  mapping: Record<string, string>,
  format: 'excel' | 'json' = 'excel',
) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('mapping', JSON.stringify(mapping));
  return api
    .post<CatalogImportResult>(
      `/api/catalogs/import/${format === 'json' ? 'json/' : ''}execute`,
      formData,
      { params: { catalog_type: catalogType } },
    )
    .then((r) => r.data);
};

export const downloadCatalogImportReport = (
  catalogType: 'universities' | 'products',
  file: File,
  mapping: Record<string, string>,
) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('mapping', JSON.stringify(mapping));
  return api
    .post<Blob>('/api/catalogs/import/report', formData, {
      params: { catalog_type: catalogType },
      responseType: 'blob',
    })
    .then((r) => r.data);
};

// --- Воркфлоу ---
export const listStages = (includeInactive = false, scope?: WorkflowScope) =>
  api
    .get<WorkflowStage[]>('/api/stages', {
      params: {
        ...(includeInactive ? { include_inactive: true } : {}),
        ...(scope ? { scope } : {}),
      },
    })
    .then((r) => r.data);

export const stageImpact = (id: number) =>
  api.get<StageImpact>(`/api/stages/${id}/impact`).then((r) => r.data);

export const createStage = (payload: Record<string, unknown>) =>
  api.post<WorkflowStage>('/api/stages', payload).then((r) => r.data);

export const updateStage = (id: number, payload: Record<string, unknown>) =>
  api.patch<WorkflowStage>(`/api/stages/${id}`, payload).then((r) => r.data);

/** Атомарная пересортировка: backend меняет порядки за одну транзакцию. */
export const reorderStages = (stages: { id: number; order: number }[]) =>
  api
    .post<WorkflowStage[]>('/api/stages/reorder', { stages })
    .then((r) => r.data);

export const deleteStage = (id: number, targetStageId?: number) =>
  api.delete(`/api/stages/${id}`, { params: targetStageId ? { target_stage_id: targetStageId } : undefined });

// --- Отчёты ---
export type ReportFilters = {
  stage_id?: number;
  university_id?: number;
  product_id?: number;
  direction_id?: number;
  assigned_kam_id?: number;
  date_from?: string;
  date_to?: string;
};

export const getReport = (params?: ReportFilters) =>
  api.get<ReportResponse>('/api/reports', { params }).then((r) => r.data);

/** Колонки отчёта из общего конфига — тот же список, что и в PDF/XLS-выгрузках. */
export const getReportColumns = () =>
  api.get<ReportColumn[]>('/api/reports/columns').then((r) => r.data);

/** Строки отчёта для предпросмотра — те же данные, что в PDF/XLS-выгрузке. */
export const getReportPreview = (params?: ReportFilters) =>
  api.get<ReportTableRow[]>('/api/reports/preview', { params }).then((r) => r.data);

export const exportXlsx = (params?: ReportFilters) =>
  api.get('/api/reports/xlsx', {
    params,
    responseType: 'blob',
  }).then((r) => r.data);

export const exportXls = (params?: ReportFilters) =>
  api.get('/api/reports/xls', {
    params,
    responseType: 'blob',
  }).then((r) => r.data);

export const exportPdf = (params?: ReportFilters) =>
  api.get('/api/reports/pdf', {
    params,
    responseType: 'blob',
  }).then((r) => r.data);

export const downloadReport = async (
  kind: 'xlsx' | 'xls' | 'pdf' | 'json',
  params: Record<string, string | number | undefined> = {},
) => {
  const response = await api.get(`/api/reports/${kind}`, {
    params,
    responseType: 'blob',
    timeout: 60_000,
  });
  const disposition = response.headers['content-disposition'] as string | undefined;
  const encodedName = disposition?.match(/filename\*=UTF-8''([^;]+)/i)?.[1];
  const plainName = disposition?.match(/filename="?([^"]+)"?/i)?.[1];
  const extension = kind === 'json' ? 'json' : kind;
  const filename = encodedName
    ? decodeURIComponent(encodedName)
    : plainName ?? `rtk-crm-report-${Date.now()}.${extension}`;
  return { blob: response.data as Blob, filename };
};
