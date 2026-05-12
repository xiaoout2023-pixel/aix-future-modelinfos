# 数据结构说明（Data Schema Reference）

本文档详细描述数据库中每张表、每个字段的含义、类型、取值范围和示例，供 API 后端开发使用。

---

## 表总览

| 表名 | 说明 | 主键 | 数据量级 |
|------|------|------|----------|
| `models` | AI 模型基本信息与能力标签 | `model_id` | 300+ |
| `pricing` | 模型定价信息（支持多渠道、多区域、多时间点） | `pricing_id` | 500+ |
| `evaluations` | 第三方独立评测分数与性能数据 | `eval_id` | 800+ |
| `change_log` | 数据变更记录（审计追踪） | `id` (自增) | 持续增长 |

### 表关系

```
models (1) ──── (N) pricing       通过 model_id 关联
models (1) ──── (N) evaluations   通过 model_id 关联
models (1) ──── (N) change_log    通过 model_id 关联
```

> 注意：当前数据库已禁用外键约束（`PRAGMA foreign_keys = OFF`），关联关系为逻辑关联，非物理外键。

---

## 1. models 表

AI 模型的基本信息，包括名称、厂商、能力、上下文长度等。

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `model_id` | TEXT | ✅ PK | — | 模型唯一标识，格式：`{provider}/{model-slug}`，例如 `openai/gpt-4o-2024-08-06`、`anthropic/claude-opus-4-7`、`google/gemini-2.5-pro` |
| `model_name` | TEXT | ✅ | — | 模型显示名称，例如 `GPT-4o`、`Claude Opus 4.7`、`Gemini 2.5 Pro` |
| `provider` | TEXT | ✅ | — | 厂商标识（小写），例如 `openai`、`anthropic`、`google`、`deepseek`、`meta`、`mistral`、`alibaba`、`xai` |
| `provider_type` | TEXT | ❌ | NULL | 厂商类型：`open_source`（开源）或 `closed`（闭源） |
| `release_date` | TEXT | ❌ | NULL | 模型发布日期，格式 `YYYY-MM-DD`，例如 `2024-08-06` |
| `status` | TEXT | ❌ | `active` | 模型状态，枚举值：`active`（可用）、`beta`（测试中）、`deprecated`（已废弃）、`coming_soon`（即将上线） |
| `aliases` | TEXT | ❌ | `[]` | 模型别名列表，JSON 数组，例如 `["gpt-4o-latest", "gpt4o"]` |
| `capabilities` | TEXT | ❌ | `{}` | 模型能力标签，JSON 对象，详见下方 **capabilities 字段结构** |
| `context_length` | INTEGER | ❌ | NULL | 最大上下文窗口长度（token 数），例如 `128000`、`200000`、`1000000` |
| `max_output_tokens` | INTEGER | ❌ | NULL | 单次请求最大输出 token 数，例如 `4096`、`16384`、`64000` |
| `regions` | TEXT | ❌ | `[]` | 支持的部署区域列表，JSON 数组，例如 `["us", "eu", "ap"]`，空数组表示全球可用 |
| `private_deployment` | INTEGER | ❌ | `0` | 是否支持私有部署，`0` = 不支持，`1` = 支持 |
| `openai_compatible` | INTEGER | ❌ | `0` | 是否兼容 OpenAI API 格式，`0` = 不兼容，`1` = 兼容 |
| `urls` | TEXT | ❌ | `{}` | 相关链接，JSON 对象，详见下方 **urls 字段结构** |
| `tags` | TEXT | ❌ | `[]` | 自定义标签列表，JSON 数组，例如 `["flagship", "reasoning", "vision"]` |
| `last_updated` | TEXT | ❌ | NULL | 最后更新时间，ISO 8601 格式，例如 `2026-05-13T02:00:00+00:00` |

### capabilities 字段结构

`capabilities` 是 JSON 对象，每个键为布尔值：

```json
{
  "text": true,
  "code": true,
  "reasoning": true,
  "vision": true,
  "image_gen": false,
  "audio": true,
  "audio_gen": false,
  "video": false,
  "tool_use": true,
  "structured_output": true,
  "streaming": true,
  "batch": true,
  "fine_tuning": false,
  "embedding": false
}
```

