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
  section_id: string | null;
  category: string | null;
  severity: string | null;
  title: string;  // Derived from explanation
  description: string;  // Mapped from explanation
  location: string | null;  // Mapped from section_id
  original_text: string | null;
  suggested_text: string | null;  // Mapped from suggestion
  suggestion: string;  // Backend field
  explanation: string | null;  // Backend field
  confidence_score: number | null;
  policy_reference: string | null;
  status: 'pending' | 'accepted' | 'rejected';
  rejection_reason: string | null;
  processed_at: string | null;
  created_at: string;
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

// Semantic IR Types
export interface SemanticIR {
  document_id: string;
  title: string;
  original_format: string;
  sections: IRSection[];
  definitions: TermDefinition[];
  formulae: FormulaReference[];
  tables: TableData[];
  cross_references: CrossReference[];
  metadata: Record<string, any>;
  validation_issues: ValidationIssue[];
}

export interface IRSection {
  id: string;
  title: string;
  content: string;
  level: number;
  section_type: 'narrative' | 'definition' | 'formula' | 'table' | 'code' | 'glossary' | 'annex' | 'unknown';
  parent_id: string | null;
  start_line: number | null;
  end_line: number | null;
}

export interface TermDefinition {
  id: string;
  term: string;
  definition: string;
  section_id: string;
  aliases: string[];
  first_occurrence_line: number;
}

export interface FormulaReference {
  id: string;
  name: string | null;
  latex: string;
  mathml: string | null;
  plain_text: string;
  variables: string[];
  dependencies: string[];
  section_id: string;
  line_number: number | null;
}

export interface TableData {
  id: string;
  title: string | null;
  headers: string[];
  rows: string[][];
  column_types: string[];
  section_id: string;
}

export interface CrossReference {
  id: string;
  source_id: string;
  source_type: string;
  target_id: string;
  target_type: string;
  reference_text: string;
  resolved: boolean;
}

export interface ValidationIssue {
  id: string;
  issue_type: 'duplicate_definition' | 'undefined_variable' | 'circular_dependency' | 'missing_reference' | 'ambiguous_term' | 'incomplete_formula';
  severity: 'error' | 'warning' | 'info';
  message: string;
  location: string;
  related_ids: string[];
  suggestion: string | null;
}
