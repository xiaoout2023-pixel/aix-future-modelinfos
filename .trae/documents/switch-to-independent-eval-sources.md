# 切换到第三方独立评测数据源计划

## 背景

当前 evaluations 数据源是 llm-registry.com，它聚合了 provider 自报分数和第三方测试，混合在一起。用户要求**只要第三方独立评测数据**，需要切换数据源。

## 数据源确认

### 数据源1：Artificial Analysis API

* **API 端点**：需 API Key（免费获取，在 artificialanalysis.ai/insights）

* **请求方式**：`GET https://api.artificialanalysis.ai/v1/models` + `GET https://api.artificialanalysis.ai/v1/models/{slug}`

* **认证**：`Authorization: Bearer {AA_API_KEY}, APIKey {aa_AmbCDVRguGrExccpSkGwqMRggaNIBcoL}`

* **数据内容**：

  * Intelligence Index（综合智能评分）

  * Coding Index（代码能力）

  * Math Index（数学能力）

  * MMLU-Pro, GPQA Diamond, HLE, AIME, LiveCodeBench, SciCode, IFBench, AA-LCR

  * 性能数据：tokens/sec, TTFT（首 token 延迟）

  * 定价数据：input/output/blended price

* **评测方法**：独立运行，标准化测试，零样本，透明方法论（v2.2）

* **权威性**：被 OpenAI, Google, Anthropic, NVIDIA, FT, Economist 引用

* **限制**：1K req/天（免费 key）

### 数据源2：LMArena (Chatbot Arena)

* **数据端点**：`https://raw.githubusercontent.com/lmarena/arena-catalog/main/data/leaderboard-text.json`

* **无需认证**，完全免费

* **数据格式**：

  ```json
  {
    "full": {"claude-opus-4-6": {"rating": 1502, "rating_q975": 1508, "rating_q025": 1496}},
    "coding": {...},
    "math": {...},
    "english": {...},
    "hard_6": {...},
    ...
  }
  ```

* **数据内容**：29 个分类的 Elo 评分（full, coding, math, english, hard\_6, creative\_writing, if, industry\_\* 等）

* **评测方法**：真人匿名对战投票，500万+ 票

* **权威性**：用户偏好排名的黄金标准

### 数据源3：llm-registry（保留，仅过滤第三方数据）

* 过滤 `sourceId` 只保留 `artificial-analysis` 和 `livebench` 来源的分数

* 作为补充数据源（覆盖 llm-registry 独有的 benchmark）

## Schema 变更

### evaluations 表字段调整

基于 Artificial Analysis 的实际评测维度，更新字段映射：

| DB 字段               | AA 字段               | 说明                               |
| ------------------- | ------------------- | -------------------------------- |
| mmlu\_pro           | mmlu\_pro           | AA 独立测试的 MMLU-Pro                |
| gpqa                | gpqa                | AA 独立测试的 GPQA Diamond            |
| humaneval           | —                   | AA 不测 HumanEval，改用 LiveCodeBench |
| swe\_bench          | —                   | AA 不测 SWE-bench                  |
| math\_500           | —                   | 改用 AIME                          |
| lmarena\_elo        | LMArena full.rating | 真人对战 Elo                         |
| tokens\_per\_second | speed               | AA 性能测试                          |
| ttft\_ms            | ttft                | AA 性能测试                          |

**新增字段**：

| DB 字段                   | 来源      | 说明                   |
| ----------------------- | ------- | -------------------- |
| aa\_intelligence\_index | AA      | 综合智能评分（最核心指标）        |
| aa\_coding\_index       | AA      | 代码能力评分               |
| aa\_math\_index         | AA      | 数学能力评分               |
| hle                     | AA      | Humanity's Last Exam |
| aime                    | AA      | 竞赛数学                 |
| livecodebench           | AA      | 代码生成                 |
| scicode                 | AA      | 科学计算代码               |
| ifbench                 | AA      | 指令遵循                 |
| aa\_lcr                 | AA      | 长上下文推理               |
| lmarena\_coding         | LMArena | 代码对战 Elo             |
| lmarena\_math           | LMArena | 数学对战 Elo             |
| lmarena\_hard           | LMArena | 难题对战 Elo             |

