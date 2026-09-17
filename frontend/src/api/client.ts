import axios from 'axios';
import type { University, CreateUniversityDto, UpdateUniversityDto, WorkflowStage } from '../types';

// Создание экземпляра axios с базовыми настройками
const apiClient = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Интерцептор для обработки ошибок
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export const universitiesApi = {
  // Получить список всех вузов
  getAll: async (params?: { status?: string; manager_name?: string }): Promise<University[]> => {
    const response = await apiClient.get<University[]>('/universities/', { params });
    return response.data;
  },

  // Получить вуз по ID
  getById: async (id: number): Promise<University> => {
    const response = await apiClient.get<University>(`/universities/${id}`);
    return response.data;
  },

  // Создать новый вуз
  create: async (data: CreateUniversityDto): Promise<University> => {
    const response = await apiClient.post<University>('/universities/', data);
    return response.data;
  },

  // Обновить вуз
  update: async (id: number, data: UpdateUniversityDto): Promise<University> => {
    const response = await apiClient.put<University>(`/universities/${id}`, data);
    return response.data;
  },

  // Удалить вуз
  delete: async (id: number): Promise<void> => {
    await apiClient.delete(`/universities/${id}`);
  },
};

export const workflowApi = {
  // Получить все этапы воркфлоу
  getAll: async (): Promise<WorkflowStage[]> => {
    const response = await apiClient.get<WorkflowStage[]>('/workflow/');
    return response.data;
  },
};

export default apiClient;
