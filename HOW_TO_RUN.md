# AIX Future ModelInfos

AI 模型元数据自动采集系统。从第三方独立评测源、官方文档和 API 采集模型信息、定价和评测数据，存入 TursoDB，通过 GitHub Actions 定时运行。

## 数据概览

| 数据表 | 说明 | 数据来源 |
|--------|------|----------|
| **models** | 模型基本信息、能力标签、上下文长度 | OpenRouter, OpenAI, Anthropic |
| **pricing** | 价格（支持多渠道、多区域） | OpenRouter, OpenAI, Anthropic |
| **evaluations** | 第三方独立评测分数、性能数据 | Artificial Analysis, LMArena, LLM Registry |

## 评测数据详解

所有评测数据均来自**第三方独立评测**，不包含厂商自报分数。

### 数据源

| 数据源 | 采集方式 | 覆盖 | 说明 |
|--------|----------|------|------|
| **Artificial Analysis** | API（需 API Key） | 516 模型 | 独立基准测试，被 OpenAI/Google/Anthropic/NVIDIA 引用 |
| **LMArena (Chatbot Arena)** | GitHub JSON（免费） | 282 模型 | 真人匿名对战投票，500万+ 票 |
| **LLM Registry** | API（免费） | 45 模型 | 聚合数据，仅保留第三方来源分数 |

### 评测字段说明

#### Artificial Analysis 独立评测

| 字段 | 说明 | 范围 |
|------|------|------|
| `aa_intelligence_index` | 综合智能评分（核心指标） | 0-100 |
| `aa_coding_index` | 代码能力评分 | 0-100 |
| `aa_math_index` | 数学能力评分 | 0-100 |
| `mmlu_pro` | MMLU-Pro 知识评测 | 0-1 |
| `gpqa` | GPQA Diamond 科学推理 | 0-1 |
| `hle` | Humanity's Last Exam | 0-1 |
| `aime` | 竞赛数学 | 0-1 |
| `livecodebench` | 代码生成 | 0-1 |
| `scicode` | 科学计算代码 | 0-1 |
| `ifbench` | 指令遵循 | 0-1 |
| `aa_lcr` | 长上下文推理 | 0-1 |
| `tokens_per_second` | 输出速度（tokens/s） | 正整数 |
| `ttft_ms` | 首 token 延迟（ms） | 正整数 |

#### LMArena 真人对战

| 字段 | 说明 | 范围 |
|------|------|------|
| `lmarena_elo` | 综合对战 Elo 评分 | 500-2000 |
| `lmarena_coding` | 代码对战 Elo | 500-2000 |
| `lmarena_math` | 数学对战 Elo | 500-2000 |
| `lmarena_hard` | 难题对战 Elo | 500-2000 |

### 如何使用评测数据

```sql
-- 查看某模型的所有评测数据
SELECT * FROM evaluations WHERE model_id = 'openai/gpt-4o-2024-08-06';

-- 按 Intelligence Index 排名 Top 20
SELECT model_id, aa_intelligence_index, tokens_per_second, ttft_ms
FROM evaluations
WHERE aa_intelligence_index IS NOT NULL
ORDER BY aa_intelligence_index DESC
LIMIT 20;

-- 按 LMArena Elo 排名 Top 20
SELECT model_id, lmarena_elo, lmarena_coding, lmarena_math
FROM evaluations
WHERE lmarena_elo IS NOT NULL
ORDER BY lmarena_elo DESC
LIMIT 20;

-- 性价比分析：Intelligence Index / 每百万 token 混合价格
SELECT e.model_id, e.aa_intelligence_index,
       p.blended_price_per_1m,
       ROUND(e.aa_intelligence_index / NULLIF(p.blended_price_per_1m, 0), 2) AS value_ratio
FROM evaluations e
JOIN pricing p ON e.model_id = p.model_id
WHERE e.aa_intelligence_index IS NOT NULL
ORDER BY value_ratio DESC
LIMIT 20;

-- 代码能力对比
SELECT model_id, aa_coding_index, lmarena_coding, livecodebench
FROM evaluations
WHERE aa_coding_index IS NOT NULL
ORDER BY aa_coding_index DESC
LIMIT 20;
```

## 快速开始

### 环境要求

- Python 3.12+
- TursoDB 账号（或本地 SQLite 测试）

### 安装

```bash
cd collector
pip install -e ".[dev]"
```

### 运行

```bash
# 干跑（不写数据库，查看采集结果）
python -m modelinfo.cli collect --table evaluations --source lmarena --dry-run

# 采集所有数据
python -m modelinfo.cli collect --table all --source all

# 只采集评测数据
python -m modelinfo.cli collect --table evaluations --source lmarena
python -m modelinfo.cli collect --table evaluations --source artificialanalysis
python -m modelinfo.cli collect --table evaluations --source llmregistry

# 只采集价格
python -m modelinfo.cli collect --table pricing --source openrouter
```

### 环境变量

