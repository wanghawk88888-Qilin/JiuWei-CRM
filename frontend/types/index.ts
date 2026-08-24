// ============================================================
// JiuWei CRM — Shared TypeScript types (aligned with backend schemas)
// ============================================================

// -- Generic API envelope ---------------------------------------------------

export interface ApiResponse<T = unknown> {
  success: boolean;
  data: T;
  message: string;
  error_code?: string;
}

// -- Auth -------------------------------------------------------------------

export interface LoginRequest {
  username: string;
  password: string;
}

export interface TokenUser {
  id: number;
  username: string;
  real_name: string;
  role: string;
}

export interface LoginResponseData {
  access_token: string;
  token_type: string;
  user: TokenUser;
}

export interface CurrentUser {
  id: number;
  username: string;
  real_name: string;
  role: string;
  phone: string | null;
  email: string | null;
}

// -- Lead -------------------------------------------------------------------

export const LEAD_STATUSES = ["new", "consulted", "following", "high_intent", "enrolled", "invalid"] as const;
export type LeadStatus = (typeof LEAD_STATUSES)[number];

export const INTENTION_LEVELS = ["low", "medium", "high"] as const;
export type IntentionLevel = (typeof INTENTION_LEVELS)[number];

export const FOLLOWUP_TYPES = ["phone", "wechat", "offline", "other"] as const;
export type FollowUpType = (typeof FOLLOWUP_TYPES)[number];

export interface LeadCreate {
  name: string;
  phone?: string | null;
  wechat?: string | null;
  email?: string | null;
  gender?: string | null;
  age?: number | null;
  education?: string | null;
  school?: string | null;
  major?: string | null;
  city?: string | null;
  current_job?: string | null;
  work_years?: string | null;
  latest_company?: string | null;
  latest_position?: string | null;
  intended_course_id?: number | null;
  source_id?: number | null;
  status?: string;
  intention_level?: string | null;
  owner_id?: number | null;
  remark?: string | null;
  ai_summary?: string | null;
  ai_course_suggestion?: string | null;
  tags?: string | null;
}

export interface LeadUpdate {
  name?: string | null;
  phone?: string | null;
  wechat?: string | null;
  email?: string | null;
  gender?: string | null;
  age?: number | null;
  education?: string | null;
  school?: string | null;
  major?: string | null;
  city?: string | null;
  current_job?: string | null;
  work_years?: string | null;
  latest_company?: string | null;
  latest_position?: string | null;
  intended_course_id?: number | null;
  source_id?: number | null;
  status?: string | null;
  intention_level?: string | null;
  owner_id?: number | null;
  remark?: string | null;
  ai_summary?: string | null;
  ai_course_suggestion?: string | null;
  tags?: string | null;
}

