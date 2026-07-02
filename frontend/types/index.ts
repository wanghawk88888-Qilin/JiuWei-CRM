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
  last_followup_by: number | null;
  last_followup_by_name: string | null;
  last_followup_at: string | null;
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
}

export interface RecentLeadItem {
  id: number;
  name: string;
  phone: string | null;
  status: string;
  intention_level: string | null;
  owner_id: number | null;
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
  created_by: number | null;
  created_at: string;
  updated_at: string;
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