| 变量 | 必需 | 说明 |
|------|------|------|
| `TURSO_DB_URL` | 正式运行时必需 | TursoDB 连接 URL（本地测试可省略） |
| `TURSO_AUTH_TOKEN` | 正式运行时必需 | TursoDB 认证 Token |
| `AA_API_KEY` | AA 评测采集时必需 | Artificial Analysis API Key（免费获取） |

本地测试时省略 `TURSO_DB_URL` 和 `TURSO_AUTH_TOKEN`，数据将写入本地 `local.db` 文件。

### 获取 Artificial Analysis API Key

1. 访问 [artificialanalysis.ai](https://artificialanalysis.ai/)
2. 注册账号
3. 在 Insights 页面获取 API Key（免费，1K 请求/天）

## 自动化运行

GitHub Actions 定时任务：

| Workflow | 运行时间 | 做什么 |
|----------|---------|--------|
| Daily Price Check | 每天 UTC 8:00 | 检查价格变动 |
| Weekly Full Collect | 每周一 UTC 2:00 | 全量更新所有数据（含评测） |

### 配置 GitHub Secrets

1. 打开 GitHub 仓库 → Settings → Secrets and variables → Actions
2. 添加以下 Secrets：
   - `TURSO_DB_URL` = `libsql://你的数据库名.turso.io`
   - `TURSO_AUTH_TOKEN` = `你的 TursoDB token`
   - `AA_API_KEY` = `你的 Artificial Analysis API Key`
3. 手动触发测试：Actions → Weekly Full Collect → Run workflow

## 项目结构

```
collector/
├── src/modelinfo/
│   ├── models.py         # Pydantic 数据模型
│   ├── db.py             # TursoDB 客户端 + Schema
│   ├── fetcher.py        # HTTP 客户端（重试 + 自定义 headers）
│   ├── normalizer.py     # 字段标准化
│   ├── differ.py         # 变更检测
│   ├── writer.py         # DB 写入 + 验证
│   ├── validator.py      # 数据校验
│   ├── change_log.py     # 变更日志 + 错误追踪
│   ├── cli.py            # Typer CLI
│   └── parsers/
│       ├── base.py                # 抽象 Parser 接口
│       ├── openrouter.py          # OpenRouter API
│       ├── openai.py              # OpenAI 官方文档
│       ├── anthropic.py           # Anthropic 官方文档
│       ├── artificialanalysis.py  # Artificial Analysis 独立评测
│       ├── lmarena.py             # LMArena 真人对战
│       └── llmregistry.py         # LLM Registry（仅第三方分数）
└── tests/
    ├── fixtures/         # 录制的 HTML/JSON 测试数据
    └── parsers/          # Parser 单元测试
```

## 数据库表结构

### models 表

| 字段 | 类型 | 说明 |
|------|------|------|
| model_id | TEXT PK | 唯一标识（格式：`provider/model-name`） |
| model_name | TEXT | 模型名称 |
| provider | TEXT | 厂商 |
| context_length | INTEGER | 最大上下文长度 |
| max_output_tokens | INTEGER | 最大输出长度 |
| capabilities | TEXT(JSON) | 能力标签 |
| status | TEXT | 状态（active/beta/deprecated） |

### pricing 表

| 字段 | 类型 | 说明 |
|------|------|------|
| pricing_id | TEXT PK | 唯一标识 |
| model_id | TEXT FK | 关联模型 |
| input_price_per_1m | REAL | 输入价格（USD/百万 token） |
| output_price_per_1m | REAL | 输出价格（USD/百万 token） |
| cache_read_price_per_1m | REAL | 缓存读价格 |
| cache_write_price_per_1m | REAL | 缓存写价格 |

### evaluations 表

| 字段 | 类型 | 来源 | 说明 |
|------|------|------|------|
| eval_id | TEXT PK | - | 唯一标识（格式：`model_id/source/date`） |
| model_id | TEXT FK | - | 关联模型 |
| eval_date | TEXT | - | 评测日期 |
| source | TEXT | - | 数据来源 URL |
| aa_intelligence_index | REAL | AA | 综合智能评分 |
| aa_coding_index | REAL | AA | 代码能力 |
| aa_math_index | REAL | AA | 数学能力 |
| mmlu_pro | REAL | AA | MMLU-Pro |
| gpqa | REAL | AA | GPQA Diamond |
| hle | REAL | AA | Humanity's Last Exam |
| aime | REAL | AA | 竞赛数学 |
| livecodebench | REAL | AA | 代码生成 |
| scicode | REAL | AA | 科学计算代码 |
| ifbench | REAL | AA | 指令遵循 |
| aa_lcr | REAL | AA | 长上下文推理 |
| lmarena_elo | REAL | LMArena | 综合对战 Elo |
| lmarena_coding | REAL | LMArena | 代码对战 Elo |
| lmarena_math | REAL | LMArena | 数学对战 Elo |
| lmarena_hard | REAL | LMArena | 难题对战 Elo |
| tokens_per_second | INTEGER | AA | 输出速度 |
| ttft_ms | INTEGER | AA | 首 token 延迟 |
| other_benchmarks | TEXT(JSON) | - | 其他 benchmark 分数 |

## 日志

- 变更日志：`logs/change_log.md`
- 错误日志：`logs/errors.jsonl`