export interface LeadListItem {
  id: number;
  name: string;
  phone: string | null;
  wechat: string | null;
  source_id: number | null;
  intended_course_id: number | null;
  status: string;
  intention_level: string | null;
  owner_id: number | null;
  owner_name: string | null;
  last_followup_by: number | null;
  last_followup_by_name: string | null;
  last_followup_at: string | null;
  last_followup_content: string | null;
  next_followup_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface LeadListData {
  items: LeadListItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface LeadDetail {
  id: number;
  name: string;
  phone: string | null;
  wechat: string | null;
  email: string | null;
  gender: string | null;
  age: number | null;
  education: string | null;
  school: string | null;
  major: string | null;
  city: string | null;
  current_job: string | null;
  work_years: string | null;
  latest_company: string | null;
  latest_position: string | null;
  intended_course_id: number | null;
  source_id: number | null;
  status: string;
  intention_level: string | null;
  owner_id: number | null;
  remark: string | null;
  ai_summary: string | null;
  ai_course_suggestion: string | null;
  tags: string | null;
  created_at: string;
  updated_at: string;
}

// -- FollowUp ---------------------------------------------------------------

export interface FollowUpCreate {
  followup_type: string;
  content: string;
  intention_level?: string | null;
  next_followup_at?: string | null;
}

export interface FollowUpItem {
  id: number;
  lead_id: number;
  followup_type: string;
  content: string;
  intention_level: string | null;
  next_followup_at: string | null;
  created_by: number;
  created_by_name: string;
  created_at: string;
  updated_at: string;
}

// -- Dashboard --------------------------------------------------------------

export interface DashboardSummary {
  total_leads: number;
  today_new_leads: number;
  pending_followups: number;
  enrolled_leads: number;
}

export interface TodayFollowUpItem {
  lead_id: number;
  lead_name: string;
  phone: string | null;
  status: string;
  intention_level: string | null;
  next_followup_at: string | null;
  owner_id: number | null;
  owner_name: string | null;
  intended_course_name: string | null;
  latest_followup_content: string | null;
  followup_priority: string;  // "overdue" | "today" | "upcoming"
}

export interface RecentLeadItem {
  id: number;
  name: string;
  phone: string | null;
  status: string;
  intention_level: string | null;
  owner_id: number | null;
  owner_name: string | null;
  created_at: string;
}

// -- Resume Import ----------------------------------------------------------

export interface ResumeImportResult {
  import_log_id: number;
  lead_draft_id: number;
  parse_status: string;
  draft: Record<string, unknown> | null;
}

// -- Lead Draft -------------------------------------------------------------

export interface LeadDraft {
  id: number;
  import_log_id: number | null;
  name: string | null;
  phone: string | null;
  wechat: string | null;
  email: string | null;
  gender: string | null;
  age: number | null;
  education: string | null;
  school: string | null;
  major: string | null;
  graduation_time: string | null;
  city: string | null;
  work_years: string | null;
  latest_company: string | null;
  latest_position: string | null;
  skills: string | null;
  ai_summary: string | null;
  ai_course_suggestion: string | null;
  raw_text_excerpt: string | null;
  status: string;
  confirmed_lead_id: number | null;
  // v0.2.1
  batch_id?: number | null;
  name_confidence?: string | null;
  phone_confidence?: string | null;
  conflict_flags?: string | null;
  duplicate_lead_id?: number | null;
  created_by: number | null;
  created_at: string;
  updated_at: string;
}

export interface LeadDraftUpdate {
  name?: string | null;
  phone?: string | null;
  wechat?: string | null;
  email?: string | null;
  gender?: string | null;
  age?: number | null;
  education?: string | null;
  school?: string | null;
  major?: string | null;
  graduation_time?: string | null;
  city?: string | null;
  work_years?: string | null;
  latest_company?: string | null;
  latest_position?: string | null;
  skills?: string | null;
}

export interface LeadDraftConfirm {
  name?: string | null;
  phone?: string | null;
  wechat?: string | null;
  email?: string | null;
  gender?: string | null;
  age?: number | null;
  education?: string | null;
  school?: string | null;
  major?: string | null;
  city?: string | null;
  current_job?: string | null;
  work_years?: string | null;
  latest_company?: string | null;
  latest_position?: string | null;
  intended_course_id?: number | null;
  source_id?: number | null;
  owner_id?: number | null;
  remark?: string | null;
}

// -- Resume Batch Import (v0.2.1) --------------------------------------------

export interface BatchLimits {
  max_files: number;
  max_file_size_mb: number;
  allowed_extensions: string[];
}

export interface BatchUploadResult {
  batch_id: number;
  batch_no: string;
  total: number;
  status: string;
}

export interface BatchSummary {
  id: number;
  batch_no: string;
  status: string;
  total_files: number;
  parsed_count: number;
  ready_count: number;
  needs_review_count: number;
  duplicate_count: number;
  failed_count: number;
  confirmed_count: number;
  created_by: number | null;
  created_at: string;
  updated_at: string;
}

export interface BatchItemConflict {
  code: string;
  candidates: string[];
}

export interface BatchItemDuplicate {
  existing_lead_id: number | null;
  existing_lead_name: string | null;
  existing_phone: string | null;
  in_batch: boolean;
}

export interface BatchItem {
  import_log_id: number;
  file_name: string;
  file_type: string | null;
  file_size: number | null;
  parse_status: string;
  error_code: string | null;
  error_message: string | null;
  lead_draft_id: number | null;
  status: string;
  name: string | null;
  phone: string | null;
  email: string | null;
  education: string | null;
  school: string | null;
  major: string | null;
  name_confidence: string | null;
  phone_confidence: string | null;
  conflicts: { name?: BatchItemConflict; phone?: BatchItemConflict };
  duplicate: BatchItemDuplicate | null;
  confirmed_lead_id: number | null;
}

export interface BatchDetail {
  batch: BatchSummary;
  items: BatchItem[];
}

export interface BatchConfirmRequest {
  source_id?: number | null;
  owner_id?: number | null;
  remark?: string | null;
}

export interface BatchConfirmResult {
  batch_id: number;
  confirmed_count: number;
  skipped_count: number;
  created: { lead_draft_id: number; lead_id: number }[];
  skipped: { lead_draft_id: number; reason: string; existing_lead_id?: number }[];
  batch_status: string;
}

export const BATCH_ITEM_STATUS_LABELS: Record<string, string> = {
  ready: "可直接导入",
  needs_review: "需人工确认",
  duplicate: "重复线索",
  failed: "解析失败",
  confirmed: "已生成线索",
  discarded: "已丢弃",
  pending: "解析中",
  parsed: "已解析",
  confirming: "确认中",
};

export const BATCH_STATUS_LABELS: Record<string, string> = {
  processing: "解析中",
  ready: "全部可导入",
  partially_ready: "部分可导入",
  completed: "已完成",
  failed: "全部失败",
};

export const CONFIDENCE_LABELS: Record<string, string> = {
  high: "高",
  medium: "中",
  low: "低",
  missing: "未识别",
};

export const IMPORT_ERROR_LABELS: Record<string, string> = {
  INVALID_FILE_TYPE: "文件类型不支持",
  FILE_TOO_LARGE: "文件过大",
  FILE_SAVE_FAILED: "文件保存失败",
  FILE_MISSING: "临时文件丢失",
  PDF_NO_EXTRACTABLE_TEXT: "PDF 无法提取文本（疑似扫描件）",
  PDF_PARSE_FAILED: "PDF 解析失败",
  DOCX_NO_EXTRACTABLE_TEXT: "Word 未提取到有效文本",
  DOCX_PARSE_FAILED: "Word 解析失败",
  PARSER_UNAVAILABLE: "服务器缺少解析组件",
  PARSE_FAILED: "解析失败",
  INTERNAL_ERROR: "系统错误",
};

export const CONFLICT_LABELS: Record<string, string> = {
  NAME_CONFLICT: "姓名存在多个候选，无法自动判定",
  PHONE_CONFLICT: "手机号存在多个候选，无法自动判定",
  NAME_MISSING: "未识别到姓名",
  PHONE_MISSING: "未识别到手机号",
};

// -- Config -----------------------------------------------------------------

export interface LeadSource {
  id: number;
  name: string;
  description: string | null;
  is_active: number;
}

export interface Course {
  id: number;
  name: string;
  description: string | null;
  is_active: number;
}

// -- User management ---------------------------------------------------------

export interface UserItem {
  id: number;
  username: string;
  real_name: string;
  role: string;
  phone: string | null;
  email: string | null;
  is_active: number;
  created_at: string;
  updated_at: string;
}

export interface UserCreate {
  username: string;
  real_name: string;
  role: string;
  phone?: string | null;
  email?: string | null;
}

export interface UserUpdate {
  real_name?: string | null;
  role?: string | null;
  phone?: string | null;
  email?: string | null;
  is_active?: number | null;
}

export interface ChangePasswordRequest {
  old_password: string;
  new_password: string;
  confirm_password: string;
}

export const ROLE_LABELS: Record<string, string> = {
  admin: "管理员",
  manager: "主管",
  counselor: "咨询师",
};

// -- Label maps (for display) -----------------------------------------------

export const STATUS_LABELS: Record<string, string> = {
  new: "新线索",
  consulted: "已咨询",
  following: "跟进中",
  high_intent: "高意向",
  enrolled: "已报名",
  invalid: "无效",
};

export const INTENTION_LABELS: Record<string, string> = {
  low: "低",
  medium: "中",
  high: "高",
};

export const FOLLOWUP_TYPE_LABELS: Record<string, string> = {
  phone: "电话",
  wechat: "微信",
  offline: "面谈",
  other: "其他",
};

export const GENDER_LABELS: Record<string, string> = {
  male: "男",
  female: "女",
};
