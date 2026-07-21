"""填充 SQL 题库：按题型分类的一批原创高频面试题（问题 / 求解思路 / Hive SQL）。

内容为原创撰写，取材于行业通用 SQL 面试考点（连续区间、留存漏斗、分组 TopN、
行列转换、同比环比、聚合去重等），不复制任何第三方站点文字，可安全公开发布。

幂等：
- 题型分类按 (section='sql', slug) get-or-create；
- 题目按 title 去重，已存在则跳过。

运行（本地 SQLite）：
    cd backend
    export DATABASE_URL="sqlite+aiosqlite:///./dev.db"
    python -m scripts.seed_sql_bank

运行（线上，示例 Neon/Postgres，注意用 asyncpg 驱动）：
    export DATABASE_URL="postgresql+asyncpg://USER:PWD@HOST/DB?ssl=require"
    python -m scripts.seed_sql_bank
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import app.models  # noqa: F401  (register models)
from app.core.database import SessionLocal
from app.modules.catalog.models import Category
from app.modules.sql_bank.models import SqlQuestion

# 题型分类（section='sql'）：合并相似题到同一题型，覆盖数据开发常见 SQL 面试题型。
CATEGORIES: list[dict[str, object]] = [
    {"slug": "continuous", "name": "连续 · 区间 · 序列", "order": 1},
    {"slug": "retention-funnel", "name": "留存与漏斗", "order": 2},
    {"slug": "group-topn", "name": "分组 TopN 与排名", "order": 3},
    {"slug": "pivot", "name": "行列转换", "order": 4},
    {"slug": "trend-cumulative", "name": "同比环比与累计", "order": 5},
    {"slug": "aggregate", "name": "聚合与去重", "order": 6},
    {"slug": "session-path", "name": "会话切分与行为路径", "order": 7},
    {"slug": "concurrency", "name": "同时在线与并发", "order": 8},
    {"slug": "graph-relation", "name": "图与关系（好友）", "order": 9},
    {"slug": "ratio-metric", "name": "比率与实验指标", "order": 10},
]


def _q(
    cat: str, title: str, difficulty: str, tags: str, prompt: str, answer: str
) -> dict[str, str]:
    return {
        "cat": cat,
        "title": title,
        "difficulty": difficulty,
        "tags": tags,
        "prompt_md": prompt.strip() + "\n",
        "answer_md": answer.strip() + "\n",
    }


QUESTIONS: list[dict[str, str]] = [
    # ---------------- 连续与区间 ----------------
    _q(
        "continuous",
        "每个用户的最长连续登录天数",
        "medium",
        "连续区间,窗口函数,row_number",
        """
给定登录表 `login`：

| 字段 | 说明 |
| --- | --- |
| uid | 用户 ID |
| dt | 登录日期（可能同一天多条） |

**要求**：求每个用户历史上的**最长连续登录天数**（自然日连续）。
""",
        """
## 求解思路

1. 先对 `(uid, dt)` 去重，避免同一天多条影响计数。
2. 按用户分区、日期升序取行号 `rn`，则 `dt - rn` 对同一段连续日期是常量，可作分组键 `grp`。
3. 按 `(uid, grp)` 计数即得每段连续长度，再对每个用户取最大值。

## 参考 SQL（Hive / Spark SQL）

```sql
SELECT uid, MAX(streak) AS max_streak
FROM (
  SELECT uid, grp, COUNT(*) AS streak
  FROM (
    SELECT uid, dt,
           DATE_SUB(dt, ROW_NUMBER() OVER (PARTITION BY uid ORDER BY dt)) AS grp
    FROM (SELECT DISTINCT uid, dt FROM login) d
  ) t
  GROUP BY uid, grp
) s
GROUP BY uid;
```
""",
    ),
    _q(
        "continuous",
        "存在连续 3 天 GMV 严格递增的商户",
        "hard",
        "连续区间,lag,自连接",
        """
给定商户日成交表 `sales`：

| 字段 | 说明 |
| --- | --- |
| shop_id | 商户 ID |
| dt | 日期 |
| gmv | 当日成交额 |

**要求**：找出**存在连续 3 个自然日 GMV 严格递增**的商户。
""",
        """
## 求解思路

1. 用 `LAG` 取每行前 1 天、前 2 天的日期与 GMV。
2. 要求日期严格相邻（`DATEDIFF=1`）且 GMV 逐日严格递增。
3. 命中的商户去重即可。

