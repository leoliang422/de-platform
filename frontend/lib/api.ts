const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export interface UserProfile {
  id: number;
  email: string;
  nickname: string;
  avatar_url: string | null;
  bio: string | null;
  job_title: string | null;
  role: string;
  points_balance: number;
  created_at: string;
}

export interface PublicUserProfile {
  id: number;
  nickname: string;
  avatar_url: string | null;
  bio: string | null;
  job_title: string | null;
  created_at: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers ?? {}),
    },
  });

  if (!res.ok) {
    let detail = `请求失败 (${res.status})`;
    try {
      const body = await res.json();
      if (Array.isArray(body?.detail)) {
        // FastAPI 校验错误：拼成可读文案
        detail = body.detail
          .map((e: { loc?: unknown[]; msg?: string }) => {
            const field = Array.isArray(e.loc) ? e.loc[e.loc.length - 1] : "";
            return field ? `${field}: ${e.msg}` : e.msg;
          })
          .join("；");
      } else if (typeof body?.detail === "string") {
        detail = body.detail;
      }
    } catch {
      // ignore json parse errors
    }
    throw new ApiError(res.status, detail);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export function register(input: {
  email: string;
  password: string;
  nickname: string;
}): Promise<UserProfile> {
  return request<UserProfile>("/auth/register", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function login(input: {
  email: string;
  password: string;
}): Promise<TokenPair> {
  return request<TokenPair>("/auth/login", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function forgotPassword(email: string): Promise<{ sent: boolean; reset_token: string | null }> {
  return request<{ sent: boolean; reset_token: string | null }>("/auth/forgot-password", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export function resetPassword(token: string, newPassword: string): Promise<void> {
  return request<void>("/auth/reset-password", {
    method: "POST",
    body: JSON.stringify({ token, new_password: newPassword }),
  });
}

export function getMe(accessToken: string): Promise<UserProfile> {
  return request<UserProfile>("/users/me", {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
}

export function updateMyProfile(
  token: string,
  input: {
    nickname?: string;
    avatar_url?: string | null;
    bio?: string | null;
    job_title?: string | null;
  },
): Promise<UserProfile> {
  return request<UserProfile>("/users/me", {
    method: "PATCH",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify(input),
  });
}

export function changeMyPassword(
  token: string,
  input: { old_password: string; new_password: string },
): Promise<void> {
  return request<void>("/users/me/password", {
    method: "PATCH",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify(input),
  });
}

export function getPublicProfile(userId: number): Promise<PublicUserProfile> {
  return request<PublicUserProfile>(`/users/${userId}`);
}

// ---- Notifications ----
export interface Notification {
  id: number;
  type: string;
  title: string;
  body: string | null;
  link: string | null;
  read_at: string | null;
  created_at: string;
}

export function getNotifications(token: string): Promise<Notification[]> {
  return authRequest<Notification[]>("/notifications", token);
}

export function getUnreadCount(token: string): Promise<{ unread: number }> {
  return authRequest<{ unread: number }>("/notifications/unread_count", token);
}

export function markNotificationRead(token: string, id: number): Promise<Notification> {
  return authRequest<Notification>(`/notifications/${id}/read`, token, { method: "POST" });
}

export function markAllNotificationsRead(token: string): Promise<{ unread: number }> {
  return authRequest<{ unread: number }>("/notifications/read-all", token, { method: "POST" });
}

export async function uploadImage(token: string, file: File): Promise<{ url: string }> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE_URL}/files/images`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  });
  if (!res.ok) {
    let detail = `上传失败 (${res.status})`;
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      // ignore
    }
    throw new ApiError(res.status, detail);
  }
  return (await res.json()) as { url: string };
}

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("de_access_token");
}

function authRequest<T>(path: string, token: string, options: RequestInit = {}): Promise<T> {
  return request<T>(path, {
    ...options,
    headers: { Authorization: `Bearer ${token}`, ...(options.headers ?? {}) },
  });
}

// ---- Catalog ----
export interface CategoryNode {
  id: number;
  name: string;
  slug: string;
  order: number;
  children: CategoryNode[];
}

export function getCategories(
  section: "knowledge" | "sql" | "interview" | "project",
): Promise<CategoryNode[]> {
  return request<CategoryNode[]>(`/categories?section=${section}`);
}

// ---- Knowledge ----
export interface KnowledgeListItem {
  id: number;
  category_id: number | null;
  title: string;
  is_paid: boolean;
  price_cash: string | null;
  price_points: number | null;
}

export interface KnowledgeDetail extends KnowledgeListItem {
  locked: boolean;
  content_md: string | null;
}

export function getKnowledgeList(categoryId?: number): Promise<KnowledgeListItem[]> {
  const q = categoryId != null ? `?category_id=${categoryId}` : "";
  return request<KnowledgeListItem[]>(`/knowledge${q}`);
}

function maybeAuth(token?: string | null): RequestInit {
  return token ? { headers: { Authorization: `Bearer ${token}` } } : {};
}

export function getKnowledgeDetail(id: number, token?: string | null): Promise<KnowledgeDetail> {
  return request<KnowledgeDetail>(`/knowledge/${id}`, maybeAuth(token));
}

// ---- SQL ----
export interface SqlListItem {
  id: number;
  category_id: number | null;
  title: string;
  difficulty: string;
  tags: string[];
}

export interface SqlDetail extends SqlListItem {
  prompt_md: string;
  answer_md: string;
}

export function getSqlList(categoryId?: number): Promise<SqlListItem[]> {
  const q = categoryId != null ? `?category_id=${categoryId}` : "";
  return request<SqlListItem[]>(`/sql-questions${q}`);
}

export function getSqlDetail(id: number): Promise<SqlDetail> {
  return request<SqlDetail>(`/sql-questions/${id}`);
}

// ---- Interview ----
export interface Company {
  id: number;
  name: string;
  logo_url: string | null;
}

export interface InterviewListItem {
  id: number;
  company_id: number;
  position: string;
  position_level: string | null;
  interview_date: string | null;
  rounds: number | null;
  result: string | null;
  city: string | null;
  channel: string | null;
}

export interface InterviewQA {
  id: number;
  section: string;
  order_index: number;
  question: string;
  answer: string;
}

export interface InterviewDetail extends InterviewListItem {
  content_md: string;
  technical_qa: InterviewQA[];
  hr_qa: InterviewQA[];
}

export interface PositionGroup {
  position: string;
  count: number;
  posts: InterviewListItem[];
}

export const INTERVIEW_RESULT_LABEL: Record<string, string> = {
  pass: "已通过",
  fail: "未通过",
  pending: "流程中",
  unknown: "未知",
};

export function getCompanies(): Promise<Company[]> {
  return request<Company[]>("/companies");
}

export function getCompanyPositions(companyId: number): Promise<PositionGroup[]> {
  return request<PositionGroup[]>(`/companies/${companyId}/positions`);
}

export function getCompanyInterviews(companyId: number): Promise<InterviewListItem[]> {
  return request<InterviewListItem[]>(`/companies/${companyId}/interviews`);
}

export function getInterviewDetail(id: number): Promise<InterviewDetail> {
  return request<InterviewDetail>(`/interviews/${id}`);
}

// ---- Projects ----
export interface ProjectListItem {
  id: number;
  title: string;
  level: string;
  access_type: string;
  price_cash: string | null;
  price_points: number | null;
}

export interface ProjectQA {
  id: number;
  question_md: string;
  answer_md: string;
  order: number;
}

export interface ProjectDetail extends ProjectListItem {
  description_md: string;
  locked: boolean;
  implementation_md: string | null;
  qa: ProjectQA[];
}

export function getProjectList(): Promise<ProjectListItem[]> {
  return request<ProjectListItem[]>("/projects");
}

export function getProjectDetail(id: number, token?: string | null): Promise<ProjectDetail> {
  return request<ProjectDetail>(`/projects/${id}`, maybeAuth(token));
}

// ---- Submissions ----
export type TargetType = "knowledge" | "sql" | "interview" | "project";

export interface InterviewQAInput {
  section: "technical" | "hr";
  question: string;
  answer: string;
}

export interface SubmissionCreateInput {
  target_type: TargetType;
  title: string;
  raw_content: string;
  category_id?: number | null;
  is_paid?: boolean;
  price_cash?: string | null;
  price_points?: number | null;
  prompt_md?: string | null;
  difficulty?: string | null;
  tags?: string | null;
  company_name?: string | null;
  position?: string | null;
  position_level?: string | null;
  interview_date?: string | null;
  interview_rounds?: number | null;
  interview_result?: "pass" | "fail" | "pending" | "unknown" | null;
  interview_city?: string | null;
  interview_channel?: string | null;
  qa_items?: InterviewQAInput[] | null;
  level?: string | null;
  access_type?: "free" | "paid" | null;
  implementation_md?: string | null;
}

export interface Submission {
  id: number;
  target_type: string;
  title: string;
  status: string;
  reject_reason: string | null;
  processed_md: string | null;
  published_ref_id: number | null;
  created_at: string;
}

export function createSubmission(
  token: string,
  input: SubmissionCreateInput,
): Promise<Submission> {
  return authRequest<Submission>("/submissions", token, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function getMySubmissions(token: string): Promise<Submission[]> {
  return authRequest<Submission[]>("/submissions/me", token);
}

export function retrySubmission(token: string, id: number): Promise<Submission> {
  return authRequest<Submission>(`/submissions/${id}/retry`, token, { method: "POST" });
}

// ---- Points ----
export interface LedgerEntry {
  id: number;
  delta: number;
  reason: string;
  ref_type: string;
  ref_id: number;
  created_at: string;
}

export interface PointsOverview {
  balance: number;
  ledger: LedgerEntry[];
}

export function getMyPoints(token: string): Promise<PointsOverview> {
  return authRequest<PointsOverview>("/points/me", token);
}

// ---- Admin ----
export interface AdminSubmission extends Submission {
  user_id: number;
  raw_content: string;
  extra: Record<string, unknown>;
}

export function adminListSubmissions(
  token: string,
  status = "pending_review",
): Promise<AdminSubmission[]> {
  return authRequest<AdminSubmission[]>(`/admin/submissions?status=${status}`, token);
}

export function adminApprove(token: string, id: number): Promise<Submission> {
  return authRequest<Submission>(`/admin/submissions/${id}/approve`, token, {
    method: "POST",
  });
}

export function adminReject(token: string, id: number, reason: string): Promise<Submission> {
  return authRequest<Submission>(`/admin/submissions/${id}/reject`, token, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}

export interface CategoryFlat {
  id: number;
  parent_id: number | null;
  section: string;
  name: string;
  slug: string;
  order: number;
}

export function adminListCategories(
  token: string,
  section: string,
): Promise<CategoryFlat[]> {
  return authRequest<CategoryFlat[]>(`/admin/categories?section=${section}`, token);
}

export function adminCreateCategory(
  token: string,
  input: { section: string; name: string; slug: string; parent_id?: number | null; order?: number },
): Promise<CategoryFlat> {
  return authRequest<CategoryFlat>("/admin/categories", token, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function adminDeleteCategory(token: string, id: number): Promise<void> {
  return authRequest<void>(`/admin/categories/${id}`, token, { method: "DELETE" });
}

// ---- Payment / Entitlements ----
export type PayableType = "project" | "knowledge";
export type UnlockMethod = "cash" | "points";

export interface Entitlement {
  id: number;
  content_type: string;
  content_id: number;
  source: string;
  created_at: string;
}

export interface UnlockResult {
  // 同步结算（积分 / mock 现金）返回 entitlement；异步支付（微信/支付宝）
  // 返回 status="pending" + pay_url/qr_code，entitlement 为 null。
  status: "paid" | "pending" | "already";
  entitlement: Entitlement | null;
  balance: number;
  already_unlocked: boolean;
  order_id?: number | null;
  pay_url?: string | null;
  qr_code?: string | null;
}

export function unlockContent(
  token: string,
  input: { content_type: PayableType; content_id: number; method: UnlockMethod },
): Promise<UnlockResult> {
  return authRequest<UnlockResult>("/payment/unlock", token, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function getMyEntitlements(token: string): Promise<Entitlement[]> {
  return authRequest<Entitlement[]>("/payment/entitlements/me", token);
}

// ---- Admin 内容管理 ----
export type ContentType = "knowledge" | "sql" | "interview" | "project";

export interface ContentSummary {
  id: number;
  title: string;
  subtitle: string | null;
  status: string;
}

export function adminListContent(
  token: string,
  type: ContentType,
): Promise<ContentSummary[]> {
  return authRequest<ContentSummary[]>(`/admin/content/${type}`, token);
}

export function adminGetContentDetail(
  token: string,
  type: ContentType,
  id: number,
): Promise<Record<string, unknown>> {
  return authRequest<Record<string, unknown>>(`/admin/content/${type}/${id}/detail`, token);
}

export function adminCreateContent(
  token: string,
  type: ContentType,
  body: Record<string, unknown>,
): Promise<ContentSummary> {
  return authRequest<ContentSummary>(`/admin/content/${type}`, token, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function adminUpdateContent(
  token: string,
  type: ContentType,
  id: number,
  body: Record<string, unknown>,
): Promise<ContentSummary> {
  return authRequest<ContentSummary>(`/admin/content/${type}/${id}`, token, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export function adminDeleteContent(
  token: string,
  type: ContentType,
  id: number,
): Promise<void> {
  return authRequest<void>(`/admin/content/${type}/${id}`, token, {
    method: "DELETE",
  });
}
