/**
 * TypeScript Type Definitions
 * Shared types between frontend and backend API
 */

// ─── Authentication Types ───

export interface LoginCredentials {
  username: string;
  password: string;
  mfaCode?: string;
}

export interface AuthToken {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  role: UserRole;
  permissions: string[];
}

export interface UserProfile {
  username: string;
  email: string;
  full_name: string;
  role: UserRole;
  sbu_access: SBUCode[];
  permissions: string[];
  mfa_enabled: boolean;
}

export enum UserRole {
  SUPER_ADMIN = 'super_admin',
  REGULATORY_OFFICER = 'regulatory_officer',
  SENIOR_AUDITOR = 'senior_auditor',
  DATA_ENTRY_AGENT = 'data_entry_agent',
  READONLY_ANALYST = 'readonly_analyst',
  AUDIT_VIEWER = 'audit_viewer',
}

// ─── SBU Types ───

export enum SBUCode {
  SBU_GENERATION = 'SBU-G',
  SBU_TRANSMISSION = 'SBU-T',
  SBU_DISTRIBUTION = 'SBU-D',
}

export interface SBUSummary {
  sbu_code: SBUCode;
  total_approved: number;
  total_actual: number;
  net_variance: number;
  disallowed_amount: number;
  passed_through_amount: number;
  compliance_status: string;
}

// ─── Cost Head Types ───

export enum CostHead {
  O_AND_M = 'O&M',
  POWER_PURCHASE = 'Power_Purchase',
  INTEREST = 'Interest',
  DEPRECIATION = 'Depreciation',
  ROE = 'Return_on_Equity',
  OTHER = 'Other',
}

export enum VarianceCategory {
  CONTROLLABLE = 'Controllable',
  UNCONTROLLABLE = 'Uncontrollable',
}

export enum MappingStatus {
  PENDING = 'Pending',
  CONFIRMED = 'Confirmed',
  OVERRIDDEN = 'Overridden',
  REJECTED = 'Rejected',
}

// ─── Extraction Types ───

export interface ExtractedField {
  field_name: string;
  sbu_code: SBUCode;
  extracted_value: number | null;
  confidence_score: number;
  source_page: number;
  source_table: number | null;
  cell_reference: string | null;
  raw_text: string | null;
  review_required: boolean;
}

export interface ExtractionResponse {
  job_id: string;
  filename: string;
  total_pages_processed: number;
  total_fields_extracted: number;
  fields_requiring_review: number;
  extraction_method: string;
  timestamp: string;
  fields: ExtractedField[];
}

// ─── Mapping Types ───

export interface MappingSuggestion {
  mapping_id: number;
  sbu_code: SBUCode;
  source_field: string;
  suggested_head: CostHead;
  suggested_category: VarianceCategory;
  confidence: number;
  reasoning: string;
  status: MappingStatus;
}

export interface MappingConfirmRequest {
  mapping_id: number;
  decision: 'Confirmed' | 'Overridden' | 'Rejected';
  override_head?: string;
  override_category?: string;
  comment: string;
  officer_name: string;
}

export interface MappingConfirmResponse {
  mapping_id: number;
  status: string;
  original_ai_suggestion: {
    source_field: string;
    suggested_head: string;
    suggested_category: string;
    confidence: number;
  };
  final_mapping: {
    head: string;
    category: string;
  };
  officer_comment: string;
  decided_by: string;
  decided_at: string;
  audit_note: string;
}

// ─── Audit & Computation Types ───

export interface RegulatoryReference {
  clause: string;
  description: string;
  order_date: string;
}

export interface AuditResult {
  timestamp: string;
  checksum: string;
  sbu_code: SBUCode;
  scenario: string;
  cost_head: CostHead;
  variance_category: VarianceCategory;
  approved_amount: number;
  actual_amount: number;
  variance_amount: number;
  disallowed_variance: number;
  passed_through_variance: number;
  disallowance_reason: string | null;
  logic_applied: string;
  regulatory_reference: RegulatoryReference;
  metadata: {
    engine_version: string;
    flags: string[];
  };
  input_snapshot: {
    head: string;
    category: string;
    sbu_code: string;
    approved: number;
    actual: number;
    anomaly_score?: number;
    evidence_page?: number;
    is_human_verified: boolean;
  };
}

// ─── Report Types ───

export interface VarianceTrend {
  cost_head: string;
  current_variance: number;
  previous_variance: number;
  trend_direction: 'increasing' | 'decreasing' | 'stable';
  trend_percentage: number;
  regulatory_significance: string;
}

export interface AnalyticalReport {
  report_id: string;
  report_type: string;
  generated_at: string;
  financial_year: string;
  sbu_scope: SBUCode[];
  preliminary_summary: {
    total_cost_heads_analyzed: number;
    total_approved_arr: number;
    total_actual_arr: number;
    net_variance: number;
  };
  variance_analysis: VarianceTrend[];
  cost_head_breakdown: Record<string, {
    approved: number;
    actual: number;
    variance: number;
  }>;
  extracted_data_summary: {
    total_fields_extracted: number;
    fields_from_table_38: number;
    fields_from_table_39: number;
    extraction_confidence_avg: number;
  };
  deviations_flagged: Array<{
    cost_head: string;
    variance: number;
    category: string;
    severity: string;
    regulatory_reference: string;
  }>;
  anomaly_count: number;
  arr_comparison: {
    approved_total: number;
    actual_total: number;
    variance_percentage: number;
  };
  gap_analysis: {
    controllable_gap: number;
    uncontrollable_gap: number;
    net_revenue_gap: number;
  };
  historical_comparison: {
    previous_year_approved: number;
    previous_year_actual: number;
    trend: string;
  };
  year_over_year_change: number;
  insights: string[];
  recommendations: string[];
  checksum: string;
  generated_by: string;
}

export interface HistoricalTrendData {
  financial_year: string;
  power_purchase_cost: number;
  o_and_m_cost: number;
  staff_cost: number;
  line_loss_percent: number;
  total_approved_arr: number;
  total_actual_arr: number;
  revenue_gap: number;
}

export interface EfficiencyResponse {
  financial_year: string;
  target_loss_percent: number;
  actual_loss_percent: number;
  deviation_percent: number;
  is_violation: boolean;
  logic_applied: string;
  regulatory_clause: string;
  penalty_estimate_cr: number;
}

// ─── Error Types ───

export interface ApiErrorResponse {
  detail: string;
  status_code?: number;
  [key: string]: unknown;
}

// ─── Component Prop Types ───

export interface DashboardProps {
  user: UserProfile;
  activeSBU?: SBUCode;
}

export interface MappingWorkbenchProps {
  pendingMappings: MappingSuggestion[];
  onConfirm: (id: number) => void;
  onOverride: (id: number, head: string, category: string, comment: string) => void;
  onReject: (id: number, comment: string) => void;
}

export interface ExtractionUploaderProps {
  onUploadComplete: (response: ExtractionResponse) => void;
  onUploadError: (error: Error) => void;
}

export interface ReportViewerProps {
  report: AnalyticalReport | null;
  isLoading: boolean;
  onGenerate: (financialYear: string) => void;
}