## 参考 SQL（Hive / Spark SQL）

```sql
SELECT DISTINCT shop_id
FROM (
  SELECT shop_id, dt, gmv,
         LAG(gmv, 1) OVER (PARTITION BY shop_id ORDER BY dt) AS gmv1,
         LAG(dt,  1) OVER (PARTITION BY shop_id ORDER BY dt) AS dt1,
         LAG(gmv, 2) OVER (PARTITION BY shop_id ORDER BY dt) AS gmv2,
         LAG(dt,  2) OVER (PARTITION BY shop_id ORDER BY dt) AS dt2
  FROM sales
) t
WHERE DATEDIFF(dt, dt1) = 1 AND DATEDIFF(dt1, dt2) = 1
  AND gmv > gmv1 AND gmv1 > gmv2;
```
""",
    ),
    _q(
        "continuous",
        "合并用户重叠的活跃区间",
        "hard",
        "区间合并,窗口函数,累计求和",
        """
给定活跃区间表 `activity`（同一用户区间可能重叠或相邻）：

| 字段 | 说明 |
| --- | --- |
| uid | 用户 ID |
| start_dt | 区间开始日期 |
| end_dt | 区间结束日期 |

**要求**：把每个用户**重叠或相邻的区间合并**，输出合并后的区间。
""",
        """
## 求解思路

1. 按 `start_dt` 排序，用窗口取「当前行之前所有区间的最大 end」（前缀最大结束日）。
2. 若当前 `start_dt` 大于前缀最大结束日，说明与前面断开，是新区间起点，标记 `is_new=1`。
3. 对 `is_new` 做累计求和得到区间分组号 `seg_id`，按组取 `MIN(start)`、`MAX(end)`。

## 参考 SQL（Hive / Spark SQL）

```sql
SELECT uid, MIN(start_dt) AS seg_start, MAX(end_dt) AS seg_end
FROM (
  SELECT uid, start_dt, end_dt,
         SUM(is_new) OVER (PARTITION BY uid ORDER BY start_dt
                           ROWS UNBOUNDED PRECEDING) AS seg_id
  FROM (
    SELECT uid, start_dt, end_dt,
           CASE WHEN start_dt <= MAX(end_dt) OVER (
                       PARTITION BY uid ORDER BY start_dt
                       ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING)
                THEN 0 ELSE 1 END AS is_new
    FROM activity
  ) t
) s
GROUP BY uid, seg_id;
```
""",
    ),
    _q(
        "continuous",
        "允许间断 1 天的最长活跃跨度",
        "hard",
        "连续区间,分段,datediff",
        """
给定登录表 `login(uid, dt)`。定义：相邻两次登录**间隔不超过 2 天**（即最多断 1 天）
视为同一段活跃。

**要求**：求每个用户活跃段覆盖的**最长天数跨度**（段内最晚日期 − 最早日期 + 1）。
""",
        """
## 求解思路

1. `(uid, dt)` 去重后按日期排序，用 `LAG` 取上一次登录日期。
2. 若与上一次间隔 `> 2` 天则开启新段（`is_new=1`），累计求和得段号 `seg_id`。
3. 每段取 `MIN(dt)`、`MAX(dt)`，跨度 = `DATEDIFF(max, min) + 1`，再对用户取最大。

## 参考 SQL（Hive / Spark SQL）

```sql
SELECT uid, MAX(DATEDIFF(seg_end, seg_start) + 1) AS max_span
FROM (
  SELECT uid, seg_id, MIN(dt) AS seg_start, MAX(dt) AS seg_end
  FROM (
    SELECT uid, dt,
           SUM(is_new) OVER (PARTITION BY uid ORDER BY dt
                             ROWS UNBOUNDED PRECEDING) AS seg_id
    FROM (
      SELECT uid, dt,
             CASE WHEN DATEDIFF(dt, LAG(dt) OVER (PARTITION BY uid ORDER BY dt)) <= 2
                  THEN 0 ELSE 1 END AS is_new
      FROM (SELECT DISTINCT uid, dt FROM login) d
    ) t
  ) g
  GROUP BY uid, seg_id
) s
GROUP BY uid;
```
""",
    ),
    _q(
        "continuous",
        "识别股价的波峰与波谷",
        "medium",
        "序列,相邻比较,lag,lead",
        """