| 键 | 类型 | 说明 |
|----|------|------|
| `text` | bool | 文本生成 |
| `code` | bool | 代码生成 |
| `reasoning` | bool | 推理能力（支持 chain-of-thought） |
| `vision` | bool | 图像理解（多模态输入） |
| `image_gen` | bool | 图像生成 |
| `audio` | bool | 音频理解 |
| `audio_gen` | bool | 音频生成 |
| `video` | bool | 视频理解 |
| `tool_use` | bool | 工具调用 / Function Calling |
| `structured_output` | bool | 结构化输出（JSON Mode） |
| `streaming` | bool | 流式输出 |
| `batch` | bool | 批处理 API |
| `fine_tuning` | bool | 支持微调 |
| `embedding` | bool | 向量嵌入 |

### urls 字段结构

```json
{
  "official": "https://openai.com/gpt-4o",
  "docs": "https://platform.openai.com/docs/guides/gpt-4o",
  "pricing": "https://openai.com/pricing"
}
```

| 键 | 类型 | 说明 |
|----|------|------|
| `official` | string? | 模型官方介绍页 |
| `docs` | string? | API 文档页 |
| `pricing` | string? | 定价页 |

### models 表示例

```json
{
  "model_id": "openai/gpt-4o-2024-08-06",
  "model_name": "GPT-4o",
  "provider": "openai",
  "provider_type": "closed",
  "release_date": "2024-08-06",
  "status": "active",
  "aliases": "[\"gpt-4o-latest\"]",
  "capabilities": "{\"text\":true,\"code\":true,\"reasoning\":true,\"vision\":true,\"tool_use\":true,\"structured_output\":true,\"streaming\":true}",
  "context_length": 128000,
  "max_output_tokens": 16384,
  "regions": "[]",
  "private_deployment": 0,
  "openai_compatible": 1,
  "urls": "{\"official\":\"https://openai.com/gpt-4o\",\"docs\":\"https://platform.openai.com/docs\"}",
  "tags": "[\"flagship\",\"vision\"]",
  "last_updated": "2026-05-13T02:00:00+00:00"
}
```

---

## 2. pricing 表

模型定价信息。同一个模型可以有多条定价记录（不同渠道、不同区域、不同时间点）。

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `pricing_id` | TEXT | ✅ PK | — | 定价记录唯一标识，格式：`{model_id}/{channel}/{region}/{valid_from}`，例如 `openai/gpt-4o-2024-08-06/official/global/2024-08-06` |
| `model_id` | TEXT | ✅ | — | 关联的模型 ID，与 models.model_id 对应 |
| `channel` | TEXT | ❌ | `official` | 定价渠道，枚举值：`official`（官方直供）、`marketplace`（第三方市场如 AWS Bedrock）、`reseller`（转售商） |
| `market_name` | TEXT | ❌ | NULL | 在该渠道的市场名称，例如 AWS Bedrock 上的模型名可能与官方不同 |
| `region` | TEXT | ❌ | `global` | 定价区域，例如 `global`、`us`、`eu`、`ap` |
| `valid_from` | TEXT | ✅ | — | 价格生效日期，格式 `YYYY-MM-DD`，同一模型不同日期的记录表示价格变更历史 |
| `currency` | TEXT | ❌ | `USD` | 货币单位，目前均为 `USD` |
| `input_price_per_1m` | REAL | ❌ | NULL | 输入价格，每百万 token 的美元价格，例如 `2.5` 表示 $2.50/1M tokens |
| `output_price_per_1m` | REAL | ❌ | NULL | 输出价格，每百万 token 的美元价格，例如 `10.0` 表示 $10.00/1M tokens |
| `cache_read_price_per_1m` | REAL | ❌ | NULL | 缓存读取价格，每百万 token，例如 `0.25`。部分模型（如 Anthropic）支持 Prompt Caching，读取缓存的 token 更便宜 |
| `cache_write_price_per_1m` | REAL | ❌ | NULL | 缓存写入价格，每百万 token，例如 `1.25`。写入缓存通常比普通输入贵，但后续读取便宜 |
| `reasoning_tokens_charged` | INTEGER | ❌ | `0` | 是否对推理 token（thinking tokens）计费，`0` = 不计费，`1` = 计费。OpenAI o 系列模型会收取推理 token 费用 |
| `reasoning_overhead_ratio` | REAL | ❌ | NULL | 推理 token 开销比例，例如 `4.0` 表示推理 token 数量是输出 token 的 4 倍 |
| `price_per_request` | REAL | ❌ | NULL | 按次计费价格（USD/次），用于不按 token 计费的模型 |
| `price_per_image` | REAL | ❌ | NULL | 图像生成单价（USD/张） |
| `price_per_audio_min` | REAL | ❌ | NULL | 音频处理单价（USD/分钟） |
| `tiers` | TEXT | ❌ | NULL | 阶梯价格，JSON 格式，例如 `[{"min_tokens": 0, "input_price": 2.5}, {"min_tokens": 1000000, "input_price": 1.25}]` |
| `volume_discount` | TEXT | ❌ | NULL | 批量折扣信息，JSON 格式 |
| `reserved_discount_pct` | REAL | ❌ | NULL | 预留实例折扣百分比，例如 `30.0` 表示 7 折 |
| `free_tier_tokens` | INTEGER | ❌ | NULL | 免费额度（token 数/月），例如 `1000000` 表示每月 100 万 token 免费 |
| `min_billable_tokens` | INTEGER | ❌ | NULL | 最小计费 token 数，不足此数量仍按此数量计费 |
| `rounding_unit` | INTEGER | ❌ | NULL | 计费取整单位（token 数），例如 `1` 表示精确计费，`1000` 表示每千 token 取整 |
| `has_spot` | INTEGER | ❌ | `0` | 是否支持竞价实例（Spot Pricing），`0` = 不支持，`1` = 支持 |
| `source` | TEXT | ❌ | NULL | 价格数据来源 URL |
| `last_verified` | TEXT | ❌ | NULL | 最后验证时间，ISO 8601 格式 |

