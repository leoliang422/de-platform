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

export interface AnnotationItem {
  id: number;
  user_id: number;
  author_nickname: string;
  author_avatar: string | null;
  parent_id: number | null;
  quote: string;
  anchor_offset: number;
  body: string;
  created_at: string;
}

export function getAnnotations(
  ct: InteractionContentType,
  id: number,
): Promise<AnnotationItem[]> {
  return request<AnnotationItem[]>(`/interactions/${ct}/${id}/annotations`);
}

export function createAnnotation(
  token: string,
  ct: InteractionContentType,
  id: number,
  body: string,
  opts?: { quote?: string; anchorOffset?: number; parentId?: number | null },
): Promise<AnnotationItem> {
  return authRequest<AnnotationItem>(`/interactions/${ct}/${id}/annotations`, token, {
    method: "POST",
    body: JSON.stringify({
      body,
      parent_id: opts?.parentId ?? null,
      quote: opts?.quote ?? "",
      anchor_offset: opts?.anchorOffset ?? 0,
    }),
  });
}

export function deleteAnnotation(token: string, annotationId: number): Promise<void> {
  return authRequest<void>(`/interactions/annotations/${annotationId}`, token, {
    method: "DELETE",
  });
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

// ---- 联系管理员（用户 ↔ 管理员私信） ----
export interface ContactMessage {
  id: number;
  from_admin: boolean;
  body: string;
  attachment_url: string | null;
  attachment_name: string | null;
  attachment_kind: "image" | "file" | null;
  read_at: string | null;
  created_at: string;
}

export interface SendMessagePayload {
  body?: string;
  attachment_url?: string;
  attachment_name?: string;
  attachment_kind?: "image" | "file";
}

export interface AdminConversation {
  user_id: number;
  nickname: string;
  avatar_url: string | null;
  last_body: string;
  last_at: string;
  unread: number;
}

export function getMyMessages(token: string): Promise<ContactMessage[]> {
  return authRequest<ContactMessage[]>("/messages", token);
}

export function getMyMessageUnread(token: string): Promise<{ unread: number }> {
  return authRequest<{ unread: number }>("/messages/unread_count", token);
}

export function sendMessageToAdmin(
  token: string,
  payload: SendMessagePayload,
): Promise<ContactMessage> {
  return authRequest<ContactMessage>("/messages", token, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getAdminConversations(token: string): Promise<AdminConversation[]> {
  return authRequest<AdminConversation[]>("/admin/messages/conversations", token);
}

export function getAdminMessageUnread(token: string): Promise<{ unread: number }> {
  return authRequest<{ unread: number }>("/admin/messages/unread_count", token);
}

export function getAdminConversation(token: string, userId: number): Promise<ContactMessage[]> {
  return authRequest<ContactMessage[]>(`/admin/messages/${userId}`, token);
}

export function replyToUser(
  token: string,
  userId: number,
  payload: SendMessagePayload,
): Promise<ContactMessage> {
  return authRequest<ContactMessage>(`/admin/messages/${userId}`, token, {
    method: "POST",
    body: JSON.stringify(payload),
  });
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

export interface AttachmentUpload {
  url: string;
  filename: string;
  kind: "image" | "file";
}

export async function uploadAttachment(token: string, file: File): Promise<AttachmentUpload> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE_URL}/files/attachment`, {
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
  return (await res.json()) as AttachmentUpload;
}

export interface ExtractResult {
  filename: string;
  kind: "text" | "image" | "document";
  placeholder: boolean;
  text: string;
  url: string | null;
}

export async function extractFile(token: string, file: File): Promise<ExtractResult> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE_URL}/files/extract`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  });
  if (!res.ok) {
    let detail = `解析失败 (${res.status})`;
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      // ignore
    }
    throw new ApiError(res.status, detail);
  }
  return (await res.json()) as ExtractResult;
}

export interface ParseResult {
  target_type: TargetType;
  items: Record<string, unknown>[];
}

export async function parseSubmission(
  token: string,
  input: { targetType: TargetType; text?: string; file?: File | null },
): Promise<ParseResult> {
  const form = new FormData();
  form.append("target_type", input.targetType);
  if (input.text) form.append("text", input.text);
  if (input.file) form.append("file", input.file);
  const res = await fetch(`${API_BASE_URL}/submissions/parse`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  });
  if (!res.ok) {
    let detail = `解析失败 (${res.status})`;
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      // ignore
    }
    throw new ApiError(res.status, detail);
  }
  return (await res.json()) as ParseResult;
}

