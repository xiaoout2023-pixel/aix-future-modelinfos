# ModelInfo Collector 使用说明

## 环境要求

- Python 3.12 或以上
- 命令行终端（CMD / PowerShell / Git Bash 都可以）

## 三种运行方式

### 方式一：用 run.bat（最简单，Windows）

打开项目目录，双击或在命令行运行：

```cmd
run.bat setup       # 首次：安装依赖 + 跑测试验证
run.bat dryrun      # 干跑：只看抓取结果，不写数据库
run.bat collect     # 正式采集，写入 TursoDB
run.bat pricing     # 只采集价格
run.bat test        # 跑所有测试
```

### 方式二：命令行（Windows / Mac / Linux 通用）

```bash
cd collector
pip install -e ".[dev]"

# 干跑
python -m modelinfo.cli collect --source openrouter --dry-run

# 只抓价格
python -m modelinfo.cli collect pricing --dry-run

# 正式采集（需要设置数据库环境变量）
python -m modelinfo.cli collect all

# 从特定来源采集
python -m modelinfo.cli collect all --source openai
```

### 方式三：GitHub Actions 自动运行（推荐）

代码已包含两个定时 workflow，无需手动操作：

| workflow | 运行时间 | 做什么 |
|----------|---------|--------|
| Daily Price Check | 每天 UTC 8:00（北京时间 16:00） | 检查价格变动 |
| Weekly Full Collect | 每周一 UTC 2:00 | 全量更新所有数据 |

**首次使用需要配置 Secrets：**

1. 打开你的 GitHub 仓库 → Settings → Secrets and variables → Actions
2. 添加两个 Secret：
   - `TURSO_DB_URL` = `libsql://你的数据库名.turso.io`
   - `TURSO_AUTH_TOKEN` = `你的 TursoDB token`
3. 手动触发一次测试：Actions → Weekly Full Collect → Run workflow

---

## 数据来源

| 来源 | 类型 | 覆盖 |
|------|------|------|
| OpenRouter API | JSON | 300+ 模型基本信息 + 价格 |
| OpenAI 官方文档 | HTML | GPT 系列官方定价 |
| Anthropic 官方文档 | HTML | Claude 系列官方定价 + thinking token |

---

## 数据库表结构

三张表：

- **models** — 模型基本信息、能力标签、上下文长度
- **pricing** — 价格（支持 official / marketplace / reseller 多渠道）
- **evaluations** — benchmark 分数、延迟数据

---

## 采集结果

干跑结果直接显示在命令行。正式采集结果写入 TursoDB。

变动日志：`logs/change_log.md`
错误日志：`logs/errors.jsonl`