给定股价表 `stock(dt, price)`（每天一条）。

**要求**：找出所有**波峰**（比前一天、后一天都高）和**波谷**（比前一天、后一天都低）的日期。
""",
        """
## 求解思路

1. 用 `LAG` 取前一天价格、`LEAD` 取后一天价格。
2. 当天价格同时大于前后即为波峰，同时小于前后即为波谷。
3. 首尾两天没有完整前后邻居，天然不会命中（`LAG/LEAD` 为 NULL）。

## 参考 SQL（Hive / Spark SQL）

```sql
SELECT dt, price,
       CASE WHEN price > prev AND price > next THEN 'peak'
            WHEN price < prev AND price < next THEN 'valley' END AS point_type
FROM (
  SELECT dt, price,
         LAG(price)  OVER (ORDER BY dt) AS prev,
         LEAD(price) OVER (ORDER BY dt) AS next
  FROM stock
) t
WHERE (price > prev AND price > next)
   OR (price < prev AND price < next);
```
""",
    ),
    # ---------------- 留存与漏斗 ----------------
    _q(
        "retention-funnel",
        "每日次日留存率",
        "medium",
        "留存,自连接,datediff",
        """
给定登录表 `login(uid, dt)`。

**要求**：按天计算**次日留存率** = 当天活跃且次日仍活跃的用户数 / 当天活跃用户数。
""",
        """
## 求解思路

1. 用登录表自连接：`b.dt` 比 `a.dt` 晚 1 天且为同一用户。
2. 当天活跃用户数用 `COUNT(DISTINCT a.uid)`，次日仍活跃用 `COUNT(DISTINCT b.uid)`。
3. 相除即得次日留存率（用 `LEFT JOIN` 保证当天无留存的日期也出现）。

## 参考 SQL（Hive / Spark SQL）

```sql
SELECT a.dt,
       COUNT(DISTINCT a.uid) AS dau,
       COUNT(DISTINCT b.uid) AS retained,
       ROUND(COUNT(DISTINCT b.uid) / COUNT(DISTINCT a.uid), 4) AS retention_1d
FROM login a
LEFT JOIN login b
  ON a.uid = b.uid AND DATEDIFF(b.dt, a.dt) = 1
GROUP BY a.dt;
```
""",
    ),
    _q(
        "retention-funnel",
        "新增用户的 1/3/7 日留存率",
        "medium",
        "留存,新增用户,条件聚合",
        """
给定注册表 `user_reg(uid, reg_dt)` 与登录表 `login(uid, dt)`。

**要求**：按注册日期分组，计算新增用户的**第 1 / 3 / 7 日留存率**。
""",
        """
## 求解思路

1. 以注册记录为基准 `LEFT JOIN` 登录记录。
2. 用 `DATEDIFF(登录日, 注册日)` 判断是第几日活跃，配合 `COUNT(DISTINCT IF(...))` 做条件去重计数。
3. 各留存数除以当日新增用户数。

## 参考 SQL（Hive / Spark SQL）

```sql
SELECT r.reg_dt,
       COUNT(DISTINCT r.uid) AS new_users,
       ROUND(COUNT(DISTINCT IF(DATEDIFF(l.dt, r.reg_dt) = 1, l.uid, NULL))
             / COUNT(DISTINCT r.uid), 4) AS retention_1d,
       ROUND(COUNT(DISTINCT IF(DATEDIFF(l.dt, r.reg_dt) = 3, l.uid, NULL))
             / COUNT(DISTINCT r.uid), 4) AS retention_3d,
       ROUND(COUNT(DISTINCT IF(DATEDIFF(l.dt, r.reg_dt) = 7, l.uid, NULL))
             / COUNT(DISTINCT r.uid), 4) AS retention_7d
FROM user_reg r
LEFT JOIN login l ON r.uid = l.uid
GROUP BY r.reg_dt;
```
""",
    ),
    _q(
        "retention-funnel",
        "注册→下单→支付 转化漏斗",
        "medium",
        "漏斗,条件聚合,转化率",
        """
给定事件表 `events(uid, event, event_time)`，`event` 取值 `register` / `order` / `pay`。

**要求**：统计三步漏斗的**去重人数**及相邻步骤的**转化率**。
""",
        """
## 求解思路