**删除字段**（不再有数据源）：

* `gsm8k` — AA 不测，llm-registry 只有 provider 自报

* `arc_challenge` — 无第三方数据

* `needle_haystack` — 无第三方数据

* `bfcl` — 无第三方数据

* `swe_bench` — AA 不测，llm-registry 只有 provider 自报

* `math_500` — 改用 aime

* `humaneval` — AA 不测，改用 livecodebench

**保留字段**（但数据来源改变）：

* `mmlu` → 保留但数据来自 AA 的 mmlu\_pro（更严格）

* `overall_score` → 用 aa\_intelligence\_index 替代

## 实施步骤

### Step 1: 更新 DB Schema

修改 `db.py` 中 evaluations 表定义：

* 新增字段：aa\_intelligence\_index, aa\_coding\_index, aa\_math\_index, hle, aime, livecodebench, scicode, ifbench, aa\_lcr, lmarena\_coding, lmarena\_math, lmarena\_hard

* 删除字段：gsm8k, arc\_challenge, needle\_haystack, bfcl, swe\_bench, math\_500, humaneval（从 CREATE TABLE 中移除，迁移时忽略旧列）

* 更新迁移逻辑

### Step 2: 更新 models.py EvalInfo

同步更新 Pydantic 模型字段

### Step 3: 新建 Artificial Analysis parser

创建 `collector/src/modelinfo/parsers/artificialanalysis.py`：

* 使用 AA\_API\_KEY 环境变量认证

* 调用 `/v1/models` 获取模型列表 + 评分

* 调用 `/v1/models/{slug}` 获取详细评分

* 映射到 evaluations 表字段

* 同时采集性能数据（tokens/sec, TTFT）

### Step 4: 新建 LMArena parser

创建 `collector/src/modelinfo/parsers/lmarena.py`：

* 从 GitHub JSON 获取 leaderboard 数据

* 映射 full/coding/math/hard\_6 的 Elo 评分

* 无需认证

### Step 5: 修改 llmregistry parser

* 添加 `sourceId` 过滤，只保留 `artificial-analysis` 和 `livebench` 来源的分数

* 作为补充数据源

### Step 6: 更新 cli.py

* 注册新 parser：artificialanalysis, lmarena

* AA\_API\_KEY 环境变量配置

### Step 7: 更新 Workflow

* 添加 AA\_API\_KEY 到 GitHub Secrets

* evaluations 采集步骤改为：artificialanalysis → lmarena → llmregistry（补充）

### Step 8: 清空旧数据

* 在 DB 中执行 TRUNCATE evaluations（DELETE FROM evaluations）

* 或者在 init\_schema 中添加版本号检测，自动清空旧结构数据

### Step 9: 添加测试

* 测试 AA parser 的字段映射

* 测试 LMArena parser 的 Elo 映射

* 测试 llmregistry 的 sourceId 过滤

### Step 10: 更新 validator.py

* 更新 validate\_evaluation 函数，匹配新字段

## 风险与注意事项

1. **AA API Key**：需要在 GitHub Secrets 中添加 `AA_API_KEY`，免费 key 限制 1K req/天
2. **模型 ID 映射**：AA 用 `gpt-5.5` 格式，LMArena 用 `gpt-5-5` 格式，我们用 `openai/gpt-5.5` 格式，需要做映射
3. **数据覆盖**：AA 覆盖 \~300 模型，LMArena 覆盖 \~200 模型，llm-registry 覆盖 1584 模型（但只有部分是第三方数据）
4. **旧字段兼容**：删除的字段在已有数据库中仍存在（SQLite 不支持 DROP COLUMN），迁移时保留旧列但不再写入
5. **性能数据**：AA 是唯一提供 tokens/sec 和 TTFT 的第三方，这是之前 evaluations 表一直为 NULL 的字段

