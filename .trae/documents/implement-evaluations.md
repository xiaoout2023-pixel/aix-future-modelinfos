# 实现 Evaluations 数据采集计划

## 数据源确认

**主数据源：llm-registry.com API**（免费、无需认证、Cloudflare CDN 全球加速）

| 端点                    | 数据                                          | 示例                                       |
| --------------------- | ------------------------------------------- | ---------------------------------------- |
| `/api/v1/models`      | 1584 个模型列表 + 基础信息                           | 模型名、provider、参数量、上下文长度、定价                |
| `/api/v1/models/{id}` | 单模型详情 + 所有 benchmark 分数                     | mmlu, gpqa-diamond, swe-bench-verified 等 |
| `/api/v1/scores`      | 1180+ 条评测分数，支持按 model/benchmark/category 过滤 | score, normalizedScore, source, asOfDate |
| `/api/v1/benchmarks`  | 229 个 benchmark 定义                          | id, name, category, maxScore             |

**已验证可获取的 benchmark 数据**（以 Claude Opus 4.6 为例）：

* `mmlu`: 91.4 ✅

* `mmlu-pro`: 82.2 ✅

* `gpqa-diamond`: 84 ✅

* `math`: 89.2 ✅

* `human-eval`: 94.6 ✅

* `swe-bench-verified`: 80.8 ✅

* `arc-agi-2`: 68.8 ✅

* `mmmu`: 76.5 ✅

* `lmarena-elo`: 1502 ✅

* `livebench`: 76.33 ✅

* `aa-intelligence-index`: 46.4 ✅

* `aa-coding-index`: 47.6 ✅

**性能数据**（tokens\_per\_second, avg\_latency\_ms, ttft\_ms）：llm-registry 不含性能数据，需要从 Artificial Analysis 页面爬取（JS 渲染，GitHub Actions 环境可能 403）。暂不实现性能数据采集，保留字段为 NULL。

## Schema 变更

### evaluations 表新增字段

```sql
ALTER TABLE evaluations ADD COLUMN mmlu_pro REAL;
ALTER TABLE evaluations ADD COLUMN gpqa REAL;
ALTER TABLE evaluations ADD COLUMN math_500 REAL;
ALTER TABLE evaluations ADD COLUMN arc_challenge REAL;
ALTER TABLE evaluations ADD COLUMN swe_bench REAL;
ALTER TABLE evaluations ADD COLUMN needle_haystack REAL;
ALTER TABLE evaluations ADD COLUMN bfcl REAL;
ALTER TABLE evaluations ADD COLUMN lmarena_elo REAL;
ALTER TABLE evaluations ADD COLUMN ttft_ms INTEGER;
```

### 字段映射（llm-registry benchmark\_id → DB 字段）

| DB 字段             | llm-registry benchmark\_id | 说明                                                           |
| ----------------- | -------------------------- | ------------------------------------------------------------ |
| mmlu              | mmlu                       | 通用知识（已有）                                                     |
| mmlu\_pro         | mmlu-pro                   | MMLU 增强版                                                     |
| gpqa              | gpqa-diamond               | 研究生级科学推理                                                     |
| gsm8k             | —                          | 数学推理（已有，llm-registry 无此 benchmark，放 other\_benchmarks）       |
| math\_500         | math                       | 高等数学                                                         |
| arc\_challenge    | —                          | 科学常识（llm-registry 无，放 other\_benchmarks）                     |
| humaneval         | human-eval                 | 代码（已有）                                                       |
| swe\_bench        | swe-bench-verified         | 真实软件工程                                                       |
| needle\_haystack  | —                          | 长文本检索（llm-registry 无，放 other\_benchmarks）                    |
| bfcl              | —                          | 函数调用（llm-registry 无，放 other\_benchmarks）                     |
| lmarena\_elo      | lmarena-elo                | 真实用户对战排名                                                     |
| ttft\_ms          | —                          | 首 token 延迟（暂无数据源）                                            |
| other\_benchmarks | JSON                       | 其余所有 benchmark（arc-agi-2, mmmu, livebench, terminal-bench 等） |

## 实现步骤

### Step 1: 更新 DB Schema

* 修改 `db.py` 中 `SCHEMA_SQL` 的 evaluations 表定义，添加新字段

* 注意：SQLite 不支持 ALTER TABLE ADD COLUMN 一次性加多列，但 SCHEMA\_SQL 是 CREATE TABLE IF NOT EXISTS，新建数据库会自动用新 schema。对于已有数据库，需要添加迁移逻辑

### Step 2: 更新 models.py 的 EvalInfo

* 在 `EvalInfo` Pydantic 模型中添加新字段

* 保持所有新字段为 Optional

### Step 3: 新建 llmregistry parser

* 创建 `collector/src/modelinfo/parsers/llmregistry.py`

* 实现 `fetch_evaluations()` 方法：

  1. 调用 `/api/v1/models` 获取模型列表
  2. 对每个模型调用 `/api/v1/models/{id}` 获取 scores
  3. 将 scores 映射到 evaluations 表字段
  4. 未映射的 benchmark 放入 `other_benchmarks` JSON

* 不实现 `fetch_models()` 和 `fetch_pricing()`（已有其他 parser 负责）

### Step 4: 注册新 parser

* 在 `cli.py` 的 source 映射中添加 `llmregistry`

* 在 `collect` 命令中支持 `--table evaluations`

### Step 5: 更新 Workflow

* 在 `weekly-full-collect.yml` 中添加 evaluations 采集步骤

* evaluations 不需要每天采集，每周一次即可

### Step 6: 添加测试

* 创建 `collector/tests/parsers/test_llmregistry.py`

* 使用 fixture 测试 benchmark 映射逻辑

* 测试 other\_benchmarks JSON 的生成

### Step 7: 数据库迁移（兼容已有数据）

* 在 `db.py` 中添加 `_migrate_evaluations_table()` 方法

* 检查新字段是否存在，不存在则 ALTER TABLE ADD COLUMN

* 在 `init_schema()` 中调用迁移

## 风险与注意事项

1. **API 限流**：llm-registry 是静态 API，无认证，但大量请求可能触发 Cloudflare 限流。建议每次请求间隔 0.5s
2. **模型 ID 映射**：llm-registry 的 modelId（如 `claude-opus-4-6`）与我们 DB 的 model\_id（如 `anthropic/claude-opus-4.6`）格式不同，需要做映射
3. **数据新鲜度**：llm-registry 数据是定期导出的，不是实时的。meta 端点可查看最新日期
4. **性能数据缺失**：tokens\_per\_second、avg\_latency\_ms、ttft\_ms 暂无可靠数据源，字段保留为 NULL