1. 用 `COUNT(DISTINCT IF(event=..., uid, NULL))` 分别统计各步去重人数。
2. 相邻步骤人数相除得转化率。
3. 若需严格时序（先注册后下单再支付），可先按 `uid` 聚合各事件的最早时间，再比较大小后计数。

## 参考 SQL（Hive / Spark SQL）

```sql
SELECT
  COUNT(DISTINCT IF(event = 'register', uid, NULL)) AS step_register,
  COUNT(DISTINCT IF(event = 'order',    uid, NULL)) AS step_order,
  COUNT(DISTINCT IF(event = 'pay',      uid, NULL)) AS step_pay,
  ROUND(COUNT(DISTINCT IF(event = 'order', uid, NULL))
        / COUNT(DISTINCT IF(event = 'register', uid, NULL)), 4) AS reg_to_order,
  ROUND(COUNT(DISTINCT IF(event = 'pay', uid, NULL))
        / COUNT(DISTINCT IF(event = 'order', uid, NULL)), 4) AS order_to_pay
FROM events;
```
""",
    ),
    # ---------------- 分组 TopN 与排名 ----------------
    _q(
        "group-topn",
        "每个部门薪资前 3 高的员工",
        "medium",
        "TopN,dense_rank,分组排名",
        """
给定员工表 `emp(emp_id, dept_id, salary)`。

**要求**：取出**每个部门薪资最高的前 3 名**（并列名次都保留）。
""",
        """
## 求解思路

1. 按部门分区、薪资降序，用 `DENSE_RANK` 计算名次（并列同名次，不跳号）。
2. 过滤名次 `<= 3`。若并列不保留、严格取 3 人，可改用 `ROW_NUMBER`。

## 参考 SQL（Hive / Spark SQL）

```sql
SELECT dept_id, emp_id, salary
FROM (
  SELECT dept_id, emp_id, salary,
         DENSE_RANK() OVER (PARTITION BY dept_id ORDER BY salary DESC) AS rk
  FROM emp
) t
WHERE rk <= 3;
```
""",
    ),
    _q(
        "group-topn",
        "每个品类销售额 Top2 商品及占比",
        "medium",
        "TopN,窗口占比,分组",
        """
给定销售明细 `sku_sales(cat_id, sku_id, amount)`。

**要求**：取每个品类**销售额前 2 的商品**，并计算其销售额**占该品类总额的比例**。
""",
        """
## 求解思路

1. 先按 `(cat_id, sku_id)` 汇总销售额。
2. 用窗口 `SUM() OVER (PARTITION BY cat_id)` 得品类总额，`ROW_NUMBER()` 得品类内排名。
3. 过滤排名 `<= 2`，用商品额 / 品类总额得占比。

## 参考 SQL（Hive / Spark SQL）

```sql
SELECT cat_id, sku_id, amount,
       ROUND(amount / cat_total, 4) AS ratio
FROM (
  SELECT cat_id, sku_id, amount,
         SUM(amount) OVER (PARTITION BY cat_id) AS cat_total,
         ROW_NUMBER() OVER (PARTITION BY cat_id ORDER BY amount DESC) AS rn
  FROM (
    SELECT cat_id, sku_id, SUM(amount) AS amount
    FROM sku_sales
    GROUP BY cat_id, sku_id
  ) g
) t
WHERE rn <= 2;
```
""",
    ),
    _q(
        "group-topn",
        "每门学科第 3 名的学生",
        "medium",
        "分组排名,dense_rank",
        """
给定成绩表 `score(sid, subject, score)`。

**要求**：取出**每门学科第 3 高分**对应的学生（并列第 3 都保留）。
""",
        """
## 求解思路

1. 按学科分区、成绩降序用 `DENSE_RANK` 排名。
2. 过滤名次等于 3 即可。

## 参考 SQL（Hive / Spark SQL）

```sql
SELECT subject, sid, score
FROM (
  SELECT subject, sid, score,
         DENSE_RANK() OVER (PARTITION BY subject ORDER BY score DESC) AS rk
  FROM score
) t
WHERE rk = 3;
```
""",
    ),
    # ---------------- 行列转换 ----------------
    _q(
        "pivot",
        "成绩表行转列",
        "medium",
        "行转列,条件聚合",
        """
给定成绩表 `score(sid, subject, score)`，`subject` 取值 `chinese` / `math` / `english`。

**要求**：转成**每个学生一行**，三科成绩各占一列。
""",
        """
## 求解思路

