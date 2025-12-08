export interface DocumentSummary {
  id: string;
  title: string;
  description: string | null;
  status: 'pending' | 'uploaded' | 'converted' | 'analyzing' | 'analyzed' | 'exported' | 'failed';
  original_format: string;
  policy_repository: string | null;
  compliance_status: 'pending' | 'compliant' | 'partial' | 'non_compliant';
  version: number;
  created_at: string;
  updated_at: string;
}

export interface DocumentDetail extends DocumentSummary {
  markdown_content: string | null;
  sections: Record<string, unknown>[] | null;
  metadata: Record<string, unknown> | null;
}

export interface DocumentListResponse {
  documents: DocumentSummary[];
  total: number;
  page: number;
  per_page: number;
}

export interface AnalysisSession {
  id: string;
  document_id: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  model_provider: string | null;
  started_at: string;
  completed_at: string | null;
  error_message: string | null;
}

export interface FeedbackItem {
  id: string;
  document_id: string;
  session_id: string;
  type: 'suggestion' | 'warning' | 'error' | 'improvement';
  severity: 'low' | 'medium' | 'high' | 'critical';
  title: string;
  description: string;
  location: string | null;
  original_text: string | null;
  suggested_text: string | null;
  policy_reference: string | null;
  status: 'pending' | 'accepted' | 'rejected';
  rejection_reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface FeedbackListResponse {
  items: FeedbackItem[];
  total: number;
  pending_count: number;
  accepted_count: number;
  rejected_count: number;
}

export interface PolicyRepository {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
  policy_count: number;
}

export interface Policy {
  id: string;
  repository_id: string;
  name: string;
  description: string;
  content: string;
  category: string;
  priority: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AuditEntry {
  id: string;
  event_type: string;
  aggregate_type: string;
  aggregate_id: string;
  occurred_at: string;
  data: Record<string, unknown>;
}

export interface AuditTrailResponse {
  entries: AuditEntry[];
  total: number;
  page: number;
  per_page: number;
}

export interface DocumentVersion {
  version_number: number;
  created_at: string;
  change_summary: string | null;
}

export interface VersionListResponse {
  versions: DocumentVersion[];
  current_version: number;
}

export interface UploadDocumentRequest {
  file: File;
  title: string;
  description?: string;
  tags?: string[];
  policy_repository_id?: string;
}

export interface AnalyzeDocumentRequest {
  model_provider?: 'gemini' | 'openai' | 'anthropic';
  focus_areas?: string[];
}

export interface ErrorResponse {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
}

export interface ChatRequest {
  message: string;
  conversation_history: ChatMessage[];
}

export interface ChatResponse {
  document_id: string;
  message: string;
  timestamp: string;
}

export interface Parameter {
  id: string;
  name: string;
  description: string | null;
  type: string;
  value: string | null;
  dependencies: string[];
  section: string | null;
}

export interface ParametersResponse {
  document_id: string;
  parameters: Parameter[];
  total: number;
}
