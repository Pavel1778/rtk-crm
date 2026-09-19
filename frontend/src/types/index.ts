export type UserRole = 'user' | 'manager' | 'admin';

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
  is_admin: boolean;
  is_active: boolean;
  created_at: string;
}

export interface Token {
  access_token: string;
  token_type: string;
  user: User;
}

export interface University {
  id: number;
  name: string;
  city: string | null;
  contact_person: string | null;
  contact_email: string | null;
  contact_phone: string | null;
}

export interface ITDirection {
  id: number;
  name: string;
}

export interface ITProduct {
  id: number;
  name: string;
  direction_id: number | null;
  direction_name: string | null;
}

export interface WorkflowStage {
  id: number;
  code: string;
  name: string;
  order: number;
  color: string | null;
  is_active: boolean;
  interaction_count: number;
}

export interface Interaction {
  id: number;
  university_id: number;
  product_id: number | null;
  stage_id: number;
  contract_number: string | null;
  contract_date: string | null;
  assigned_kam_id: number | null;
  university_specialist: string | null;
  notes: string | null;
  is_active: boolean;
  university_name: string | null;
  product_name: string | null;
  stage_name: string | null;
  stage_code: string | null;
  assigned_kam_name: string | null;
}

export interface InteractionCard {
  id: number;
  university_id: number;
  university_name: string | null;
  product_id: number | null;
  product_name: string | null;
  stage_id: number;
  stage_name: string | null;
  stage_code: string | null;
  contract_number: string | null;
  university_specialist: string | null;
  assigned_kam_name: string | null;
  is_active: boolean;
  actions_open: number;
  actions_total: number;
  comments_count: number;
}

export interface BoardColumn {
  stage: WorkflowStage;
  interactions: InteractionCard[];
}

export interface BoardResponse {
  columns: BoardColumn[];
  total: number;
}

export interface ActionItem {
  id: number;
  interaction_id: number;
  title: string;
  description: string | null;
  due_date: string | null;
  is_completed: boolean;
  author_name: string | null;
}

export interface CommentItem {
  id: number;
  interaction_id: number;
  text: string;
  author_name: string | null;
  created_at: string;
}

export interface ReportMetric {
  key: string;
  label: string;
  value: number;
  unit: string | null;
}

export interface StageProgress {
  stage_code: string;
  stage_name: string;
  count: number;
  percent: number;
}

export interface ReportResponse {
  metrics: ReportMetric[];
  stage_progress: StageProgress[];
  generated_at: string;
}

export interface AttachedFile {
  id: number;
  interaction_id: number;
  filename: string;
  size: number;
  mime_type: string;
  uploaded_by: number | null;
  uploader_name: string | null;
  created_at: string;
}
