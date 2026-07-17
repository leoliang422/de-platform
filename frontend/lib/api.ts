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

// ---- Interactions (点赞/收藏/浏览/评论) ----
export type InteractionContentType = "knowledge" | "sql" | "interview" | "project";

export interface InteractionStats {
  content_type: string;
  content_id: number;
  views: number;
  likes: number;
  favorites: number;
  comments: number;
  liked: boolean;
  favorited: boolean;
}

export interface CommentItem {
  id: number;
  user_id: number;
  author_nickname: string;
  author_avatar: string | null;
  parent_id: number | null;
  body: string;
  created_at: string;
}

export interface FavoriteItem {
  content_type: string;
  content_id: number;
  title: string;
  created_at: string;
}

export function getInteractionStats(
  ct: InteractionContentType,
  id: number,
  token?: string | null,
): Promise<InteractionStats> {
  return request<InteractionStats>(`/interactions/${ct}/${id}`, maybeAuth(token));
}

export function toggleLike(
  token: string,
  ct: InteractionContentType,
  id: number,
): Promise<InteractionStats> {
  return authRequest<InteractionStats>(`/interactions/${ct}/${id}/like`, token, {
    method: "POST",
  });
}

export function toggleFavorite(
  token: string,
  ct: InteractionContentType,
  id: number,
): Promise<InteractionStats> {
  return authRequest<InteractionStats>(`/interactions/${ct}/${id}/favorite`, token, {
    method: "POST",
  });
}

export function addView(ct: InteractionContentType, id: number): Promise<{ views: number }> {
  return request<{ views: number }>(`/interactions/${ct}/${id}/view`, { method: "POST" });
}

export function getComments(ct: InteractionContentType, id: number): Promise<CommentItem[]> {
  return request<CommentItem[]>(`/interactions/${ct}/${id}/comments`);
}

export function createComment(
  token: string,
  ct: InteractionContentType,
  id: number,
  body: string,
  parentId?: number | null,
): Promise<CommentItem> {
  return authRequest<CommentItem>(`/interactions/${ct}/${id}/comments`, token, {
    method: "POST",
    body: JSON.stringify({ body, parent_id: parentId ?? null }),
  });
}

export function deleteComment(token: string, commentId: number): Promise<void> {
  return authRequest<void>(`/interactions/comments/${commentId}`, token, { method: "DELETE" });
}

export function getMyFavorites(token: string): Promise<FavoriteItem[]> {
  return authRequest<FavoriteItem[]>("/interactions/me/favorites", token);
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
  views: number;
  likes: number;
  favorites: number;
  comments: number;
  hotness: number;
}

