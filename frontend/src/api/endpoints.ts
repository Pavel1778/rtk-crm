import { api } from './client';
import type {
  ActionItem,
  BoardResponse,
  CommentItem,
  ITDirection,
  ITProduct,
  Interaction,
  ReportResponse,
  Token,
  University,
  User,
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
}) => api.get<BoardResponse>('/api/interactions/board', { params }).then((r) => r.data);

export const getInteraction = (id: number) =>
  api.get<Interaction>(`/api/interactions/${id}`).then((r) => r.data);

export const createInteraction = (payload: {
  university_id: number;
  product_id?: number | null;
  stage_id?: number | null;
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
  return api.post(`/api/files/interactions/${interactionId}/upload`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then((r) => r.data);
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

// --- Воркфлоу ---
export const listStages = () =>
  api.get<WorkflowStage[]>('/api/stages').then((r) => r.data);

export const createStage = (payload: Record<string, unknown>) =>
  api.post<WorkflowStage>('/api/stages', payload).then((r) => r.data);

export const updateStage = (id: number, payload: Record<string, unknown>) =>
  api.patch<WorkflowStage>(`/api/stages/${id}`, payload).then((r) => r.data);

export const deleteStage = (id: number) =>
  api.delete(`/api/stages/${id}`);

// --- Отчёты ---
export const getReport = () =>
  api.get<ReportResponse>('/api/reports').then((r) => r.data);

export const exportXlsx = (params?: {
  stage_id?: number;
  university_id?: number;
  product_id?: number;
}) =>
  api.get('/api/reports/xlsx', {
    params,
    responseType: 'blob',
  }).then((r) => r.data);

export const exportXls = (params?: {
  stage_id?: number;
  university_id?: number;
  product_id?: number;
}) =>
  api.get('/api/reports/xls', {
    params,
    responseType: 'blob',
  }).then((r) => r.data);

export const exportPdf = (params?: {
  stage_id?: number;
  university_id?: number;
  product_id?: number;
}) =>
  api.get('/api/reports/pdf', {
    params,
    responseType: 'blob',
  }).then((r) => r.data);