1. 按 `sid` 分组。
2. 用 `MAX(IF(subject=..., score, NULL))` 把每一科的分数「挑」到对应列上。

## 参考 SQL（Hive / Spark SQL）

```sql
SELECT sid,
       MAX(IF(subject = 'chinese', score, NULL)) AS chinese,
       MAX(IF(subject = 'math',    score, NULL)) AS math,
       MAX(IF(subject = 'english', score, NULL)) AS english
FROM score
GROUP BY sid;
```
""",
    ),
    _q(
        "pivot",
        "逗号分隔标签列转行",
        "medium",
        "列转行,explode,lateral view",
        """
给定用户标签表 `user_tags(uid, tags)`，`tags` 为逗号分隔字符串，如 `"数仓,实时,调优"`。

**要求**：把标签**拆成每行一个**（uid, tag）。
""",
        """
## 求解思路

1. `SPLIT(tags, ',')` 得到数组。
2. `LATERAL VIEW EXPLODE(...)` 把数组炸开成多行。

## 参考 SQL（Hive / Spark SQL）

```sql
SELECT uid, tag
FROM user_tags
LATERAL VIEW EXPLODE(SPLIT(tags, ',')) t AS tag;
```
""",
    ),
    _q(
        "pivot",
        "用户访问路径按序拼接",
        "medium",
        "有序拼接,collect_list,sort by",
        """
给定浏览表 `page_view(uid, page, view_time)`。

**要求**：把每个用户访问过的页面**按时间顺序**拼成路径字符串，如 `home>list>detail`。
""",
        """
## 求解思路

1. `COLLECT_LIST` 只在数据「有序进入 reducer」时才保序，
   因此先按 `DISTRIBUTE BY uid SORT BY uid, view_time` 排序。
2. 再按 `uid` 分组，用 `CONCAT_WS('>', COLLECT_LIST(page))` 拼接。

## 参考 SQL（Hive / Spark SQL）

```sql
SELECT uid, CONCAT_WS('>', COLLECT_LIST(page)) AS path
FROM (
  SELECT uid, page, view_time
  FROM page_view
  DISTRIBUTE BY uid SORT BY uid, view_time
) t
GROUP BY uid;
```
""",
    ),
    # ---------------- 同比环比与累计 ----------------
    _q(
        "trend-cumulative",
        "月度销售额同比与环比",
        "hard",
        "同比,环比,lag",
        """
给定成交表 `sales(dt, amount)`（`dt` 为日期）。

**要求**：按**月**汇总销售额，并计算**环比**（较上月）与**同比**（较去年同月）增长率。
""",
        """
## 求解思路

1. 用 `SUBSTR(dt, 1, 7)` 取「年-月」聚合出月度销售额。
2. 按月份排序，`LAG(amount, 1)` 取上月、`LAG(amount, 12)` 取去年同月。
3. 增长率 = 本期 / 上期 − 1。注意月份连续无缺失时 `LAG(…,12)` 才恰好对齐去年同月。

## 参考 SQL（Hive / Spark SQL）

```sql
SELECT ym, amount,
       ROUND(amount / LAG(amount, 1)  OVER (ORDER BY ym) - 1, 4) AS mom,
       ROUND(amount / LAG(amount, 12) OVER (ORDER BY ym) - 1, 4) AS yoy
FROM (
  SELECT SUBSTR(dt, 1, 7) AS ym, SUM(amount) AS amount
  FROM sales
  GROUP BY SUBSTR(dt, 1, 7)
) m;
```
""",
    ),
    _q(
        "trend-cumulative",
        "累计销售额及占全期比例",
        "medium",
        "累计,窗口帧,占比",
        """
给定成交表 `sales(dt, amount)`。

**要求**：按日期输出**累计销售额**（含当天及之前），以及累计额**占全期总额的比例**。
""",
        """
## 求解思路

1. 先按天汇总。
2. `SUM() OVER (ORDER BY dt ROWS UNBOUNDED PRECEDING)` 得累计额；`SUM() OVER ()` 得全期总额。
3. 两者相除得累计占比。

## 参考 SQL（Hive / Spark SQL）

