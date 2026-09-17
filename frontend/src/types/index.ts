export interface University {
  id: number;
  name: string;
  vendor: string | null;
  product: string | null;
  contract_number: string | null;
  license_signed: boolean;
  license_expiry_year: number | null;
  status: string;
  manager_name: string | null;
  university_responsible: string | null;
  comment: string | null;
  current_workflow_stage_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface WorkflowStage {
  id: number;
  name: string;
  order: number;
  description: string | null;
  is_active: boolean;
}

export interface CreateUniversityDto {
  name: string;
  vendor?: string;
  product?: string;
  contract_number?: string;
  license_signed?: boolean;
  license_expiry_year?: number;
  status: string;
  manager_name?: string;
  university_responsible?: string;
  comment?: string;
  current_workflow_stage_id?: number;
}

export interface UpdateUniversityDto {
  name?: string;
  vendor?: string;
  product?: string;
  contract_number?: string;
  license_signed?: boolean;
  license_expiry_year?: number;
  status?: string;
  manager_name?: string;
  university_responsible?: string;
  comment?: string;
  current_workflow_stage_id?: number;
}
