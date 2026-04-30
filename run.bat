@echo off
chcp 65001 >nul
cd /d "%~dp0collector"

echo ========================================
echo   ModelInfo Collector
echo ========================================
echo.

if "%~1"=="" (
    echo Usage:
    echo   run.bat setup      首次安装依赖
    echo   run.bat test       运行测试
    echo   run.bat dryrun     干跑采集（只看不写，数据不进库）
    echo   run.bat collect    正式采集，写入 TursoDB
    echo   run.bat pricing    只采集价格
    echo   run.bat help       查看所有命令
    echo.
    echo 首次使用请先: run.bat setup
    goto :end
)

if "%~1"=="setup" (
    echo [1/2] 安装 Python 依赖...
    pip install -e ".[dev]"
    echo.
    echo [2/2] 验证安装...
    python -m pytest tests/ -q
    echo.
    echo 安装完成！下一步试试: run.bat dryrun
    goto :end
)

if "%~1"=="test" (
    python -m pytest tests/ -v
    goto :end
)

if "%~1"=="dryrun" (
    echo 干跑模式：只抓取并显示数据，不写入数据库...
    echo 数据来源: OpenRouter（300+ 模型）
    echo.
    python -m modelinfo.cli collect --source openrouter --dry-run
    goto :end
)

if "%~1"=="collect" (
    echo 正式采集：抓取全部来源数据，写入 TursoDB...
    echo 需要设置环境变量 TURSO_DB_URL 和 TURSO_AUTH_TOKEN
    echo.
    python -m modelinfo.cli collect --table all
    goto :end
)

if "%~1"=="pricing" (
    echo 只采集价格数据...
    python -m modelinfo.cli collect pricing
    goto :end
)

if "%~1"=="help" (
    python -m modelinfo.cli --help
    echo.
    python -m modelinfo.cli collect --help
    goto :end
)

echo 未知命令: %~1
echo 请用 run.bat 查看可用命令

:end