```sql
SELECT dt, amount,
       SUM(amount) OVER (ORDER BY dt ROWS UNBOUNDED PRECEDING) AS cum_amount,
       ROUND(SUM(amount) OVER (ORDER BY dt ROWS UNBOUNDED PRECEDING)
             / SUM(amount) OVER (), 4) AS cum_ratio
FROM (
  SELECT dt, SUM(amount) AS amount
  FROM sales
  GROUP BY dt
) d;
```
""",
    ),
    _q(
        "trend-cumulative",
        "近 7 日移动平均活跃数",
        "medium",
        "移动平均,窗口帧",
        """
给定日活表 `dau(dt, cnt)`。

**要求**：计算每一天的**近 7 日（含当天）移动平均**活跃数。
""",
        """
## 求解思路

1. 按日期排序，用滑动窗口帧 `ROWS BETWEEN 6 PRECEDING AND CURRENT ROW`。
2. 对 `cnt` 求 `AVG` 即为近 7 日移动平均（起始不足 7 天时按实际天数计算）。

## 参考 SQL（Hive / Spark SQL）

```sql
SELECT dt, cnt,
       ROUND(AVG(cnt) OVER (ORDER BY dt
             ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 2) AS ma7
FROM dau;
```
""",
    ),
    # ---------------- 聚合与去重 ----------------
    _q(
        "aggregate",
        "去掉一个最高分和最低分求平均",
        "easy",
        "聚合,去极值",
        """
给定成绩表 `score(sid, subject, score)`。

**要求**：每门学科**去掉一个最高分和一个最低分**后求平均分。
""",
        """
## 求解思路

1. 直接用聚合：总分减去最高最低，除以（人数 − 2）。
2. 用 `HAVING COUNT(*) > 2` 排除人数不足的学科，避免除零。

## 参考 SQL（Hive / Spark SQL）

```sql
SELECT subject,
       ROUND((SUM(score) - MAX(score) - MIN(score)) / (COUNT(*) - 2), 2) AS avg_trimmed
FROM score
GROUP BY subject
HAVING COUNT(*) > 2;
```
""",
    ),
    _q(
        "aggregate",
        "每门学科成绩中位数",
        "hard",
        "中位数,percentile",
        """
给定成绩表 `score(subject, score)`。

**要求**：求**每门学科的成绩中位数**。
""",
        """
## 求解思路

1. Hive/Spark 可直接用 `PERCENTILE`（精确，需整型）计算 0.5 分位。
2. 大数据量下可用 `PERCENTILE_APPROX(score, 0.5)` 近似加速。

## 参考 SQL（Hive / Spark SQL）

```sql
SELECT subject,
       PERCENTILE(CAST(score AS BIGINT), 0.5) AS median
FROM score
GROUP BY subject;

-- 近似版本（大数据量）
-- SELECT subject, PERCENTILE_APPROX(score, 0.5) AS median FROM score GROUP BY subject;
```
""",
    ),
    _q(
        "aggregate",
        "每个用户的首单与末单",
        "easy",
        "去重,row_number,首末记录",
        """
给定订单表 `orders(uid, order_id, order_time, amount)`。

**要求**：取出每个用户**最早**和**最晚**的一笔订单，并标注是 `first` 还是 `last`。
""",
        """
## 求解思路

1. 同一子查询里开两个 `ROW_NUMBER`：一个按时间升序、一个按时间降序。
2. 过滤「升序第 1」或「降序第 1」，并用 `CASE` 标注首末。

## 参考 SQL（Hive / Spark SQL）

```sql
SELECT uid, order_id, order_time, amount,
       CASE WHEN rn_first = 1 THEN 'first' ELSE 'last' END AS flag
FROM (
  SELECT uid, order_id, order_time, amount,
         ROW_NUMBER() OVER (PARTITION BY uid ORDER BY order_time ASC)  AS rn_first,
         ROW_NUMBER() OVER (PARTITION BY uid ORDER BY order_time DESC) AS rn_last
  FROM orders
) t
WHERE rn_first = 1 OR rn_last = 1;
```
""",
    ),
    _q(
        "aggregate",
        "明细去重保留最新一条",
        "easy",
        "去重,row_number,拉链",
        """
给定用户档案流水 `user_profile(uid, name, update_time)`，同一 `uid` 有多条历史。

**要求**：每个 `uid` 只保留 `update_time` **最新的一条**。
""",
        """
## 求解思路

1. 按 `uid` 分区、`update_time` 降序用 `ROW_NUMBER` 打标。
2. 取 `rn = 1` 即最新一条（这是数仓「取最新快照」的通用写法）。

## 参考 SQL（Hive / Spark SQL）

