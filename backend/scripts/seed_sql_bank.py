"""填充 SQL 题库：按题型分类的一批原创高频面试题。

每题分三段：一、题目描述（含示例表与示例数据）；二、求解思路；三、求解 SQL（含注释与注意事项）。
内容为原创撰写，取材于行业通用 SQL 面试考点，不复制任何第三方站点文字，可安全公开发布。

幂等 / 可更新：
- 题型分类按 (section='sql', slug) get-or-create，并同步名称/顺序；
- 题目按 title upsert：已存在则更新正文（便于迭代内容），不存在则新增。

运行（本地 SQLite）：
    cd backend
    export DATABASE_URL="sqlite+aiosqlite:///./dev.db"
    python -m scripts.seed_sql_bank

运行（线上，示例 Neon/Postgres，注意用 asyncpg 驱动、ssl=require）：
    export DATABASE_URL="postgresql+asyncpg://USER:PWD@HOST/DB?ssl=require"
    python -m scripts.seed_sql_bank
"""

from __future__ import annotations

# 本文件以中文题库“内容”为主，注释/说明行较长且不宜折行（会破坏 Markdown 渲染），
# 故对整文件豁免行宽检查。
# ruff: noqa: E501
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
    {"slug": "join", "name": "多表连接与自连接", "order": 11},
]


def _q(
    cat: str,
    title: str,
    difficulty: str,
    tags: str,
    desc: str,
    sample: str,
    idea: str,
    solution: str,
) -> dict[str, str]:
    prompt_md = (
        "## 一、题目描述\n\n" + desc.strip() + "\n\n**示例数据**\n\n" + sample.strip() + "\n"
    )
    answer_md = (
        "## 二、求解思路\n\n"
        + idea.strip()
        + "\n\n## 三、求解 SQL（Hive / Spark SQL）\n\n"
        + solution.strip()
        + "\n"
    )
    return {
        "cat": cat,
        "title": title,
        "difficulty": difficulty,
        "tags": tags,
        "prompt_md": prompt_md,
        "answer_md": answer_md,
    }


