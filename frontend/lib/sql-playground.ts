// 在线 SQL 判题（PoC）：使用 DuckDB-WASM 在浏览器端执行用户 SQL，
// 与参考解在同一份示例数据上对比结果集，判断是否通过。
// 说明：DuckDB 兼容标准 SQL / 窗口函数；Hive 专有语法（LATERAL VIEW EXPLODE、
// COLLECT_LIST 等）不在本 PoC 支持范围，仅对可用标准 SQL 表达的题目开放。

import type * as DuckDB from "@duckdb/duckdb-wasm";

type AsyncDuckDB = DuckDB.AsyncDuckDB;
type AsyncConn = Awaited<ReturnType<AsyncDuckDB["connect"]>>;

let dbPromise: Promise<AsyncDuckDB> | null = null;

async function getDb(): Promise<AsyncDuckDB> {
  if (!dbPromise) {
    dbPromise = (async () => {
      const duckdb = await import("@duckdb/duckdb-wasm");
      const bundles = duckdb.getJsDelivrBundles();
      const bundle = await duckdb.selectBundle(bundles);
      const workerUrl = URL.createObjectURL(
        new Blob([`importScripts("${bundle.mainWorker}");`], {
          type: "text/javascript",
        }),
      );
      const worker = new Worker(workerUrl);
      const db = new duckdb.AsyncDuckDB(new duckdb.VoidLogger(), worker);
      await db.instantiate(bundle.mainModule, bundle.pthreadWorker);
      URL.revokeObjectURL(workerUrl);
      return db;
    })();
  }
  return dbPromise;
}

export interface QueryResult {
  columns: string[];
  rows: string[][];
}

export interface JudgeResult {
  actual: QueryResult;
  expected: QueryResult;
  pass: boolean;
}

function normalizeCell(v: unknown): string {
  if (v === null || v === undefined) return "∅";
  if (typeof v === "bigint") return v.toString();
  return String(v);
}

function splitStatements(sql: string): string[] {
  return sql
    .split(";")
    .map((s) => s.trim())
    .filter(Boolean);
}

async function runOne(conn: AsyncConn, sql: string): Promise<QueryResult> {
  const table = await conn.query(sql);
  const columns = table.schema.fields.map((f) => f.name);
  const rows = table.toArray().map((r) => {
    const obj = r as unknown as Record<string, unknown>;
    return columns.map((c) => normalizeCell(obj[c]));
  });
  return { columns, rows };
}

// 结果集比对：按“行”做多重集合比较（忽略列名，按列位置比对单元格）。
// ordered=true 时按输出顺序严格比对，否则忽略行序。
function compare(a: QueryResult, b: QueryResult, ordered: boolean): boolean {
  if (a.rows.length !== b.rows.length) return false;
  const aRows = a.rows.map((r) => JSON.stringify(r));
  const bRows = b.rows.map((r) => JSON.stringify(r));
  if (ordered) return aRows.every((r, i) => r === bRows[i]);
  return [...aRows].sort().every((r, i) => r === [...bRows].sort()[i]);
}

export async function runAndJudge(
  setupSql: string,
  solutionSql: string,
  userSql: string,
  ordered: boolean,
): Promise<JudgeResult> {
  const db = await getDb();
  const conn = await db.connect();
  try {
    for (const stmt of splitStatements(setupSql)) {
      await conn.query(stmt);
    }
    const expected = await runOne(conn, solutionSql);
    const actual = await runOne(conn, userSql);
    return { actual, expected, pass: compare(expected, actual, ordered) };
  } finally {
    await conn.close();
  }
}

export interface PlaygroundFixture {
  // 建表 + 造数（用 CREATE OR REPLACE 保证可重复运行）
  setupSql: string;
  // 参考解，用于自动生成“期望结果”
  solutionSql: string;
  // 结果是否要求有序
  ordered: boolean;
  // 编辑器初始内容
  starterSql: string;
}

// PoC 阶段：按题目标题挂载判题夹具（仅收录可用标准 SQL 表达的题）。
export const PLAYGROUND_FIXTURES: Record<string, PlaygroundFixture> = {
  "每个部门薪资前 3 高的员工": {
    ordered: false,
    setupSql: `
CREATE OR REPLACE TABLE emp(emp_id INT, dept_id INT, salary INT);
INSERT INTO emp VALUES (1,10,30000),(2,10,25000),(3,10,25000),(4,10,20000),(5,20,40000);
`,
    solutionSql: `
SELECT dept_id, emp_id, salary
FROM (
  SELECT dept_id, emp_id, salary,
         DENSE_RANK() OVER (PARTITION BY dept_id ORDER BY salary DESC) AS rk
  FROM emp
) t
WHERE rk <= 3;
`,
    starterSql: `-- 表：emp(emp_id, dept_id, salary)
-- 目标：取每个部门薪资前 3 高的员工（并列名次都保留）
-- 请让输出列为：dept_id, emp_id, salary

SELECT dept_id, emp_id, salary
FROM emp
-- 在此补全你的查询…
;`,
  },
  "每门学科第 3 名的学生": {
    ordered: false,
    setupSql: `
CREATE OR REPLACE TABLE score(sid VARCHAR, subject VARCHAR, score INT);
INSERT INTO score VALUES ('A','math',95),('B','math',90),('C','math',85),('D','math',80);
`,
    solutionSql: `
SELECT subject, sid, score
FROM (
  SELECT subject, sid, score,
         DENSE_RANK() OVER (PARTITION BY subject ORDER BY score DESC) AS rk
  FROM score
) t
WHERE rk = 3;
`,
    starterSql: `-- 表：score(sid, subject, score)
-- 目标：取每门学科第 3 高分对应的学生
-- 请让输出列为：subject, sid, score

SELECT subject, sid, score
FROM score
-- 在此补全你的查询…
;`,
  },
};