```sql
SELECT uid, name, update_time
FROM (
  SELECT uid, name, update_time,
         ROW_NUMBER() OVER (PARTITION BY uid ORDER BY update_time DESC) AS rn
  FROM user_profile
) t
WHERE rn = 1;
```
""",
    ),
    # ---------------- 会话切分与行为路径 ----------------
    _q(
        "session-path",
        "按 30 分钟间隔切分会话（Session）",
        "hard",
        "session,分段,时间差,窗口函数",
        """
给定行为流水 `page_view(uid, view_time)`。定义：同一用户相邻两次行为**间隔超过 30 分钟**
即切分为新会话。

**要求**：求每个用户的**会话（session）数量**。
""",
        """
## 求解思路

1. 按用户、时间排序，用 `LAG` 取上一条行为时间。
2. 若与上一条间隔 `> 1800` 秒（或本行是该用户首条，`LAG` 为 NULL）则开启新会话 `is_new=1`。
3. 对 `is_new` 累计求和得会话号，用户维度取最大会话号即为会话数。

## 参考 SQL（Hive / Spark SQL）

```sql
SELECT uid, MAX(session_id) AS session_cnt
FROM (
  SELECT uid,
         SUM(is_new) OVER (PARTITION BY uid ORDER BY view_time
                           ROWS UNBOUNDED PRECEDING) AS session_id
  FROM (
    SELECT uid, view_time,
           CASE WHEN LAG(view_time) OVER (PARTITION BY uid ORDER BY view_time) IS NULL
                     OR UNIX_TIMESTAMP(view_time)
                        - UNIX_TIMESTAMP(LAG(view_time) OVER (PARTITION BY uid ORDER BY view_time))
                        > 1800
                THEN 1 ELSE 0 END AS is_new
    FROM page_view
  ) t
) s
GROUP BY uid;
```
""",
    ),
    # ---------------- 同时在线与并发 ----------------
    _q(
        "concurrency",
        "直播间历史最大同时在线人数",
        "hard",
        "并发,事件流,前缀和,扫描线",
        """
给定观看记录 `live_session(uid, enter_time, leave_time)`。

**要求**：求该直播间**历史最大同时在线人数**。
""",
        """
## 求解思路

1. 把每条观看拆成两个事件：进入 `+1`、离开 `-1`。
2. 按时间排序做前缀和（在线人数随事件累加）；同一时刻**先进后出**
   （`+1` 排在 `-1` 前，避免瞬时低估）。
3. 前缀和的最大值即最大同时在线人数。

## 参考 SQL（Hive / Spark SQL）

```sql
SELECT MAX(online) AS max_online
FROM (
  SELECT SUM(delta) OVER (ORDER BY ts, delta DESC
                          ROWS UNBOUNDED PRECEDING) AS online
  FROM (
    SELECT enter_time AS ts,  1 AS delta FROM live_session
    UNION ALL
    SELECT leave_time AS ts, -1 AS delta FROM live_session
  ) e
) t;
```
""",
    ),
    # ---------------- 图与关系（好友） ----------------
    _q(
        "graph-relation",
        "共同好友数最多的用户对 TopN",
        "medium",
        "自连接,共同好友,图关系",
        """
给定好友表 `friend(uid, fid)`，表示 `uid` 与 `fid` 是好友。

**要求**：计算任意两个用户的**共同好友数**，取共同好友最多的 Top 10 用户对。
""",
        """
## 求解思路

1. 对好友表按同一个好友 `fid` 自连接：两个不同用户共享同一个 `fid` 即拥有一个共同好友。
2. 用 `a.uid < b.uid` 去重（避免 (A,B) 与 (B,A) 重复、并排除自己）。
3. 按用户对分组计数，排序取 TopN。

## 参考 SQL（Hive / Spark SQL）

```sql
SELECT a.uid AS u1, b.uid AS u2, COUNT(*) AS common_friends
FROM friend a
JOIN friend b ON a.fid = b.fid AND a.uid < b.uid
GROUP BY a.uid, b.uid
ORDER BY common_friends DESC
LIMIT 10;
```
""",
    ),
    _q(
        "graph-relation",
        "互相关注的用户对",
        "medium",
        "自连接,双向关系,图关系",
        """
给定关注表 `follow(follower, followee)`，表示 `follower` 关注了 `followee`（单向）。