QUESTIONS: list[dict[str, str]] = [
    # ---------------- 连续 · 区间 · 序列 ----------------
    _q(
        "continuous",
        "每个用户的最长连续登录天数",
        "medium",
        "连续区间,窗口函数,row_number",
        """
给定登录表 `login(uid, dt)`（`dt` 为登录日期，同一天可能多条）。

**要求**：求每个用户历史上的**最长连续登录天数**（自然日连续）。
""",
        """
| uid | dt |
| --- | --- |
| 1 | 2024-05-01 |
| 1 | 2024-05-02 |
| 1 | 2024-05-03 |
| 1 | 2024-05-06 |
| 2 | 2024-05-01 |
| 2 | 2024-05-03 |

> 期望：用户 1 最长连续 3 天（05-01~05-03），用户 2 为 1 天。
""",
        """
1. 先对 `(uid, dt)` 去重，避免同一天多条影响计数。
2. 按用户分区、日期升序取行号 `rn`；对同一段连续日期，`dt - rn` 是常量，可作分组键 `grp`。
3. 按 `(uid, grp)` 计数得每段连续长度，再对每个用户取最大值。
""",
        """
```sql
SELECT uid, MAX(streak) AS max_streak
FROM (
  SELECT uid, grp, COUNT(*) AS streak
  FROM (
    SELECT uid, dt,
           -- 连续日期上，dt 与行号同步 +1，二者相减为常量，可作分组键
           DATE_SUB(dt, ROW_NUMBER() OVER (PARTITION BY uid ORDER BY dt)) AS grp
    FROM (SELECT DISTINCT uid, dt FROM login) d   -- 先去重，避免一天多条
  ) t
  GROUP BY uid, grp
) s
GROUP BY uid;
```

> 注意：务必先按 `(uid, dt)` 去重；否则同一天的重复登录会把行号打乱，分组键失效。
""",
    ),
    _q(
        "continuous",
        "存在连续 3 天 GMV 严格递增的商户",
        "hard",
        "连续区间,lag,窗口函数",
        """
给定商户日成交表 `sales(shop_id, dt, gmv)`。

**要求**：找出**存在连续 3 个自然日 GMV 严格递增**的商户。
""",
        """
| shop_id | dt | gmv |
| --- | --- | --- |
| A | 2024-05-01 | 100 |
| A | 2024-05-02 | 120 |
| A | 2024-05-03 | 150 |
| B | 2024-05-01 | 200 |
| B | 2024-05-02 | 180 |

> 期望：仅商户 A（100 < 120 < 150 且日期连续）。
""",
        """
1. 用 `LAG` 取每行前 1 天、前 2 天的日期与 GMV。
2. 要求日期严格相邻（`DATEDIFF = 1`）且 GMV 逐日严格递增。
3. 命中的商户去重即可。
""",
        """
```sql
SELECT DISTINCT shop_id
FROM (
  SELECT shop_id, dt, gmv,
         LAG(gmv, 1) OVER (PARTITION BY shop_id ORDER BY dt) AS gmv1,  -- 前一天 GMV
         LAG(dt,  1) OVER (PARTITION BY shop_id ORDER BY dt) AS dt1,
         LAG(gmv, 2) OVER (PARTITION BY shop_id ORDER BY dt) AS gmv2,  -- 前两天 GMV
         LAG(dt,  2) OVER (PARTITION BY shop_id ORDER BY dt) AS dt2
  FROM sales
) t
WHERE DATEDIFF(dt, dt1) = 1 AND DATEDIFF(dt1, dt2) = 1   -- 三天日期连续
  AND gmv > gmv1 AND gmv1 > gmv2;                        -- 严格递增
```

> 注意：`DATEDIFF` 条件不可省略，否则跨越缺失日期也会被误判为“连续”。
""",
    ),
    _q(
        "continuous",
        "合并用户重叠的活跃区间",
        "hard",
        "区间合并,窗口函数,累计求和",
        """
给定活跃区间表 `activity(uid, start_dt, end_dt)`（同一用户区间可能重叠或相邻）。

**要求**：把每个用户**重叠或相邻的区间合并**，输出合并后的区间。
""",
        """
| uid | start_dt | end_dt |
| --- | --- | --- |
| 1 | 2024-05-01 | 2024-05-03 |
| 1 | 2024-05-02 | 2024-05-05 |
| 1 | 2024-05-08 | 2024-05-09 |

> 期望：合并为 (05-01 ~ 05-05) 和 (05-08 ~ 05-09)。
""",
        """
1. 按 `start_dt` 排序，用窗口取「当前行之前所有区间的最大 end」（前缀最大结束日）。
2. 若当前 `start_dt` 大于该前缀最大结束日，说明与前面断开，是新区间起点，标记 `is_new=1`。
3. 对 `is_new` 做累计求和得到区间分组号 `seg_id`，按组取 `MIN(start)`、`MAX(end)`。
""",
        """
```sql
SELECT uid, MIN(start_dt) AS seg_start, MAX(end_dt) AS seg_end
FROM (
  SELECT uid, start_dt, end_dt,
         SUM(is_new) OVER (PARTITION BY uid ORDER BY start_dt
                           ROWS UNBOUNDED PRECEDING) AS seg_id   -- 累计得区间编号
  FROM (
    SELECT uid, start_dt, end_dt,
           CASE WHEN start_dt <= MAX(end_dt) OVER (
                       PARTITION BY uid ORDER BY start_dt
                       ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING)  -- 之前的最大 end
                THEN 0 ELSE 1 END AS is_new
    FROM activity
  ) t
) s
GROUP BY uid, seg_id;
```

> 注意：前缀最大值窗口帧要用 `... AND 1 PRECEDING`（不含当前行），否则会把自己算进去导致永远不新开区间。
""",
    ),
    _q(
        "continuous",
        "允许间断 1 天的最长活跃跨度",
        "hard",
        "连续区间,分段,datediff",
        """
给定登录表 `login(uid, dt)`。定义：相邻两次登录**间隔不超过 2 天**（即最多断 1 天）视为同一段活跃。

**要求**：求每个用户活跃段覆盖的**最长天数跨度**（段内最晚日期 − 最早日期 + 1）。
""",
        """
| uid | dt |
| --- | --- |
| 1 | 2024-05-01 |
| 1 | 2024-05-02 |
| 1 | 2024-05-04 |
| 1 | 2024-05-07 |

> 期望：05-01、05-02、05-04 属同一段（间隔 ≤ 2 天），跨度 4 天；05-07 另起一段。
""",
        """
1. `(uid, dt)` 去重后按日期排序，用 `LAG` 取上一次登录日期。
2. 若与上一次间隔 `> 2` 天则开启新段（`is_new=1`），累计求和得段号 `seg_id`。
3. 每段取 `MIN(dt)`、`MAX(dt)`，跨度 = `DATEDIFF(max, min) + 1`，再对用户取最大。
""",
        """
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
                  THEN 0 ELSE 1 END AS is_new    -- 间隔 ≤ 2 天算同段
      FROM (SELECT DISTINCT uid, dt FROM login) d
    ) t
  ) g
  GROUP BY uid, seg_id
) s
GROUP BY uid;
```

> 注意：这里求的是「跨度天数」而非「登录次数」，用 max−min+1；若要登录次数改用 COUNT。
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
| dt | price |
| --- | --- |
| 2024-05-01 | 10 |
| 2024-05-02 | 14 |
| 2024-05-03 | 9 |
| 2024-05-04 | 12 |

> 期望：05-02 为波峰（14），05-03 为波谷（9）。
""",
        """
1. 用 `LAG` 取前一天价格、`LEAD` 取后一天价格。
2. 当天价格同时大于前后即为波峰，同时小于前后即为波谷。
3. 首尾两天没有完整前后邻居，`LAG/LEAD` 为 NULL，天然不会命中。
""",
        """
```sql
SELECT dt, price,
       CASE WHEN price > prev AND price > next THEN 'peak'      -- 波峰
            WHEN price < prev AND price < next THEN 'valley'     -- 波谷
       END AS point_type
FROM (
  SELECT dt, price,
         LAG(price)  OVER (ORDER BY dt) AS prev,
         LEAD(price) OVER (ORDER BY dt) AS next
  FROM stock
) t
WHERE (price > prev AND price > next)
   OR (price < prev AND price < next);
```

> 注意：相等（price = prev）时不算波峰/波谷；若业务允许“非严格”，把 `>`/`<` 改为 `>=`/`<=`。
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
| uid | dt |
| --- | --- |
| 1 | 2024-05-01 |
| 1 | 2024-05-02 |
| 2 | 2024-05-01 |

> 期望：05-01 当日活跃 2 人，次日仍活跃 1 人（用户 1），次日留存率 = 0.5。
""",
        """
1. 用登录表自连接：`b.dt` 比 `a.dt` 晚 1 天且为同一用户。
2. 当天活跃用 `COUNT(DISTINCT a.uid)`，次日仍活跃用 `COUNT(DISTINCT b.uid)`。
3. 相除即得次日留存率（`LEFT JOIN` 保证当天无留存的日期也出现）。
""",
        """
```sql
SELECT a.dt,
       COUNT(DISTINCT a.uid) AS dau,
       COUNT(DISTINCT b.uid) AS retained,
       ROUND(COUNT(DISTINCT b.uid) / COUNT(DISTINCT a.uid), 4) AS retention_1d
FROM login a
LEFT JOIN login b
  ON a.uid = b.uid AND DATEDIFF(b.dt, a.dt) = 1   -- 次日
GROUP BY a.dt;
```

> 注意：务必用 `COUNT(DISTINCT ...)`，因为同一用户一天可能多次登录，直接 COUNT 会重复计数。
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
`user_reg`：

| uid | reg_dt |
| --- | --- |
| 1 | 2024-05-01 |
| 2 | 2024-05-01 |

`login`：

| uid | dt |
| --- | --- |
| 1 | 2024-05-02 |
| 1 | 2024-05-08 |

> 期望：05-01 新增 2 人；次日留存 0.5（用户 1），7 日留存 0.5（用户 1 于 05-08）。
""",
        """
1. 以注册记录为基准 `LEFT JOIN` 登录记录。
2. 用 `DATEDIFF(登录日, 注册日)` 判断是第几日活跃，配合 `COUNT(DISTINCT IF(...))` 做条件去重计数。
3. 各留存数除以当日新增用户数。
""",
        """
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

> 注意：`= 7` 指“注册后第 7 天当天活跃”；若要“7 日内活跃”改成 `BETWEEN 1 AND 7`。
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
| uid | event | event_time |
| --- | --- | --- |
| 1 | register | 2024-05-01 10:00 |
| 1 | order | 2024-05-01 11:00 |
| 1 | pay | 2024-05-01 12:00 |
| 2 | register | 2024-05-01 09:00 |
| 2 | order | 2024-05-01 09:30 |

> 期望：注册 2 人、下单 2 人、支付 1 人；注册→下单 100%，下单→支付 50%。
""",
        """
1. 用 `COUNT(DISTINCT IF(event=..., uid, NULL))` 分别统计各步去重人数。
2. 相邻步骤人数相除得转化率。
3. 若需严格时序（先注册后下单再支付），可先按 `uid` 聚合各事件最早时间再比较大小。
""",
        """
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

> 注意：本写法只看“是否发生过”，不校验时间先后；严格漏斗需保证 register_time < order_time < pay_time。
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
| emp_id | dept_id | salary |
| --- | --- | --- |
| 1 | 10 | 30000 |
| 2 | 10 | 25000 |
| 3 | 10 | 25000 |
| 4 | 10 | 20000 |
| 5 | 20 | 40000 |

> 期望：部门 10 取薪资前三档（30000、并列 25000、20000），并列 25000 都保留。
""",
        """
1. 按部门分区、薪资降序，用 `DENSE_RANK` 计算名次（并列同名次、不跳号）。
2. 过滤名次 `<= 3`。若并列不保留、严格取 3 人，改用 `ROW_NUMBER`。
""",
        """
```sql
SELECT dept_id, emp_id, salary
FROM (
  SELECT dept_id, emp_id, salary,
         DENSE_RANK() OVER (PARTITION BY dept_id ORDER BY salary DESC) AS rk
  FROM emp
) t
WHERE rk <= 3;
```

> 注意：`ROW_NUMBER`（唯一序号，并列也只保留一个）/ `RANK`（并列跳号）/ `DENSE_RANK`（并列不跳号）语义不同，按需选择。
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
| cat_id | sku_id | amount |
| --- | --- | --- |
| 1 | 101 | 500 |
| 1 | 102 | 300 |
| 1 | 103 | 200 |
| 2 | 201 | 1000 |

> 期望：品类 1 取 101（500，占 0.5）、102（300，占 0.3）；品类 2 取 201。
""",
        """
1. 先按 `(cat_id, sku_id)` 汇总销售额。
2. 用窗口 `SUM() OVER (PARTITION BY cat_id)` 得品类总额，`ROW_NUMBER()` 得品类内排名。
3. 过滤排名 `<= 2`，用商品额 / 品类总额得占比。
""",
        """
```sql
SELECT cat_id, sku_id, amount,
       ROUND(amount / cat_total, 4) AS ratio
FROM (
  SELECT cat_id, sku_id, amount,
         SUM(amount) OVER (PARTITION BY cat_id) AS cat_total,               -- 品类总额
         ROW_NUMBER() OVER (PARTITION BY cat_id ORDER BY amount DESC) AS rn -- 品类内排名
  FROM (
    SELECT cat_id, sku_id, SUM(amount) AS amount
    FROM sku_sales
    GROUP BY cat_id, sku_id
  ) g
) t
WHERE rn <= 2;
```

> 注意：占比分母是“品类总额”而非“Top2 之和”；聚合与排名放在同一层子查询里可少扫一遍数据。
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
| sid | subject | score |
| --- | --- | --- |
| A | math | 95 |
| B | math | 90 |
| C | math | 85 |
| D | math | 80 |

> 期望：math 第 3 名为学生 C（85）。
""",
        """
1. 按学科分区、成绩降序用 `DENSE_RANK` 排名。
2. 过滤名次等于 3 即可。
""",
        """
```sql
SELECT subject, sid, score
FROM (
  SELECT subject, sid, score,
         DENSE_RANK() OVER (PARTITION BY subject ORDER BY score DESC) AS rk
  FROM score
) t
WHERE rk = 3;
```

> 注意：用 `DENSE_RANK` 时若前面有并列，第 3 名可能有多人；题目要求“并列都保留”正合适。
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
| sid | subject | score |
| --- | --- | --- |
| 1 | chinese | 80 |
| 1 | math | 90 |
| 1 | english | 70 |
| 2 | chinese | 60 |

> 期望：学生 1 → (chinese 80, math 90, english 70)；学生 2 → (chinese 60, 其余 NULL)。
""",
        """
1. 按 `sid` 分组。
2. 用 `MAX(IF(subject=..., score, NULL))` 把每一科的分数“挑”到对应列上。
""",
        """
```sql
SELECT sid,
       MAX(IF(subject = 'chinese', score, NULL)) AS chinese,
       MAX(IF(subject = 'math',    score, NULL)) AS math,
       MAX(IF(subject = 'english', score, NULL)) AS english
FROM score
GROUP BY sid;
```

> 注意：用 `MAX` 而非 `SUM`，避免某学生同一科目有多条时被求和；缺考科目自然为 NULL。
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
| uid | tags |
| --- | --- |
| 1 | 数仓,实时,调优 |
| 2 | SQL |

> 期望：用户 1 拆成 3 行（数仓 / 实时 / 调优），用户 2 拆成 1 行（SQL）。
""",
        """
1. `SPLIT(tags, ',')` 得到数组。
2. `LATERAL VIEW EXPLODE(...)` 把数组炸开成多行。
""",
        """
```sql
SELECT uid, tag
FROM user_tags
LATERAL VIEW EXPLODE(SPLIT(tags, ',')) t AS tag;
```

> 注意：若某些行 tags 为空，`EXPLODE` 会丢掉该行；要保留可改用 `LATERAL VIEW OUTER EXPLODE`。
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
| uid | page | view_time |
| --- | --- | --- |
| 1 | home | 2024-05-01 10:00 |
| 1 | list | 2024-05-01 10:01 |
| 1 | detail | 2024-05-01 10:02 |

> 期望：用户 1 → `home>list>detail`。
""",
        """
1. `COLLECT_LIST` 只有在数据“有序进入 reducer”时才保序，
   因此先按 `DISTRIBUTE BY uid SORT BY uid, view_time` 排序。
2. 再按 `uid` 分组，用 `CONCAT_WS('>', COLLECT_LIST(page))` 拼接。
""",
        """
```sql
SELECT uid, CONCAT_WS('>', COLLECT_LIST(page)) AS path
FROM (
  SELECT uid, page, view_time
  FROM page_view
  DISTRIBUTE BY uid SORT BY uid, view_time   -- 关键：保证进入聚合前已按时间有序
) t
GROUP BY uid;
```

> 注意：直接对未排序数据用 `COLLECT_LIST` 不保证顺序；必须先 `DISTRIBUTE BY + SORT BY`（或 Spark 里 `sort_array` + 结构体带时间戳）。
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
| dt | amount |
| --- | --- |
| 2023-01-15 | 100 |
| 2024-01-10 | 120 |
| 2024-02-10 | 150 |

> 期望：2024-02 环比 = 150/120−1 = 25%；2024-01 同比 = 120/100−1 = 20%。
""",
        """
1. 用 `SUBSTR(dt, 1, 7)` 取“年-月”聚合出月度销售额。
2. 按月份排序，`LAG(amount, 1)` 取上月、`LAG(amount, 12)` 取去年同月。
3. 增长率 = 本期 / 上期 − 1。
""",
        """
```sql
SELECT ym, amount,
       ROUND(amount / LAG(amount, 1)  OVER (ORDER BY ym) - 1, 4) AS mom,  -- 环比
       ROUND(amount / LAG(amount, 12) OVER (ORDER BY ym) - 1, 4) AS yoy   -- 同比
FROM (
  SELECT SUBSTR(dt, 1, 7) AS ym, SUM(amount) AS amount
  FROM sales
  GROUP BY SUBSTR(dt, 1, 7)
) m;
```

> 注意：`LAG(...,12)` 默认“往前数 12 行”，只有月份连续无缺失时才恰好等于“去年同月”；有缺失月份时应改为按 `ym` 自连接去年同月。
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
| dt | amount |
| --- | --- |
| 2024-05-01 | 100 |
| 2024-05-02 | 200 |
| 2024-05-03 | 300 |

> 期望：累计 100 / 300 / 600；累计占比 ≈ 0.1667 / 0.5 / 1.0（全期总额 600）。
""",
        """
1. 先按天汇总。
2. `SUM() OVER (ORDER BY dt ROWS UNBOUNDED PRECEDING)` 得累计额；`SUM() OVER ()` 得全期总额。
3. 两者相除得累计占比。
""",
        """
```sql
SELECT dt, amount,
       SUM(amount) OVER (ORDER BY dt ROWS UNBOUNDED PRECEDING) AS cum_amount, -- 累计
       ROUND(SUM(amount) OVER (ORDER BY dt ROWS UNBOUNDED PRECEDING)
             / SUM(amount) OVER (), 4) AS cum_ratio                           -- 占全期比例
FROM (
  SELECT dt, SUM(amount) AS amount
  FROM sales
  GROUP BY dt
) d;
```

> 注意：`SUM() OVER ()` 空窗口表示全表总额；累计一定要写明帧 `ROWS UNBOUNDED PRECEDING`，否则默认帧在有排序时是 RANGE 会把同值行一起累计。
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
| dt | cnt |
| --- | --- |
| 2024-05-01 | 100 |
| 2024-05-02 | 200 |
| 2024-05-03 | 300 |

> 期望：不足 7 天时按已有天数平均，如 05-03 的 ma7 = (100+200+300)/3 = 200。
""",
        """
1. 按日期排序，用滑动窗口帧 `ROWS BETWEEN 6 PRECEDING AND CURRENT ROW`。
2. 对 `cnt` 求 `AVG` 即为近 7 日移动平均（起始不足 7 天时按实际天数计算）。
""",
        """
```sql
SELECT dt, cnt,
       ROUND(AVG(cnt) OVER (ORDER BY dt
             ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 2) AS ma7  -- 含当天共 7 天
FROM dau;
```

> 注意：`6 PRECEDING` + 当前行 = 7 行；若日期有缺失（某天无数据），按“行”滑动会跨过缺口，需要先补齐日期维度。
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
| sid | subject | score |
| --- | --- | --- |
| A | math | 100 |
| B | math | 60 |
| C | math | 80 |
| D | math | 90 |

> 期望：去掉 100 和 60，(80+90)/2 = 85。
""",
        """
1. 直接用聚合：总分减去最高最低，除以（人数 − 2）。
2. 用 `HAVING COUNT(*) > 2` 排除人数不足的学科，避免除零。
""",
        """
```sql
SELECT subject,
       ROUND((SUM(score) - MAX(score) - MIN(score)) / (COUNT(*) - 2), 2) AS avg_trimmed
FROM score
GROUP BY subject
HAVING COUNT(*) > 2;   -- 至少 3 人才有意义，避免除以 0
```

> 注意：若最高/最低分有并列，这种写法只各去掉一个；若要去掉“所有并列极值”需另用排名过滤。
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
| subject | score |
| --- | --- |
| math | 80 |
| math | 90 |
| math | 70 |

> 期望：math 中位数 = 80。
""",
        """
1. Hive/Spark 可直接用 `PERCENTILE`（精确，需整型）计算 0.5 分位。
2. 大数据量下可用 `PERCENTILE_APPROX(score, 0.5)` 近似加速。
""",
        """
```sql
SELECT subject,
       PERCENTILE(CAST(score AS BIGINT), 0.5) AS median
FROM score
GROUP BY subject;

-- 大数据量近似版本（更快，略有误差）：
-- SELECT subject, PERCENTILE_APPROX(score, 0.5) AS median FROM score GROUP BY subject;
```

> 注意：`PERCENTILE` 要求入参为整型（用 `CAST(... AS BIGINT)`）；浮点数用 `PERCENTILE_APPROX`。
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
| uid | order_id | order_time | amount |
| --- | --- | --- | --- |
| 1 | 1001 | 2024-05-01 10:00 | 50 |
| 1 | 1002 | 2024-05-03 12:00 | 80 |
| 1 | 1003 | 2024-05-05 09:00 | 30 |

> 期望：首单 1001（first）、末单 1003（last）。
""",
        """
1. 同一子查询里开两个 `ROW_NUMBER`：一个按时间升序、一个按时间降序。
2. 过滤“升序第 1”或“降序第 1”，并用 `CASE` 标注首末。
""",
        """
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

> 注意：只有一笔订单的用户，该行 rn_first 与 rn_last 同时为 1，会被标为 first（`CASE` 先判 first）；如需同时体现可自行调整。
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
| uid | name | update_time |
| --- | --- | --- |
| 1 | 张三 | 2024-05-01 |
| 1 | 张三丰 | 2024-05-03 |

> 期望：保留 (1, 张三丰, 2024-05-03)。
""",
        """
1. 按 `uid` 分区、`update_time` 降序用 `ROW_NUMBER` 打标。
2. 取 `rn = 1` 即最新一条（数仓“取最新快照”的通用写法）。
""",
        """
```sql
SELECT uid, name, update_time
FROM (
  SELECT uid, name, update_time,
         ROW_NUMBER() OVER (PARTITION BY uid ORDER BY update_time DESC) AS rn
  FROM user_profile
) t
WHERE rn = 1;
```

> 注意：若 update_time 可能相等，需再加一个稳定排序键（如自增 id）避免结果随机。
""",
    ),
    # ---------------- 会话切分与行为路径 ----------------
    _q(
        "session-path",
        "按 30 分钟间隔切分会话（Session）",
        "hard",
        "session,分段,时间差,窗口函数",
        """
给定行为流水 `page_view(uid, view_time)`。定义：同一用户相邻两次行为**间隔超过 30 分钟**即切分为新会话。

**要求**：求每个用户的**会话（session）数量**。
""",
        """
| uid | view_time |
| --- | --- |
| 1 | 2024-05-01 10:00:00 |
| 1 | 2024-05-01 10:20:00 |
| 1 | 2024-05-01 11:30:00 |

> 期望：10:00 与 10:20 间隔 20 分钟同一会话；11:30 距上一条 70 分钟另起会话 → 共 2 个会话。
""",
        """
1. 按用户、时间排序，用 `LAG` 取上一条行为时间。
2. 若与上一条间隔 `> 1800` 秒（或本行是该用户首条，`LAG` 为 NULL）则开启新会话。
3. 对 `is_new` 累计求和得会话号，用户维度取最大会话号即为会话数。
""",
        """
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
                        > 1800                        -- 间隔 > 30 分钟
                THEN 1 ELSE 0 END AS is_new
    FROM page_view
  ) t
) s
GROUP BY uid;
```

> 注意：首条行为的 `LAG` 为 NULL，必须显式判 NULL 记为新会话，否则该用户会少算一个 session。
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
| uid | enter_time | leave_time |
| --- | --- | --- |
| 1 | 2024-05-01 10:00 | 2024-05-01 10:30 |
| 2 | 2024-05-01 10:10 | 2024-05-01 10:40 |
| 3 | 2024-05-01 10:35 | 2024-05-01 10:50 |

> 期望：10:10~10:30 用户 1、2 同时在线，最大同时在线 = 2。
""",
        """
1. 把每条观看拆成两个事件：进入 `+1`、离开 `-1`。
2. 按时间排序做前缀和（在线人数随事件累加）；同一时刻**先进后出**（`+1` 排在 `-1` 前，避免瞬时低估）。
3. 前缀和的最大值即最大同时在线人数。
""",
        """
```sql
SELECT MAX(online) AS max_online
FROM (
  SELECT SUM(delta) OVER (ORDER BY ts, delta DESC
                          ROWS UNBOUNDED PRECEDING) AS online   -- 前缀和 = 当前在线数
  FROM (
    SELECT enter_time AS ts,  1 AS delta FROM live_session      -- 进入 +1
    UNION ALL
    SELECT leave_time AS ts, -1 AS delta FROM live_session      -- 离开 -1
  ) e
) t;
```

> 注意：同一时刻的排序 `ORDER BY ts, delta DESC` 让 +1 先于 -1，保证边界时刻不低估；若业务定义“离开即不在线”，可反过来。
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
| uid | fid |
| --- | --- |
| 1 | 100 |
| 2 | 100 |
| 1 | 200 |
| 2 | 200 |

> 期望：用户对 (1, 2) 共同好友 100、200 共 2 个。
""",
        """
1. 对好友表按同一个好友 `fid` 自连接：两个不同用户共享同一个 `fid` 即拥有一个共同好友。
2. 用 `a.uid < b.uid` 去重（避免 (A,B) 与 (B,A) 重复、并排除自己）。
3. 按用户对分组计数，排序取 TopN。
""",
        """
```sql
SELECT a.uid AS u1, b.uid AS u2, COUNT(*) AS common_friends
FROM friend a
JOIN friend b ON a.fid = b.fid AND a.uid < b.uid   -- 同一好友；u1<u2 去重
GROUP BY a.uid, b.uid
ORDER BY common_friends DESC
LIMIT 10;
```

> 注意：`a.uid < b.uid` 既避免自连接产生 (A,A)，又保证每对只出现一次。
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
| follower | followee |
| --- | --- |
| 1 | 2 |
| 2 | 1 |
| 1 | 3 |

> 期望：用户对 (1, 2) 互相关注；(1, 3) 只是单向。
""",
        """
1. 关注表自连接：若存在 `(A→B)` 且 `(B→A)` 两条记录，则 A、B 互相关注。
2. 连接条件为 `a.follower = b.followee AND a.followee = b.follower`。
3. 用 `a.follower < a.followee` 去重每对只留一条。
""",
        """
```sql
SELECT a.follower AS u1, a.followee AS u2
FROM follow a
JOIN follow b
  ON a.follower = b.followee AND a.followee = b.follower
WHERE a.follower < a.followee;   -- 每对只保留一条
```

> 注意：不加 `follower < followee` 会得到 (1,2) 与 (2,1) 两条重复结果。
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
| uid | order_date |
| --- | --- |
| 1 | 2024-05-01 |
| 1 | 2024-05-03 |
| 2 | 2024-05-02 |

> 期望：用户 1 下单 2 次（复购），用户 2 下单 1 次；复购率 = 1/2 = 0.5。
""",
        """
1. 先按 `uid` 统计下单次数。
2. 分子为下单次数 ≥ 2 的用户数，分母为全部下单用户数，相除即复购率。
""",
        """
```sql
SELECT ROUND(COUNT(IF(order_cnt >= 2, uid, NULL)) / COUNT(uid), 4) AS repurchase_rate
FROM (
  SELECT uid, COUNT(*) AS order_cnt   -- 每个用户下单次数
  FROM orders
  GROUP BY uid
) t;
```

> 注意：若按“订单去重日期”定义复购（一天多单只算一次），先对 `(uid, order_date)` 去重再统计。
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
| uid | group_name | is_convert |
| --- | --- | --- |
| 1 | A | 1 |
| 2 | A | 0 |
| 3 | B | 1 |
| 4 | B | 1 |

> 期望：A 组转化率 = 1/2 = 0.5；B 组 = 2/2 = 1.0。
""",
        """
1. 按 `group_name` 分组。
2. 参与用户数用 `COUNT(DISTINCT uid)`；转化用户数用
   `COUNT(DISTINCT IF(is_convert = 1, uid, NULL))`。
3. 相除得各组转化率，可直接对比 A/B 组差异。
""",
        """
```sql
SELECT group_name,
       COUNT(DISTINCT uid) AS users,
       COUNT(DISTINCT IF(is_convert = 1, uid, NULL)) AS converts,
       ROUND(COUNT(DISTINCT IF(is_convert = 1, uid, NULL))
             / COUNT(DISTINCT uid), 4) AS cvr
FROM ab_log
GROUP BY group_name;
```

> 注意：用 `COUNT(DISTINCT uid)` 而非 `COUNT(*)`，避免同一用户多条日志导致分母虚高。
""",
    ),
    # ---------------- 多表连接与自连接 ----------------
    _q(
        "join",
        "薪资高于其直属经理的员工",
        "easy",
        "自连接,上下级,比较",
        """
给定员工表 `emp(emp_id, name, salary, manager_id)`，`manager_id` 指向本表的 `emp_id`（经理也是员工）。

**要求**：找出**薪资严格高于其直属经理**的员工姓名。
""",
        """
| emp_id | name | salary | manager_id |
| --- | --- | --- | --- |
| 1 | Joe | 70000 | 3 |
| 2 | Henry | 80000 | 4 |
| 3 | Sam | 60000 | NULL |
| 4 | Max | 90000 | NULL |

> 期望：Joe（70000 > 经理 Sam 60000）。
""",
        """
1. 员工与经理在同一张表，用**自连接**：员工行的 `manager_id` 关联经理行的 `emp_id`。
2. 用 `INNER JOIN` 自然排除没有经理的记录，再比较两侧 `salary`。
""",
        """
```sql
SELECT e.name
FROM emp e
JOIN emp m            -- m 为 e 的直属经理
  ON e.manager_id = m.emp_id
WHERE e.salary > m.salary;
```

> 注意：用 `INNER JOIN` 而非 `LEFT JOIN`，无经理者（`manager_id IS NULL`）自动不参与比较。
""",
    ),
    _q(
        "join",
        "至少有 5 名直接下属的经理",
        "medium",
        "自连接,分组计数,having",
        """
给定员工表 `emp(emp_id, name, manager_id)`，`manager_id` 指向本表 `emp_id`。

**要求**：找出**直接下属人数 >= 5** 的经理姓名。
""",
        """
| emp_id | name | manager_id |
| --- | --- | --- |
| 101 | A | NULL |
| 102 | B | 101 |
| 103 | C | 101 |
| 104 | D | 101 |
| 105 | E | 101 |
| 106 | F | 101 |

> 期望：A（其下属 B/C/D/E/F 共 5 人）。
""",
        """
1. 按 `manager_id` 分组统计**直接下属数**，用 `HAVING` 过滤 `>= 5`。
2. 再关联员工表把 `manager_id` 换成经理姓名。
""",
        """
```sql
SELECT m.name
FROM emp m
JOIN (
  SELECT manager_id, COUNT(*) AS sub_cnt   -- 每个经理的直接下属数
  FROM emp
  WHERE manager_id IS NOT NULL
  GROUP BY manager_id
  HAVING COUNT(*) >= 5
) t ON m.emp_id = t.manager_id;
```

> 注意：先在子查询里 `GROUP BY ... HAVING` 收敛数据，再 JOIN 取名，避免对全表做大连接。
""",
    ),
    _q(
        "join",
        "统计每个专业的学生人数（含 0 人专业）",
        "medium",
        "left join,补零,分组计数",
        """
给定专业表 `dept(dept_id, dept_name)` 与学生表 `student(stu_id, dept_id)`。

**要求**：统计**每个专业的学生人数**，没有学生的专业也要出现，人数记为 0，按人数降序、专业名升序排序。
""",
        """
| dept_id | dept_name |
| --- | --- |
| 1 | 计算机 |
| 2 | 数学 |
| 3 | 物理 |

| stu_id | dept_id |
| --- | --- |
| 1001 | 1 |
| 1002 | 1 |
| 1003 | 2 |

> 期望：计算机 2、数学 1、物理 0。
""",
        """
1. 以**专业表为主表** `LEFT JOIN` 学生表，保证 0 人专业不被过滤掉。
2. 用 `COUNT(student.stu_id)` 而非 `COUNT(*)`：`COUNT(列)` 不统计 NULL，未匹配到学生的专业自然计 0。
""",
        """
```sql
SELECT d.dept_name,
       COUNT(s.stu_id) AS stu_cnt      -- 计数列而非 *，未匹配的 NULL 记 0
FROM dept d
LEFT JOIN student s ON d.dept_id = s.dept_id
GROUP BY d.dept_name
ORDER BY stu_cnt DESC, d.dept_name ASC;
```

> 注意：`COUNT(*)` 会把 LEFT JOIN 产生的空行也算 1，导致 0 人专业错误地变成 1。
""",
    ),
    # ---------------- 聚合与去重（补充） ----------------
    _q(
        "aggregate",
        "查找重复的邮箱",
        "easy",
        "分组,having,重复值",
        """
给定用户表 `person(id, email)`。

**要求**：找出**表中重复出现**的邮箱（出现次数 >= 2）。
""",
        """
| id | email |
| --- | --- |
| 1 | a@x.com |
| 2 | b@x.com |
| 3 | a@x.com |

> 期望：a@x.com（出现 2 次）。
""",
        """
1. 按 `email` 分组计数，`HAVING COUNT(*) > 1` 即为重复邮箱。
2. 若邮箱大小写需视为相同，先 `LOWER(email)` 再分组。
""",
        """
```sql
SELECT email
FROM person
GROUP BY email
HAVING COUNT(*) > 1;
```

> 注意：过滤聚合结果要用 `HAVING`，`WHERE` 不能引用 `COUNT(*)` 等聚合值。
""",
    ),
    _q(
        "aggregate",
        "删除重复邮箱只保留每组最小 id",
        "medium",
        "去重,保留最小id,窗口函数",
        """
给定用户表 `person(id, email)`，同一邮箱可能出现多行。

**要求**：对每个邮箱**只保留 id 最小的一行**，其余视为需删除。请给出「保留结果集」以及「需删除的 id 集合」。
""",
        """
| id | email |
| --- | --- |
| 1 | a@x.com |
| 2 | b@x.com |
| 3 | a@x.com |

> 期望：保留 id=1、2；需删除 id=3。
""",
        """
1. 按 `email` 分区、`id` 升序取 `ROW_NUMBER`，`rn=1` 即每组最小 id。
2. 保留结果取 `rn = 1`；需删除的取 `rn > 1`。
3. 若在 MySQL 里真删除，可用 `DELETE p1 FROM person p1 JOIN person p2 ON p1.email=p2.email AND p1.id>p2.id`。
""",
        """
```sql
-- 保留每个邮箱 id 最小的一行
SELECT id, email
FROM (
  SELECT id, email,
         ROW_NUMBER() OVER (PARTITION BY email ORDER BY id) AS rn
  FROM person
) t
WHERE rn = 1;

-- 需删除的 id（rn > 1）
SELECT id
FROM (
  SELECT id,
         ROW_NUMBER() OVER (PARTITION BY email ORDER BY id) AS rn
  FROM person
) t
WHERE rn > 1;
```

> 注意：Hive/Spark 无原地 `DELETE`，通常用「重写保留结果覆盖写回」实现去重。
""",
    ),
    # ---------------- 分组 TopN 与排名（补充） ----------------
    _q(
        "group-topn",
        "分数排名（并列同名次且名次连续）",
        "medium",
        "dense_rank,排名,并列",
        """
给定分数表 `scores(id, score)`。

**要求**：按分数从高到低排名。**分数相同名次相同**，且名次**连续不跳号**（如 1,1,2,3）。返回 `score` 与其名次。
""",
        """
| id | score |
| --- | --- |
| 1 | 3.50 |
| 2 | 3.65 |
| 3 | 4.00 |
| 4 | 3.85 |
| 5 | 4.00 |

> 期望：4.00→1、4.00→1、3.85→2、3.65→3、3.50→4。
""",
        """
1. 名次相同且连续不跳号，正是 `DENSE_RANK` 的语义。
2. 若要求「并列跳号」（1,1,3）则用 `RANK`；「唯一序号」用 `ROW_NUMBER`。
""",
        """
```sql
SELECT score,
       DENSE_RANK() OVER (ORDER BY score DESC) AS rnk
FROM scores
ORDER BY score DESC;
```

> 注意：`rank` 在很多方言里是保留字，做列别名时建议改名（如 `rnk`）或加反引号。
""",
    ),
    # ---------------- 行列转换（补充） ----------------
    _q(
        "pivot",
        "相邻两两交换座位号",
        "medium",
        "case,奇偶,行内交换",
        """
给定座位表 `seat(id, name)`，`id` 从 1 连续递增。

**要求**：**两两相邻交换**座位——1 与 2 换、3 与 4 换……。若总人数为奇数，最后一位座位不变。返回按 `id` 升序的新座位表。
""",
        """
| id | name |
| --- | --- |
| 1 | Abbot |
| 2 | Doris |
| 3 | Emerson |
| 4 | Green |
| 5 | Jeames |

> 期望：id=1→Doris、2→Abbot、3→Green、4→Emerson、5→Jeames（末位奇数不变）。
""",
        """
1. 新 id 规则：奇数 `id` 变 `id+1`，偶数 `id` 变 `id-1`。
2. 末位为奇数时 `id+1` 超出最大 id，需保持不变——用总人数判断。
3. 用 `CASE` 计算新 id 后按新 id 排序即可。
""",
        """
```sql
SELECT
  CASE
    WHEN id % 2 = 1 AND id = (SELECT MAX(id) FROM seat) THEN id  -- 末位奇数不变
    WHEN id % 2 = 1 THEN id + 1                                   -- 奇数与后一位换
    ELSE id - 1                                                   -- 偶数与前一位换
  END AS id,
  name
FROM seat
ORDER BY id;
```

> 注意：奇数总人数时最后一行必须特判，否则会被换到一个不存在的座位。
""",
    ),
    # ---------------- 图与关系（补充） ----------------
    _q(
        "graph-relation",
        "标记二叉树节点的类型（根/内部/叶子）",
        "medium",
        "树,自连接,case,节点类型",
        """
给定树表 `tree(id, p_id)`，`p_id` 为父节点 id；根节点的 `p_id` 为 NULL。

**要求**：为每个节点标注类型——`Root`（无父）、`Leaf`（无子）、`Inner`（既有父又有子）。
""",
        """
| id | p_id |
| --- | --- |
| 1 | NULL |
| 2 | 1 |
| 3 | 1 |
| 4 | 2 |
| 5 | 2 |

> 期望：1→Root、2→Inner、3→Leaf、4→Leaf、5→Leaf。
""",
        """
1. `p_id IS NULL` → 根节点 `Root`。
2. 否则看该节点 id 是否出现在别人的 `p_id` 中：出现则为 `Inner`，不出现则为 `Leaf`。
3. 用「是否存在子节点」的集合做判断（`IN` 子查询或半连接）。
""",
        """
```sql
SELECT id,
  CASE
    WHEN p_id IS NULL THEN 'Root'
    WHEN id IN (SELECT DISTINCT p_id FROM tree WHERE p_id IS NOT NULL) THEN 'Inner'
    ELSE 'Leaf'
  END AS node_type
FROM tree;
```

> 注意：判断顺序要先处理 `Root`，否则只有一个根节点的树会被误判为 `Leaf`。
""",
    ),
    _q(
        "graph-relation",
        "好友数最多的用户",
        "medium",
        "无向图,union,分组计数,topn",
        """
给定好友申请成功表 `request_accepted(requester_id, accepter_id)`，好友关系是**无向**的（双方互为好友）。

**要求**：找出**好友数最多**的用户及其好友数。
""",
        """
| requester_id | accepter_id |
| --- | --- |
| 1 | 2 |
| 1 | 3 |
| 2 | 3 |
| 3 | 4 |

> 期望：用户 3 好友数 3（与 1、2、4）。
""",
        """
1. 无向关系里，一个人既可能是 `requester` 也可能是 `accepter`，两列都要计入。
2. 用 `UNION ALL` 把两列摊成一列 `uid`，再按 `uid` 分组计数。
3. 取计数最大的用户（并列可用窗口排名保留）。
""",
        """
```sql
SELECT uid, COUNT(*) AS friend_cnt
FROM (
  SELECT requester_id AS uid FROM request_accepted
  UNION ALL
  SELECT accepter_id  AS uid FROM request_accepted
) t
GROUP BY uid
ORDER BY friend_cnt DESC
LIMIT 1;
```

> 注意：用 `UNION ALL` 而非 `UNION`——同一条好友关系两列本就代表两个人各 +1，去重会漏计。
""",
    ),
    # ---------------- 同比环比与累计（补充） ----------------
    _q(
        "trend-cumulative",
        "员工近 3 个月的累计薪水（不含最新月）",
        "hard",
        "累计,滑动窗口,排除最新月",
        """
给定月度薪水表 `salary(emp_id, pay_month, amount)`，`pay_month` 形如 `2024-01`。

**要求**：对每个员工，**排除其最新的一个月**后，按月计算「当月及往前共 3 个月」的**累计薪水**（滑动 3 个月求和）。
""",
        """
| emp_id | pay_month | amount |
| --- | --- | --- |
| 1 | 2024-01 | 20 |
| 1 | 2024-02 | 30 |
| 1 | 2024-03 | 40 |
| 1 | 2024-04 | 60 |

> 期望：先排除最新月 2024-04；对 01/02/03 计算滑动 3 月累计（01=20、02=50、03=90）。
""",
        """
1. 先按员工取每月最新序号，标记并**剔除最新月**（`ROW_NUMBER` 降序 = 1 的那月）。
2. 在剩余月份上按 `pay_month` 升序，用窗口帧 `ROWS BETWEEN 2 PRECEDING AND CURRENT ROW` 求滑动 3 月和。
""",
        """
```sql
SELECT emp_id, pay_month,
       SUM(amount) OVER (
         PARTITION BY emp_id ORDER BY pay_month
         ROWS BETWEEN 2 PRECEDING AND CURRENT ROW   -- 当月+前2月
       ) AS cum_3m
FROM (
  SELECT emp_id, pay_month, amount,
         ROW_NUMBER() OVER (PARTITION BY emp_id ORDER BY pay_month DESC) AS rn
  FROM salary
) t
WHERE rn > 1        -- 剔除最新月
ORDER BY emp_id, pay_month;
```

> 注意：滑动累计用 `ROWS` 帧假设月份连续；若存在缺月，应先补齐月历再计算，避免「3 行」不等于「3 个月」。
""",
    ),
]


async def _ensure_categories(db: AsyncSession) -> dict[str, int]:
    slug_to_id: dict[str, int] = {}
    for c in CATEGORIES:
        existing = await db.scalar(
            select(Category).where(Category.section == "sql", Category.slug == c["slug"])
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

        existing_by_title = {
            row.title: row for row in (await db.execute(select(SqlQuestion))).scalars().all()
        }

        inserted = 0
        updated = 0
        for q in QUESTIONS:
            row = existing_by_title.get(q["title"])
            if row is None:
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
            else:
                # upsert：更新正文，便于迭代题目内容。
                row.category_id = slug_to_id[q["cat"]]
                row.difficulty = q["difficulty"]
                row.prompt_md = q["prompt_md"]
                row.answer_md = q["answer_md"]
                row.tags = q["tags"]
                row.status = "published"
                updated += 1

        await db.commit()
        print(
            f"SQL 题库灌入完成：题型 {len(slug_to_id)} 个；新增 {inserted} 道、更新 {updated} 道"
            f"（共 {len(QUESTIONS)} 道）。"
        )


if __name__ == "__main__":
    asyncio.run(seed_sql_bank())
