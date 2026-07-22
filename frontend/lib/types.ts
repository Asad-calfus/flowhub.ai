// Mirrors backend/app/schemas/*.py and the src/*/schemas.py Literals they wrap.
// Keep in sync by hand - there is no generated client in this phase.

export type FeedbackType =
  | "Bug report"
  | "Feature request"
  | "Usability issue"
  | "Performance issue"
  | "Service complaint"
  | "Praise"
  | "Question"
  | "Other";

export type Category =
  | "Technical Issue"
  | "Product Feedback"
  | "Support Experience"
  | "Positive Feedback"
  | "Inquiry"
  | "Other";

export type ProductModule =
  | "Authentication"
  | "Dashboard"
  | "Task Management"
  | "Notifications"
  | "Billing"
  | "Integrations"
  | "Reports"
  | "Mobile App";

export type Sentiment = "Positive" | "Neutral" | "Negative" | "Mixed";
export type Urgency = "Low" | "Medium" | "High";
export type Source = "Support ticket" | "Survey" | "App review" | "Chat" | "Email" | "Community post";
export type CustomerTier = "Free" | "Pro" | "Enterprise";
export type ContextType = "known_bug" | "feature_request" | "release";
export type ContextStatus =
  | "known_bug"
  | "duplicate_feature_request"
  | "possible_release_issue"
  | "new_untracked_issue"
  | "no_confident_match";
export type TrendStatus = "new" | "growing" | "stable" | "declining";
export type AnalysisMethod = "baseline" | "llm";
export type ReportGenerationMode = "deterministic" | "dry_run" | "live";
export type GenerationMethod = "deterministic" | "dry_run" | "llm";

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface FeedbackOut {
  id: string;
  feedback_text: string;
  source: Source | null;
  feedback_created_at: string | null;
  customer_id: string | null;
  customer_tier: CustomerTier | null;
  product_version: string | null;
  rating: number | null;
  language: string | null;
  processing_status: string;
  created_at: string;
  updated_at: string;
}

export interface ImportSummary {
  feedback_imported: number;
  feedback_skipped: number;
  context_records_imported: number;
  context_records_skipped: number;
  analysis_results_imported: number;
  analysis_results_skipped: number;
  embeddings_imported: number;
  embeddings_skipped: number;
  context_matches_imported: number;
  context_matches_skipped: number;
  themes_imported: number;
  themes_skipped: number;
  theme_members_imported: number;
  theme_members_skipped: number;
  errors: string[];
}

export interface FeedbackListFilters {
  page?: number;
  page_size?: number;
  source?: string;
  sentiment?: string;
  category?: string;
  product_module?: string;
  customer_tier?: string;
  customer_id?: string;
  processing_status?: string;
  date_from?: string;
  date_to?: string;
}

export interface AnalysisOut {
  feedback_id: string;
  feedback_type: FeedbackType;
  category: Category;
  product_module: ProductModule;
  sentiment: Sentiment;
  urgency: Urgency;
  confidence: number;
  reasoning: string;
  model_name: string;
  prompt_version: string | null;
  created_at: string;
}

export interface SimilarFeedbackOut {
  feedback_id: string;
  matched_feedback_id: string;
  rank: number;
  similarity_score: number;
  text_preview: string;
}

export interface ContextMatchOut {
  feedback_id: string;
  context_record_id: string;
  context_type: ContextType;
  title: string;
  match_type: string;
  similarity_score: number;
  rank: number;
  match_status: string;
}

export interface ContextMatchSummary {
  feedback_id: string;
  status: ContextStatus;
  matched_context_id: string | null;
  candidates: ContextMatchOut[];
}

export interface ThemeMemberOut {
  feedback_id: string;
  membership_score: number | null;
}

export interface ThemeOut {
  id: string;
  name: string;
  keywords: string[];
  feedback_count: number;
  first_seen: string | null;
  last_seen: string | null;
  trend_status: TrendStatus | null;
}

export interface ThemeDetailOut extends ThemeOut {
  sentiment_distribution: Record<string, number>;
  representative_feedback: Record<string, unknown>[];
  members: ThemeMemberOut[];
}

export interface SupportingEvidence {
  representative_feedback_ids: string[];
  related_context_ids: string[];
  related_theme_ids: string[];
  evidence_strength: "high" | "medium" | "low";
}

export interface SummaryMetrics {
  total_feedback: number;
  feedback_by_source: Record<string, number>;
  feedback_by_type: Record<string, number>;
  sentiment_distribution: Record<string, number>;
  feedback_by_product_module: Record<string, number>;
  feedback_by_customer_tier: Record<string, number>;
  new_issue_count: number;
  low_confidence_count: number;
  average_confidence: number | null;
}

export interface ThemeInsight {
  theme_id: string;
  title: string;
  description: string;
  feedback_count: number;
  trend: TrendStatus;
  percent_change: number | null;
  sentiment_distribution: Record<string, number>;
  product_module: string | null;
  evidence: SupportingEvidence;
}