### pricing 表示例

```json
{
  "pricing_id": "openai/gpt-4o-2024-08-06/official/global/2024-08-06",
  "model_id": "openai/gpt-4o-2024-08-06",
  "channel": "official",
  "market_name": null,
  "region": "global",
  "valid_from": "2024-08-06",
  "currency": "USD",
  "input_price_per_1m": 2.5,
  "output_price_per_1m": 10.0,
  "cache_read_price_per_1m": 1.25,
  "cache_write_price_per_1m": null,
  "reasoning_tokens_charged": 0,
  "reasoning_overhead_ratio": null,
  "price_per_request": null,
  "price_per_image": null,
  "price_per_audio_min": null,
  "tiers": null,
  "volume_discount": null,
  "reserved_discount_pct": null,
  "free_tier_tokens": null,
  "min_billable_tokens": null,
  "rounding_unit": null,
  "has_spot": 0,
  "source": "https://openai.com/pricing",
  "last_verified": "2026-05-13T02:00:00+00:00"
}
```

### 常用查询

```sql
-- 获取某模型最新官方全球定价
SELECT * FROM pricing
WHERE model_id = 'openai/gpt-4o-2024-08-06'
  AND channel = 'official'
  AND region = 'global'
ORDER BY valid_from DESC LIMIT 1;

-- 获取某模型所有渠道的定价
SELECT channel, region, input_price_per_1m, output_price_per_1m
FROM pricing
WHERE model_id = 'openai/gpt-4o-2024-08-06'
ORDER BY valid_from DESC;

-- 价格历史趋势
SELECT valid_from, input_price_per_1m, output_price_per_1m
FROM pricing
WHERE model_id = 'openai/gpt-4o-2024-08-06'
  AND channel = 'official'
ORDER BY valid_from;
```

---

## 3. evaluations 表

第三方独立评测数据。所有分数均来自独立第三方评测机构，不包含厂商自报分数。

