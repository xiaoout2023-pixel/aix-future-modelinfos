# AI 模型元数据自动采集系统 — 设计文档

## 概述

构建一个自动化元数据采集系统，从官方文档、中转平台、第三方评测机构获取 AI 模型的事实数据。数据写入 TursoDB，为 AI 模型成本计算顾问产品提供准确、可追溯、可比较的数据基础。

## 设计目标

- **准确**：以官方来源为主，记录 source URL，可追溯
- **可比较**：统一单位、统一字段、统一枚举值
- **可更新**：自动检测价格变动，diff 后增量更新
- **能赚钱**：数据直接支撑成本计算顾问，帮客户省钱

## Schema 设计

三张表分离事实和评测：

### models 表

| 字段 | 类型 | 说明 |
|---|---|---|
| model_id | string | 唯一标识，如 "openai/gpt-5" |
| model_name | string | 显示名称 |
| provider | string | 厂商 |
| provider_type | enum | open_source / closed |
| release_date | date | 发布日期 |
| status | enum | active / beta / deprecated / coming_soon |
| aliases | string[] | API 模型名别名，如 ["gpt-4o-2024-08-06"] |
| capabilities.text | bool | 文本生成 |
| capabilities.code | bool | 代码生成 |
| capabilities.reasoning | bool | 推理能力 |
| capabilities.vision | bool | 图像理解 |
| capabilities.image_gen | bool | 图像生成 |
| capabilities.audio | bool | 音频理解 |
| capabilities.audio_gen | bool | 音频生成 |
| capabilities.video | bool | 视频理解 |
| capabilities.tool_use | bool | 工具调用 |
| capabilities.structured_output | bool | JSON/结构化输出 |
| capabilities.streaming | bool | 流式 |
| capabilities.batch | bool | 批处理 |
| capabilities.fine_tuning | bool | 微调支持 |
| capabilities.embedding | bool | 向量能力 |
| context_length | int | 最大上下文长度 |
| max_output_tokens | int | 最大输出 |
| regions | string[] | 支持区域 |
| private_deployment | bool | 是否支持私有部署 |
| openai_compatible | bool | OpenAI API 兼容 |
| urls.official | string | 官方页面 |
| urls.docs | string | API 文档 |
| urls.pricing | string | 定价页 |
| tags | string[] | 标签 |
| last_updated | datetime | 最后更新时间 |

### pricing 表

| 字段 | 类型 | 说明 |
|---|---|---|
| pricing_id | string | 唯一标识 |
| model_id | string | 关联 models |
| channel | enum | official / marketplace / reseller |
| market_name | string | 渠道名，如 "openrouter" |
| region | string | 区域 |
| valid_from | date | 价格生效日期 |
| currency | enum | 货币 |
| input_price_per_1m | float | 输入价格（USD/1M tokens） |
| output_price_per_1m | float | 输出价格 |
| cache_read_price_per_1m | float | 缓存读价格 |
| cache_write_price_per_1m | float | 缓存写价格 |
| reasoning_tokens_charged | bool | 推理 token 是否额外计费 |
| reasoning_overhead_ratio | float | 推理 token / 输出 token 倍数 |
| price_per_request | float | 单次调用 |
| price_per_image | float | 图像生成 |
| price_per_audio_min | float | 音频 |
| tiers | json | 阶梯价格 |
| volume_discount | json | 量大议价 |
| reserved_discount_pct | float | 预付折扣 |
| free_tier_tokens | int | 月免费额度 |
| min_billable_tokens | int | 最小计费单位 |
| rounding_unit | int | 计费取整单位 |
| has_spot | bool | 是否有竞价实例 |
| source | string | 数据来源 URL |
| last_verified | datetime | 最后验证时间 |

### evaluations 表

| 字段 | 类型 | 说明 |
|---|---|---|
| eval_id | string | 唯一标识 |
| model_id | string | 关联 models |
| eval_date | date | 评测日期 |
| source | string | 评测来源，如 "artificial_analysis" |
| mmlu | float | MMLU 分数 |
| gsm8k | float | GSM8K 分数 |
| humaneval | float | HumanEval 分数 |
| other_benchmarks | json | 其他 benchmark |
| tokens_per_second | int | 生成速度 |
| avg_latency_ms | int | 平均延迟 |
| p95_latency_ms | int | P95 延迟 |
| reasoning_level | enum | low / medium / high |
| overall_score | float | 综合分 |
| cost_efficiency_score | float | 性价比分 |