export interface ProductModuleInsight {
  product_module: string;
  title: string;
  description: string;
  feedback_count: number;
  negative_ratio: number;
  sentiment_distribution: Record<string, number>;
  evidence: SupportingEvidence;
}

export interface ContextInsight {
  context_id: string;
  context_type: "known_bug" | "feature_request" | "release" | "new_issue";
  title: string;
  description: string;
  feedback_count: number;
  trend: TrendStatus;
  status: string | null;
  product_module: string | null;
  evidence: SupportingEvidence;
}

export interface RecommendedAction {
  action_id: string;
  action_type: string;
  title: string;
  description: string;
  priority: "Low" | "Medium" | "High";
  evidence: SupportingEvidence;
}

export interface EnterpriseInsight {
  title: string;
  description: string;
  feedback_count: number;
  evidence: SupportingEvidence;
}

export interface WeeklyReport {
  report_id: string | null;
  period: {
    start_date: string;
    end_date: string;
    previous_period_start: string | null;
    previous_period_end: string | null;
    is_all_time: boolean;
  };
  product_module_filter: string | null;
  customer_tier_filter: string | null;
  executive_summary: string;
  summary_metrics: SummaryMetrics;
  top_pain_points: ThemeInsight[];
  growing_themes: ThemeInsight[];
  most_negative_modules: ProductModuleInsight[];
  feature_requests: ContextInsight[];
  known_bugs_growing: ContextInsight[];
  release_related_issues: ContextInsight[];
  enterprise_feedback: EnterpriseInsight[];
  new_untracked_issues: ContextInsight[];
  recommended_actions: RecommendedAction[];
  data_limitations: { notes: string[] };
  generation_method: GenerationMethod;
  model_name: string | null;
  prompt_version: string | null;
  created_at: string | null;
}

export interface ReportSummaryOut {
  id: string;
  start_date: string;
  end_date: string;
  is_all_time: boolean;
  product_module_filter: string | null;
  customer_tier_filter: string | null;
  generation_method: string;
  model_name: string | null;
  prompt_version: string | null;
  created_at: string;
}

export interface ReportOut extends ReportSummaryOut {
  report: WeeklyReport;
  markdown: string;
}

export interface ReportShareLinkOut {
  report_id: string;
  token: string;
  path: string;
  expires_at: string;
}

export interface ReportGenerationRequest {
  // Omit both for an all-time report over every stored feedback record.
  start_date?: string | null;
  end_date?: string | null;
  mode?: ReportGenerationMode;
  product_module?: string | null;
  customer_tier?: string | null;
  force?: boolean;
}

export interface HealthStatus {
  status: string;
  database?: string;
  llm_provider?: string;
  llm_model?: string;
  llm_configured?: boolean;
}

export interface BatchAnalysisResultItem {
  feedback_id: string;
  status: "success" | "failed" | "skipped";
  error?: string | null;
}

export interface BatchAnalysisResponse {
  requested: number;
  succeeded: number;
  failed: number;
  skipped: number;
  results: BatchAnalysisResultItem[];
}

export interface CostEstimate {
  pending_count: number;
  provider: string;
  model: string;
  configured: boolean;
  estimated_cost_usd: number | null;
}

export interface RetrievalBatchResultItem {
  feedback_id: string;
  status: "success" | "failed";
  error?: string | null;
}

export interface RetrievalBatchResponse {
  requested: number;
  succeeded: number;
  failed: number;
  results: RetrievalBatchResultItem[];
}

export interface RecomputeThemesResponse {
  themes_created: number;
  feedback_assigned: number;
  feedback_unclustered: number;
}

// --- Human-in-the-loop corrections ---

export type CorrectableField = "feedback_type" | "category" | "product_module" | "sentiment" | "urgency";

export interface CorrectionRequest {
  field: CorrectableField;
  corrected_value: string;
  corrected_by?: string | null;
}

export interface CorrectionOut {
  id: number;
  feedback_id: string;
  field: CorrectableField;
  original_value: string;
  corrected_value: string;
  corrected_by: string | null;
  created_at: string;
}

export interface CorrectionStatsOut {
  total_classified: number;
  total_corrected_records: number;
  correction_rate: number;
  corrections_by_field: Record<string, number>;
}

// --- Churn risk ---

export type RiskLevel = "Low" | "Medium" | "High";

export interface CustomerRiskOut {
  customer_id: string;
  customer_tier: string | null;
  risk_score: number;
  risk_level: RiskLevel;
  total_feedback: number;
  negative_count: number;
  high_urgency_count: number;
  last_feedback_sentiment: string | null;
  suggested_action: string;
  reviewed: boolean;
}

// --- AI Copilot ---

export interface CopilotAskRequest {
  question: string;
  top_k?: number;
  live?: boolean;
}

export interface CopilotSource {
  feedback_id: string;
  text_preview: string;
  sentiment: string | null;
  similarity_score: number;
}

export interface CopilotAnswerOut {
  question: string;
  answer: string;
  model_name: string;
  sources: CopilotSource[];
}