| 字段 | 类型 | 必填 | 默认值 | 数据来源 | 说明 |
|------|------|------|--------|----------|------|
| `eval_id` | TEXT | ✅ PK | — | — | 评测记录唯一标识，格式：`{model_id}/{source_name}/{date}`，例如 `openai/gpt-4o-2024-08-06/artificialanalysis/2026-05-13`、`openai/gpt-4o-2024-08-06/lmarena/2026-05-13` |
| `model_id` | TEXT | ✅ | — | — | 关联的模型 ID，与 models.model_id 对应 |
| `eval_date` | TEXT | ✅ | — | — | 评测数据采集日期，格式 `YYYY-MM-DD` |
| `source` | TEXT | ✅ | — | — | 数据来源 URL，例如 `https://artificialanalysis.ai`、`https://lmarena.ai`、`https://llm-registry.com/api/v1` |
| `mmlu` | REAL | ❌ | NULL | LLM Registry | MMLU (Massive Multitask Language Understanding) 分数，范围 0-100，综合知识评测 |
| `mmlu_pro` | REAL | ❌ | NULL | AA / LLM Registry | MMLU-Pro 分数。AA 来源范围 0-1（比例值），LLM Registry 来源范围 0-100（百分制）。更严格的 MMLU 升级版，减少随机猜测 |
| `gpqa` | REAL | ❌ | NULL | AA / LLM Registry | GPQA Diamond 分数。AA 来源范围 0-1，LLM Registry 来源范围 0-100。研究生级别科学推理评测 |
| `aa_intelligence_index` | REAL | ❌ | NULL | AA | Artificial Analysis 综合智能评分，范围 0-100。基于 10 项评测（含 GDPval-AA、Terminal-Bench Hard、GPQA 等）的加权综合分，是最核心的模型能力指标 |
| `aa_coding_index` | REAL | ❌ | NULL | AA | Artificial Analysis 代码能力评分，范围 0-100。基于 LiveCodeBench、Terminal-Bench 等代码评测 |
| `aa_math_index` | REAL | ❌ | NULL | AA | Artificial Analysis 数学能力评分，范围 0-100。基于 AIME、MATH 等数学评测 |
| `hle` | REAL | ❌ | NULL | AA | Humanity's Last Exam 分数，范围 0-1。号称"人类最后的考试"，极难的多学科评测 |
| `aime` | REAL | ❌ | NULL | AA | AIME (American Invitational Mathematics Examination) 分数，范围 0-1。美国数学邀请赛级别竞赛题 |
| `livecodebench` | REAL | ❌ | NULL | AA | LiveCodeBench 分数，范围 0-1。实时更新的代码生成评测 |
| `scicode` | REAL | ❌ | NULL | AA | SciCode 分数，范围 0-1。科学计算代码生成评测 |
| `ifbench` | REAL | ❌ | NULL | AA | IFBench (Instruction Following Benchmark) 分数，范围 0-1。指令遵循能力评测 |
| `aa_lcr` | REAL | ❌ | NULL | AA | Artificial Analysis 长上下文推理 (Long Context Reasoning) 分数，范围 0-1 |
| `lmarena_elo` | REAL | ❌ | NULL | LMArena | LMArena 综合对战 Elo 评分，范围约 500-2000。基于真人匿名对战投票，500万+ 票，是用户偏好的黄金标准 |
| `lmarena_coding` | REAL | ❌ | NULL | LMArena | LMArena 代码对战 Elo，范围约 500-2000。代码场景下的用户偏好排名 |
| `lmarena_math` | REAL | ❌ | NULL | LMArena | LMArena 数学对战 Elo，范围约 500-2000。数学场景下的用户偏好排名 |
| `lmarena_hard` | REAL | ❌ | NULL | LMArena | LMArena 难题对战 Elo，范围约 500-2000。高难度提示词场景下的用户偏好排名 |
| `other_benchmarks` | TEXT | ❌ | NULL | 多种 | 其他未单独建列的 benchmark 分数，JSON 对象，例如 `{"aime_25": 0.934, "terminalbench_hard": 0.235, "tau2": 0.658}` |
| `tokens_per_second` | INTEGER | ❌ | NULL | AA | 输出速度（tokens/秒），数值越大越快。例如 `208` 表示每秒输出 208 个 token |
| `avg_latency_ms` | INTEGER | ❌ | NULL | — | 平均延迟（毫秒），目前无数据源 |
| `p95_latency_ms` | INTEGER | ❌ | NULL | — | P95 延迟（毫秒），目前无数据源 |
| `ttft_ms` | INTEGER | ❌ | NULL | AA | 首 Token 延迟 / Time To First Token（毫秒）。从发送请求到收到第一个 token 的时间，例如 `489` 表示 489ms |
| `reasoning_level` | TEXT | ❌ | NULL | — | 推理等级，枚举值：`low`、`medium`、`high`，目前无数据源 |
| `overall_score` | REAL | ❌ | NULL | — | 综合评分，目前无数据源，建议使用 `aa_intelligence_index` 替代 |
| `cost_efficiency_score` | REAL | ❌ | NULL | — | 性价比评分，目前无数据源，可自行计算 `aa_intelligence_index / blended_price` |

### ⚠️ 分数量纲说明

不同来源的分数量纲不同，API 展示时需要注意：

| 来源 | 分数量纲 | 示例 |
|------|----------|------|
| **Artificial Analysis** | 比例值 0-1 | `gpqa = 0.521` 表示 52.1% |
| **Artificial Analysis** (index 类) | 0-100 | `aa_intelligence_index = 57.3` |
| **LMArena** | Elo 评分 | `lmarena_elo = 1464` |
| **LLM Registry** | 百分制 0-100 | `gpqa = 65.6` 表示 65.6 分 |

