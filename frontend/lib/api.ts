const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export interface UserProfile {
  id: number;
  email: string;
  nickname: string;
  role: string;
  points_balance: number;
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

export function getMe(accessToken: string): Promise<UserProfile> {
  return request<UserProfile>("/users/me", {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
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
}

export interface InterviewDetail extends InterviewListItem {
  content_md: string;
}

export function getCompanies(): Promise<Company[]> {
  return request<Company[]>("/companies");
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
  entitlement: Entitlement;
  balance: number;
  already_unlocked: boolean;
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