export interface KnowledgeListPage {
  items: KnowledgeListItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface KnowledgeDetail {
  id: number;
  category_id: number | null;
  title: string;
  is_paid: boolean;
  price_cash: string | null;
  price_points: number | null;
  locked: boolean;
  content_md: string | null;
}

export function getKnowledgeList(opts?: {
  categoryId?: number | null;
  sort?: "hot" | "new";
  page?: number;
  pageSize?: number;
}): Promise<KnowledgeListPage> {
  const p = new URLSearchParams();
  if (opts?.categoryId != null) p.set("category_id", String(opts.categoryId));
  if (opts?.sort) p.set("sort", opts.sort);
  if (opts?.page) p.set("page", String(opts.page));
  if (opts?.pageSize) p.set("page_size", String(opts.pageSize));
  const q = p.toString();
  return request<KnowledgeListPage>(`/knowledge${q ? `?${q}` : ""}`);
}

function maybeAuth(token?: string | null): RequestInit {
  return token ? { headers: { Authorization: `Bearer ${token}` } } : {};
}

export function getKnowledgeDetail(id: number, token?: string | null): Promise<KnowledgeDetail> {
  return request<KnowledgeDetail>(`/knowledge/${id}`, maybeAuth(token));
}

// ---- Knowledge Tree（知识树） ----
export interface TreeNode {
  id: number;
  title: string;
  knowledge_item_id: number | null;
  status: string;
  proposer_id: number | null;
  order_index: number;
  children: TreeNode[];
}

export interface PendingNode {
  id: number;
  category_id: number;
  parent_id: number | null;
  parent_title: string | null;
  title: string;
  knowledge_item_id: number | null;
  proposer_id: number | null;
  note: string | null;
  created_at: string;
}

export function getKnowledgeTree(categoryId: number): Promise<TreeNode[]> {
  return request<TreeNode[]>(`/knowledge-tree?category_id=${categoryId}`);
}

export function proposeTreeNode(
  token: string,
  input: { category_id: number; parent_id?: number | null; title: string; note?: string | null },
): Promise<{ id: number; status: string }> {
  return authRequest(`/knowledge-tree/nodes`, token, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function adminGetKnowledgeTree(token: string, categoryId: number): Promise<TreeNode[]> {
  return authRequest<TreeNode[]>(`/admin/knowledge-tree?category_id=${categoryId}`, token);
}

export function adminListPendingNodes(token: string): Promise<PendingNode[]> {
  return authRequest<PendingNode[]>(`/admin/knowledge-tree/pending`, token);
}

export function adminApproveNode(token: string, id: number): Promise<{ status: string }> {
  return authRequest(`/admin/knowledge-tree/${id}/approve`, token, { method: "POST" });
}

export function adminRejectNode(token: string, id: number): Promise<void> {
  return authRequest<void>(`/admin/knowledge-tree/${id}/reject`, token, { method: "POST" });
}

export function adminCreateTreeNode(
  token: string,
  input: {
    category_id: number;
    parent_id?: number | null;
    title: string;
    knowledge_item_id?: number | null;
    order_index?: number;
  },
): Promise<{ id: number; status: string }> {
  return authRequest(`/admin/knowledge-tree/nodes`, token, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function adminUpdateTreeNode(
  token: string,
  id: number,
  input: {
    title?: string;
    parent_id?: number | null;
    knowledge_item_id?: number | null;
    order_index?: number;
    status?: string;
  },
): Promise<{ id: number; status: string }> {
  return authRequest(`/admin/knowledge-tree/${id}`, token, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

export function adminDeleteTreeNode(token: string, id: number): Promise<void> {
  return authRequest<void>(`/admin/knowledge-tree/${id}`, token, { method: "DELETE" });
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

export interface InterviewQA {
  id: number;
  section: string;
  order_index: number;
  question: string;
  answer: string;
}

export interface InterviewCard {
  id: number;
  company_id: number;
  title: string;
  interview_type: string | null;
  content_md: string;
  author_id: number | null;
  author_nickname: string;
  author_avatar: string | null;
  rounds_covered: string[];
  qa: InterviewQA[];
}

export interface InterviewTypeGroup {
  interview_type: string;
  count: number;
  posts: InterviewCard[];
}

export const INTERVIEW_TYPE_LABEL: Record<string, string> = {
  daily: "日常实习",
  summer: "暑期实习",
  campus: "校招",
  social: "社招",
  other: "其他",
};

// 展示顺序：日常实习 → 暑期实习 → 校招 → 社招
export const INTERVIEW_TYPE_ORDER = ["daily", "summer", "campus", "social", "other"];

export const INTERVIEW_ROUND_LABEL: Record<string, string> = {
  round1: "一面",
  round2: "二面",
  round3: "三面",
  hr: "HR面",
};

export const INTERVIEW_ROUND_ORDER = ["round1", "round2", "round3", "hr"];

export function getCompanies(): Promise<Company[]> {
  return request<Company[]>("/companies");
}

export function getCompanyInterviewsByType(companyId: number): Promise<InterviewTypeGroup[]> {
  return request<InterviewTypeGroup[]>(`/companies/${companyId}/interviews-by-type`);
}

export function getInterviewDetail(id: number): Promise<InterviewCard> {
  return request<InterviewCard>(`/interviews/${id}`);
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
  section: "round1" | "round2" | "round3" | "hr";
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
  interview_type?: "social" | "campus" | "daily" | "summer" | null;
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

// ---- Admin 用户管理 ----
export interface AdminUser {
  id: number;
  email: string;
  nickname: string;
  role: string;
  points_balance: number;
  created_at: string;
}

export function adminListUsers(token: string, q?: string): Promise<AdminUser[]> {
  const qs = q ? `?q=${encodeURIComponent(q)}` : "";
  return authRequest<AdminUser[]>(`/admin/users${qs}`, token);
}

export function adminUpdateUser(
  token: string,
  id: number,
  input: {
    role?: string;
    set_points?: number;
    delta_points?: number;
    reason?: string;
  },
): Promise<AdminUser> {
  return authRequest<AdminUser>(`/admin/users/${id}`, token, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
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