> **特别注意**：`mmlu_pro` 和 `gpqa` 字段同时存在 AA（0-1）和 LLM Registry（0-100）两种来源的数据。同一模型同一字段，不同来源的 eval_id 不同，但值需要乘以 100 才能对齐。API 展示时建议：
> - 方案 A：统一转换为百分制展示
> - 方案 B：按 source 分开展示，标注量纲

### evaluations 表示例

```json
{
  "eval_id": "openai/gpt-4o-2024-08-06/artificialanalysis/2026-05-13",
  "model_id": "openai/gpt-4o-2024-08-06",
  "eval_date": "2026-05-13",
  "source": "https://artificialanalysis.ai",
  "mmlu": null,
  "mmlu_pro": null,
  "gpqa": 0.521,
  "aa_intelligence_index": 18.6,
  "aa_coding_index": 16.6,
  "aa_math_index": null,
  "hle": 0.029,
  "aime": 0.117,
  "livecodebench": 0.317,
  "scicode": 0.331,
  "ifbench": 0.36,
  "aa_lcr": 0.35,
  "lmarena_elo": null,
  "lmarena_coding": null,
  "lmarena_math": null,
  "lmarena_hard": null,
  "other_benchmarks": null,
  "tokens_per_second": 99,
  "avg_latency_ms": null,
  "p95_latency_ms": null,
  "ttft_ms": 489,
  "reasoning_level": null,
  "overall_score": null,
  "cost_efficiency_score": null
}
```

```json
{
  "eval_id": "openai/gpt-4o-2024-08-06/lmarena/2026-05-13",
  "model_id": "openai/gpt-4o-2024-08-06",
  "eval_date": "2026-05-13",
  "source": "https://lmarena.ai",
  "mmlu": null,
  "mmlu_pro": null,
  "gpqa": null,
  "aa_intelligence_index": null,
  "aa_coding_index": null,
  "aa_math_index": null,
  "hle": null,
  "aime": null,
  "livecodebench": null,
  "scicode": null,
  "ifbench": null,
  "aa_lcr": null,
  "lmarena_elo": 1287.22,
  "lmarena_coding": 1289.14,
  "lmarena_math": 1270.59,
  "lmarena_hard": 1266.14,
  "other_benchmarks": null,
  "tokens_per_second": null,
  "avg_latency_ms": null,
  "p95_latency_ms": null,
  "ttft_ms": null,
  "reasoning_level": null,
  "overall_score": null,
  "cost_efficiency_score": null
}
```

### 常用查询

```sql
-- 获取某模型的所有评测数据（来自不同源）
SELECT * FROM evaluations
WHERE model_id = 'openai/gpt-4o-2024-08-06';

-- 获取某模型最新 AA 评测
SELECT * FROM evaluations
WHERE model_id = 'openai/gpt-4o-2024-08-06'
  AND source = 'https://artificialanalysis.ai'
ORDER BY eval_date DESC LIMIT 1;

-- 获取某模型最新 LMArena 评测
SELECT * FROM evaluations
WHERE model_id = 'openai/gpt-4o-2024-08-06'
  AND source = 'https://lmarena.ai'
ORDER BY eval_date DESC LIMIT 1;

-- Intelligence Index Top 20
SELECT model_id, aa_intelligence_index, tokens_per_second, ttft_ms
FROM evaluations
WHERE aa_intelligence_index IS NOT NULL
ORDER BY aa_intelligence_index DESC
LIMIT 20;

-- LMArena Elo Top 20
SELECT model_id, lmarena_elo, lmarena_coding, lmarena_math, lmarena_hard
FROM evaluations
WHERE lmarena_elo IS NOT NULL
ORDER BY lmarena_elo DESC
LIMIT 20;

-- 性价比分析
SELECT e.model_id,
       e.aa_intelligence_index,
       p.input_price_per_1m,
       p.output_price_per_1m,
       ROUND(e.aa_intelligence_index / NULLIF(p.output_price_per_1m, 0), 2) AS value_ratio
FROM evaluations e
JOIN pricing p ON e.model_id = p.model_id
  AND p.channel = 'official'
  AND p.region = 'global'
WHERE e.aa_intelligence_index IS NOT NULL
  AND e.source = 'https://artificialanalysis.ai'
ORDER BY value_ratio DESC
LIMIT 20;

-- 模型完整视图（模型 + 最新定价 + 最新评测）
SELECT m.model_id, m.model_name, m.provider, m.context_length,
       p.input_price_per_1m, p.output_price_per_1m,
       e.aa_intelligence_index, e.lmarena_elo, e.tokens_per_second
FROM models m
LEFT JOIN pricing p ON m.model_id = p.model_id
  AND p.channel = 'official' AND p.region = 'global'
LEFT JOIN evaluations e ON m.model_id = e.model_id
  AND e.source = 'https://artificialanalysis.ai'
ORDER BY e.aa_intelligence_index DESC;
```