## 数据源策略

### models 表数据源

| 来源 | 方式 | 覆盖 | 可信度 |
|---|---|---|---|
| 厂商 API/docs 页 | 网页抓取 | OpenAI, Anthropic, Google, DeepSeek 等 ~20 家 | 官方 |
| OpenRouter API | API 调用 | ~300+ 模型基本信息 | 中间商但规范 |
| GitHub 开源模型页 | 网页抓取 | Llama, Qwen, Mistral 等 | 官方 |

### pricing 表数据源

| 来源 | 方式 | 说明 |
|---|---|---|
| 官方定价页 | 网页抓取 | 第一手价格，权威 |
| OpenRouter API | API fetch | 实时价格，跨厂商标准化 |
| 关键模型人工抽查 | 手动校验 | 保证准确性 |

### evaluations 表数据源

| 来源 | 方式 | 覆盖 |
|---|---|---|
| Artificial Analysis | API/抓取 | 延迟、质量、价格对比 |
| LiveBench | 抓取 | 综合 benchmark |
| Chatbot Arena (LMSYS) | 抓取 | Elo 排名 |
| MMLU/GSM8K/HumanEval | 抓取 | 学术 benchmark |

## 系统架构

```
Sources                    Collector Engine                  Storage
───────                    ────────────────                  ───────
厂商官网 ────┐
OpenRouter ──┤
评测网站 ────┼──► Fetcher ──► Parser ──► Normalizer ──► Differ ──► TursoDB
GitHub ──────┘        │                               │
                       │                               ▼
                       └── Logs & Errors ──► change_log 表
```

### 流水线

1. **Fetcher**：多来源并发拉取（网页用 HTTP + parser，API 用 SDK）
2. **Parser**：每个来源独立解析器，提取结构化字段
3. **Normalizer**：统一格式（价格→1M tokens、日期→YYYY-MM-DD、枚举→小写）
4. **Differ**：对比库里已有数据，只标记变化的记录
5. **Writer**：upsert 到 TursoDB，写入 change_log
6. **Validator**：抽查关键模型数据合理性

### 运行模式

**GitHub Actions 定时调度：**

- **价格检查**：每日 UTC 8:00 运行，检查所有模型价格变动
- **全量采集**：每周一 UTC 2:00 运行，全量更新 models + pricing + evaluations
- **手动触发**：`workflow_dispatch`，可指定来源或单个模型

TursoDB 连接信息通过 GitHub Secrets 注入。采集结果和变更日志 commit 回仓库，保持可追溯。

```
GitHub Actions (cron)               Collector (Python CLI)            TursoDB
───────────────────                ──────────────────────           ───────
schedule: daily  ──► checkout repo ──► fetch + parse + diff ──► upsert
                         │                    │
                         ▼                    ▼
                    git log / blame     change_log.md (commit back)

## Tokenizer 差异处理

GPT 和 Claude 等 token 计数方式不同，同一段话计数不同。

**处理**：models 表不额外标注，但在成本顾问展示层告知用户：
> "价格统一按各自厂商 tokenizer 计数。跨厂商比较时，实际消耗可能因 tokenizer 差异浮动 ±20%。"

## 设计决策记录

| 决策 | 结论 | 原因 |
|---|---|---|
| 三表 vs 单表 | 三表 | 价格变动频繁，独立管理不污染模型主表 |
| 事实 vs 评测分离 | 分离 | 来源不同、更新频率不同、可追溯性不同 |
| 快照版本 | model_id 聚合，aliases 记录 | 用户关注模型家族，不关心日期后缀 |
| 字段覆盖 | 只存能抓到的 | 抓不到的不硬填，允许 null |
| 推理 token | 单独标注 | 隐性成本可能 3-10x，不做不行 |
| 折扣存储 | json 字段 | 灵活，避免阶梯数不定导致表膨胀 |