export function completeAnswer(
  token: string,
  input: { target_type: TargetType; question: string; context?: string },
): Promise<{ answer: string }> {
  return authRequest<{ answer: string }>("/submissions/complete-answer", token, {
    method: "POST",
    body: JSON.stringify(input),
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
  q?: string | null;
  sort?: "hot" | "new";
  page?: number;
  pageSize?: number;
}): Promise<KnowledgeListPage> {
  const p = new URLSearchParams();
  if (opts?.categoryId != null) p.set("category_id", String(opts.categoryId));
  if (opts?.q && opts.q.trim()) p.set("q", opts.q.trim());
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
  answer_md: string | null;
  answer_locked: boolean;
  module_unlocked: boolean;
  free_used: number;
  free_limit: number;
  unlock_points: number;
}

export function getSqlList(categoryId?: number): Promise<SqlListItem[]> {
  const q = categoryId != null ? `?category_id=${categoryId}` : "";
  return request<SqlListItem[]>(`/sql-questions${q}`);
}

export function getSqlDetail(id: number, token?: string | null): Promise<SqlDetail> {
  return request<SqlDetail>(`/sql-questions/${id}`, maybeAuth(token));
}

export function revealSqlAnswer(token: string, id: number): Promise<SqlDetail> {
  return authRequest<SqlDetail>(`/sql-questions/${id}/reveal`, token, { method: "POST" });
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
  position: string;
  interview_type: string | null;
  content_md: string;
  author_id: number | null;
  author_nickname: string;
  author_avatar: string | null;
  rounds_covered: string[];
  qa: InterviewQA[];
  locked: boolean;
}

export interface InterviewTypeGroup {
  interview_type: string;
  count: number;
  posts: InterviewCard[];
}

export interface ModuleAccessInfo {
  unlocked: boolean;
  free_used: number;
  free_limit: number;
  unlock_points: number;
}

export interface InterviewByTypeResponse {
  groups: InterviewTypeGroup[];
  access: ModuleAccessInfo;
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

export function getCompanyInterviewsByType(
  companyId: number,
  token?: string | null,
): Promise<InterviewByTypeResponse> {
  return request<InterviewByTypeResponse>(
    `/companies/${companyId}/interviews-by-type`,
    maybeAuth(token),
  );
}

export function getInterviewDetail(id: number, token?: string | null): Promise<InterviewCard> {
  return request<InterviewCard>(`/interviews/${id}`, maybeAuth(token));
}

/** 当前用户自己上传的面经（可按公司名过滤），本人内容始终可见。 */
export function getMyInterviews(token: string, company?: string): Promise<InterviewCard[]> {
  const q = company ? `?company=${encodeURIComponent(company)}` : "";
  return authRequest<InterviewCard[]>(`/interviews/mine${q}`, token);
}

export function revealInterview(token: string, id: number): Promise<InterviewCard> {
  return authRequest<InterviewCard>(`/interviews/${id}/reveal`, token, { method: "POST" });
}

// ---- 模块级积分访问（sql / interview） ----
export type AccessModule = "sql" | "interview";

export interface ModuleAccess {
  module: string;
  unlocked: boolean;
  free_used: number;
  free_limit: number;
  unlock_points: number;
}

export interface ModuleUnlockResult extends ModuleAccess {
  balance: number;
  already: boolean;
}

export function getModuleAccess(module: AccessModule, token?: string | null): Promise<ModuleAccess> {
  return request<ModuleAccess>(`/access/${module}`, maybeAuth(token));
}

export function unlockModule(token: string, module: AccessModule): Promise<ModuleUnlockResult> {
  return authRequest<ModuleUnlockResult>(`/access/${module}/unlock`, token, { method: "POST" });
}

// ---- 管理端面经目录（公司=文件夹，类型=子文件夹，面经=文件） ----
export interface InterviewPostItem {
  id: number;
  interview_type: string | null;
  status: string;
  label: string;
}

export interface InterviewCompanyNode {
  id: number;
  name: string;
  posts: InterviewPostItem[];
}

export function adminGetInterviewTree(token: string): Promise<InterviewCompanyNode[]> {
  return authRequest<InterviewCompanyNode[]>("/admin/content/interview/tree", token);
}

export function adminCreateCompany(
  token: string,
  name: string,
): Promise<{ id: number; name: string }> {
  return authRequest<{ id: number; name: string }>("/admin/content/interview/company", token, {
    method: "POST",
    body: JSON.stringify({ name }),
  });
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
  position?: string | null;
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

export function deleteSubmission(token: string, id: number): Promise<void> {
  return authRequest<void>(`/submissions/${id}`, token, { method: "DELETE" });
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

export function adminApprove(
  token: string,
  id: number,
  content?: string,
): Promise<Submission> {
  return authRequest<Submission>(`/admin/submissions/${id}/approve`, token, {
    method: "POST",
    body: JSON.stringify({ content: content ?? null }),
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
  input: { section: string; name: string; slug?: string; parent_id?: number | null; order?: number },
): Promise<CategoryFlat> {
  return authRequest<CategoryFlat>("/admin/categories", token, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function adminUpdateCategory(
  token: string,
  id: number,
  input: { name?: string; parent_id?: number | null; order?: number },
): Promise<CategoryFlat> {
  return authRequest<CategoryFlat>(`/admin/categories/${id}`, token, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

export function adminDeleteCategory(token: string, id: number): Promise<void> {
  return authRequest<void>(`/admin/categories/${id}`, token, { method: "DELETE" });
}

// ---- 管理端文件夹树（分类=文件夹，八股/SQL=文件） ----
export interface FolderItem {
  id: number;
  title: string;
  status: string;
}

export interface FolderNode {
  id: number;
  name: string;
  order: number;
  children: FolderNode[];
  items: FolderItem[];
}

export interface FolderTree {
  roots: FolderNode[];
  uncategorized: FolderItem[];
}

export function adminGetFolderTree(token: string, section: string): Promise<FolderTree> {
  return authRequest<FolderTree>(`/admin/categories/tree?section=${section}`, token);
}

export interface CategoryReorderItem {
  id: number;
  parent_id: number | null;
  order: number;
}

export function adminReorderCategories(
  token: string,
  section: string,
  items: CategoryReorderItem[],
): Promise<void> {
  return authRequest<void>("/admin/categories/reorder", token, {
    method: "POST",
    body: JSON.stringify({ section, items }),
  });
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

// ---- Admin 用户权限范围（模块解锁 / 项目解锁）----
export interface AdminModuleAccess {
  module: string;
  label: string;
  unlocked: boolean;
}

export interface AdminProjectAccess {
  id: number;
  title: string;
  access_type: string;
  unlocked: boolean;
}

export interface AdminUserAccess {
  user_id: number;
  modules: AdminModuleAccess[];
  projects: AdminProjectAccess[];
}

export function adminGetUserAccess(token: string, userId: number): Promise<AdminUserAccess> {
  return authRequest<AdminUserAccess>(`/admin/users/${userId}/access`, token);
}

export function adminSetModuleAccess(
  token: string,
  userId: number,
  module: string,
  grant: boolean,
): Promise<AdminUserAccess> {
  return authRequest<AdminUserAccess>(`/admin/users/${userId}/access/module/${module}`, token, {
    method: grant ? "PUT" : "DELETE",
  });
}

export function adminSetProjectAccess(
  token: string,
  userId: number,
  projectId: number,
  grant: boolean,
): Promise<AdminUserAccess> {
  return authRequest<AdminUserAccess>(
    `/admin/users/${userId}/access/project/${projectId}`,
    token,
    { method: grant ? "PUT" : "DELETE" },
  );
}

// ---- Payment / Entitlements ----
// 仅项目采用单条积分解锁（八股免费；SQL/面经为模块级积分门控）。
export type PayableType = "project";
export type UnlockMethod = "points";

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

// ---- 积分充值（人工确认）----
export interface RechargePackage {
  id: number;
  amount: number; // 人民币元
  points: number; // 到账积分
}

export interface RechargeConfig {
  qr_url: string;
  packages: RechargePackage[];
}

export interface RechargeOrder {
  id: number;
  amount_cash: number;
  points_delta: number | null;
  status: string; // pending | paid | failed
  created_at: string;
}

export interface AdminRechargeOrder extends RechargeOrder {
  user_id: number;
  user_nickname: string;
  user_email: string;
}

export function getRechargeConfig(): Promise<RechargeConfig> {
  return request<RechargeConfig>("/payment/recharge/config");
}

export function createRechargeOrder(token: string, packageId: number): Promise<RechargeOrder> {
  return authRequest<RechargeOrder>("/payment/recharge", token, {
    method: "POST",
    body: JSON.stringify({ package_id: packageId }),
  });
}

export function getMyRechargeOrders(token: string): Promise<RechargeOrder[]> {
  return authRequest<RechargeOrder[]>("/payment/recharge/me", token);
}

export function adminListRechargeOrders(
  token: string,
  status = "pending",
): Promise<AdminRechargeOrder[]> {
  return authRequest<AdminRechargeOrder[]>(`/admin/recharge-orders?status=${status}`, token);
}

export function adminConfirmRecharge(token: string, orderId: number): Promise<AdminRechargeOrder> {
  return authRequest<AdminRechargeOrder>(`/admin/recharge-orders/${orderId}/confirm`, token, {
    method: "POST",
  });
}

export function adminRejectRecharge(token: string, orderId: number): Promise<AdminRechargeOrder> {
  return authRequest<AdminRechargeOrder>(`/admin/recharge-orders/${orderId}/reject`, token, {
    method: "POST",
  });
}

export function adminGetRechargeQr(token: string): Promise<{ url: string }> {
  return authRequest<{ url: string }>("/admin/recharge-qr", token);
}

export function adminSetRechargeQr(token: string, url: string): Promise<{ url: string }> {
  return authRequest<{ url: string }>("/admin/recharge-qr", token, {
    method: "PUT",
    body: JSON.stringify({ url }),
  });
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

// ---- Applications（投递记录管理） ----
export type CompanyNature = "state" | "private" | "foreign" | "other";
export type ApplicationStatus =
  | "applied"
  | "resume_fail"
  | "written"
  | "written_fail"
  | "round1"
  | "round1_fail"
  | "round2"
  | "round2_fail"
  | "round3"
  | "round3_fail"
  | "hr"
  | "hr_fail"
  | "rejected"
  | "offer";

export const COMPANY_NATURE_LABEL: Record<string, string> = {
  state: "国央企",
  private: "私企",
  foreign: "外企",
  other: "其他",
};

export const APPLICATION_STATUS_LABEL: Record<string, string> = {
  applied: "已投递",
  resume_fail: "简历挂",
  written: "笔试中",
  written_fail: "笔试挂",
  round1: "一面中",
  round1_fail: "一面挂",
  round2: "二面中",
  round2_fail: "二面挂",
  round3: "三面中",
  round3_fail: "三面挂",
  hr: "HR面中",
  hr_fail: "HR面挂",
  rejected: "已拒",
  offer: "Offer",
};

export interface ApplicationRecord {
  id: number;
  list_id: number;
  company_name: string;
  nature: CompanyNature | null;
  position: string;
  applied_date: string | null;
  status: ApplicationStatus;
  order_index: number;
  interview_company_id: number | null;
}

export interface ApplicationList {
  id: number;
  name: string;
  order_index: number;
  records: ApplicationRecord[];
}

export interface CalendarEvent {
  id: number;
  title: string;
  event_date: string;
  start_time: string | null;
  end_time: string | null;
  note: string | null;
  color: string | null;
}

export interface InterviewCompany {
  id: number;
  name: string;
  post_count: number;
}

export function getApplicationLists(token: string): Promise<ApplicationList[]> {
  return authRequest<ApplicationList[]>("/applications/lists", token);
}

export function getInterviewCompanies(token: string): Promise<InterviewCompany[]> {
  return authRequest<InterviewCompany[]>("/applications/interview-companies", token);
}

export function createApplicationList(token: string, name: string): Promise<ApplicationList> {
  return authRequest<ApplicationList>("/applications/lists", token, {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export function renameApplicationList(
  token: string,
  listId: number,
  name: string,
): Promise<ApplicationList> {
  return authRequest<ApplicationList>(`/applications/lists/${listId}`, token, {
    method: "PATCH",
    body: JSON.stringify({ name }),
  });
}

export function deleteApplicationList(token: string, listId: number): Promise<void> {
  return authRequest<void>(`/applications/lists/${listId}`, token, { method: "DELETE" });
}

export function addApplicationRecord(
  token: string,
  listId: number,
  input: Partial<Omit<ApplicationRecord, "id" | "list_id" | "order_index">>,
): Promise<ApplicationRecord> {
  return authRequest<ApplicationRecord>(`/applications/lists/${listId}/records`, token, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function updateApplicationRecord(
  token: string,
  recordId: number,
  input: Partial<Omit<ApplicationRecord, "id" | "list_id" | "order_index">>,
): Promise<ApplicationRecord> {
  return authRequest<ApplicationRecord>(`/applications/records/${recordId}`, token, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

export function deleteApplicationRecord(token: string, recordId: number): Promise<void> {
  return authRequest<void>(`/applications/records/${recordId}`, token, { method: "DELETE" });
}

export function getCalendarEvents(token: string, month?: string): Promise<CalendarEvent[]> {
  const q = month ? `?month=${encodeURIComponent(month)}` : "";
  return authRequest<CalendarEvent[]>(`/applications/calendar${q}`, token);
}

export function createCalendarEvent(
  token: string,
  input: Omit<CalendarEvent, "id">,
): Promise<CalendarEvent> {
  return authRequest<CalendarEvent>("/applications/calendar", token, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function updateCalendarEvent(
  token: string,
  eventId: number,
  input: Partial<Omit<CalendarEvent, "id">>,
): Promise<CalendarEvent> {
  return authRequest<CalendarEvent>(`/applications/calendar/${eventId}`, token, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

export function deleteCalendarEvent(token: string, eventId: number): Promise<void> {
  return authRequest<void>(`/applications/calendar/${eventId}`, token, { method: "DELETE" });
}