---

## 4. change_log 表

数据变更审计日志，记录每次采集时发生的字段变更。

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `id` | INTEGER | ✅ PK (自增) | — | 日志记录 ID |
| `table_name` | TEXT | ✅ | — | 变更所在的表名，枚举值：`models`、`pricing`、`evaluations` |
| `model_id` | TEXT | ✅ | — | 变更关联的模型 ID |
| `field_name` | TEXT | ✅ | — | 变更的字段名，例如 `input_price_per_1m`、`status`、`aa_intelligence_index` |
| `old_value` | TEXT | ❌ | NULL | 变更前的值（字符串形式），`NULL` 表示新增字段 |
| `new_value` | TEXT | ❌ | NULL | 变更后的值（字符串形式），`NULL` 表示字段被删除 |
| `changed_at` | TEXT | ✅ | — | 变更发生时间，ISO 8601 格式，例如 `2026-05-13T02:00:00+00:00` |
| `source_url` | TEXT | ❌ | NULL | 触发变更的数据来源 URL |

### change_log 表示例

```json
{
  "id": 42,
  "table_name": "pricing",
  "model_id": "openai/gpt-4o-2024-08-06",
  "field_name": "input_price_per_1m",
  "old_value": "5.0",
  "new_value": "2.5",
  "changed_at": "2026-05-13T02:00:00+00:00",
  "source_url": "https://openai.com/pricing"
}
```

### 常用查询

```sql
-- 某模型的所有变更历史
SELECT * FROM change_log
WHERE model_id = 'openai/gpt-4o-2024-08-06'
ORDER BY changed_at DESC;

-- 最近 7 天的价格变更
SELECT * FROM change_log
WHERE table_name = 'pricing'
  AND changed_at >= datetime('now', '-7 days')
ORDER BY changed_at DESC;

-- 某字段的所有变更记录
SELECT model_id, old_value, new_value, changed_at
FROM change_log
WHERE field_name = 'input_price_per_1m'
ORDER BY changed_at DESC
LIMIT 20;
```

---

## 附录：数据来源说明

| 来源标识 | 机构 | 评测方法 | 权威性 | 数据量 |
|----------|------|----------|--------|--------|
| `https://artificialanalysis.ai` | Artificial Analysis | 独立运行标准化测试，零样本，透明方法论 v2.2 | 被 OpenAI/Google/Anthropic/NVIDIA/FT/Economist 引用 | 516 模型 |
| `https://lmarena.ai` | LMArena (Chatbot Arena) | 真人匿名对战投票 | 用户偏好排名的黄金标准，500万+ 票 | 282 模型 |
| `https://llm-registry.com/api/v1` | LLM Registry | 聚合多来源数据（仅保留第三方独立来源） | 聚合平台，数据来自 AA/LiveBench/LMArena 等 | 45 模型 |

## 附录：provider 枚举值

当前数据库中出现的 provider 值：

| provider | 厂商 |
|----------|------|
| `openai` | OpenAI |
| `anthropic` | Anthropic |
| `google` | Google |
| `meta` | Meta |
| `deepseek` | DeepSeek |
| `mistral` | Mistral |
| `alibaba` | Alibaba (Qwen) |
| `nvidia` | NVIDIA |
| `xai` | xAI (Grok) |
| `zhipu` | Z.ai / 智谱 (GLM) |
| `cohere` | Cohere |
| `minimax` | MiniMax |
| `moonshot` | Moonshot (Kimi) |
| `xiaomi` | Xiaomi |
| `microsoft` | Microsoft |
| `amazon` | Amazon |
| `reka` | Reka |
| `01ai` | 01.AI (Yi) |
| `ai21` | AI21 Labs |
| `cerebras` | Cerebras |
| `groq` | Groq |
| `together` | Together AI |
| `perplexity` | Perplexity |