**要求**：找出所有**互相关注**的用户对。
""",
        """
## 求解思路

1. 关注表自连接：若存在 `(A→B)` 且 `(B→A)` 两条记录，则 A、B 互相关注。
2. 连接条件为 `a.follower = b.followee AND a.followee = b.follower`。
3. 用 `a.follower < a.followee` 去重每对只留一条。

## 参考 SQL（Hive / Spark SQL）

```sql
SELECT a.follower AS u1, a.followee AS u2
FROM follow a
JOIN follow b
  ON a.follower = b.followee AND a.followee = b.follower
WHERE a.follower < a.followee;
```
""",
    ),
    # ---------------- 比率与实验指标 ----------------
    _q(
        "ratio-metric",
        "用户复购率",
        "medium",
        "复购率,比率指标,条件计数",
        """
给定订单表 `orders(uid, order_date)`。定义**复购用户**为下单次数 ≥ 2 的用户。

**要求**：计算**复购率** = 复购用户数 / 有过下单的用户数。
""",
        """
## 求解思路

1. 先按 `uid` 统计下单次数。
2. 分子为下单次数 ≥ 2 的用户数，分母为全部下单用户数，相除即复购率。

## 参考 SQL（Hive / Spark SQL）

```sql
SELECT ROUND(COUNT(IF(order_cnt >= 2, uid, NULL)) / COUNT(uid), 4) AS repurchase_rate
FROM (
  SELECT uid, COUNT(*) AS order_cnt
  FROM orders
  GROUP BY uid
) t;
```
""",
    ),
    _q(
        "ratio-metric",
        "AB 实验各组转化率对比",
        "medium",
        "AB实验,转化率,分组聚合",
        """
给定实验日志 `ab_log(uid, group_name, is_convert)`，`group_name` 为实验组（如 `A` / `B`），
`is_convert` 为该用户是否转化（1/0）。

**要求**：计算**每个实验组的转化率**（转化用户数 / 参与用户数）。
""",
        """
## 求解思路

1. 按 `group_name` 分组。
2. 参与用户数用 `COUNT(DISTINCT uid)`；转化用户数用
   `COUNT(DISTINCT IF(is_convert = 1, uid, NULL))`。
3. 相除得各组转化率，可直接对比 A/B 组差异。

## 参考 SQL（Hive / Spark SQL）

```sql
SELECT group_name,
       COUNT(DISTINCT uid) AS users,
       COUNT(DISTINCT IF(is_convert = 1, uid, NULL)) AS converts,
       ROUND(COUNT(DISTINCT IF(is_convert = 1, uid, NULL))
             / COUNT(DISTINCT uid), 4) AS cvr
FROM ab_log
GROUP BY group_name;
```
""",
    ),
]


async def _ensure_categories(db: AsyncSession) -> dict[str, int]:
    slug_to_id: dict[str, int] = {}
    for c in CATEGORIES:
        existing = await db.scalar(
            select(Category).where(
                Category.section == "sql", Category.slug == c["slug"]
            )
        )
        if existing is None:
            existing = Category(
                section="sql", name=c["name"], slug=c["slug"], order=int(c["order"])
            )
            db.add(existing)
            await db.flush()
        else:
            # 已存在则同步名称/顺序（便于后续调整题型命名）。
            existing.name = str(c["name"])
            existing.order = int(c["order"])
        slug_to_id[str(c["slug"])] = existing.id
    return slug_to_id


async def seed_sql_bank() -> None:
    async with SessionLocal() as db:
        slug_to_id = await _ensure_categories(db)

        existing_titles = set(
            (await db.execute(select(SqlQuestion.title))).scalars().all()
        )

        inserted = 0
        for q in QUESTIONS:
            if q["title"] in existing_titles:
                continue
            db.add(
                SqlQuestion(
                    category_id=slug_to_id[q["cat"]],
                    title=q["title"],
                    difficulty=q["difficulty"],
                    prompt_md=q["prompt_md"],
                    answer_md=q["answer_md"],
                    tags=q["tags"],
                    status="published",
                )
            )
            inserted += 1

        await db.commit()
        print(
            f"SQL 题库灌入完成：题型 {len(slug_to_id)} 个，本次新增题目 {inserted} 道"
            f"（已存在则跳过，共 {len(QUESTIONS)} 道）。"
        )


if __name__ == "__main__":
    asyncio.run(seed_sql_bank())
