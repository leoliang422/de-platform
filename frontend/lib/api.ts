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
      if (body?.detail) detail = body.detail;
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
  content_md: string;
}

export function getKnowledgeList(categoryId?: number): Promise<KnowledgeListItem[]> {
  const q = categoryId != null ? `?category_id=${categoryId}` : "";
  return request<KnowledgeListItem[]>(`/knowledge${q}`);
}

export function getKnowledgeDetail(id: number): Promise<KnowledgeDetail> {
  return request<KnowledgeDetail>(`/knowledge/${id}`);
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

export function getProjectDetail(id: number): Promise<ProjectDetail> {
  return request<ProjectDetail>(`/projects/${id}`);
}
