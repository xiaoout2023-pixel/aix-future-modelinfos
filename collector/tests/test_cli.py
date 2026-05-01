import os

from typer.testing import CliRunner
from modelinfo.cli import app
from tests.conftest import load_fixture_json

runner = CliRunner()


def test_collect_models_dry_run(httpx_mock, openrouter_response, tmp_path):
    """Collect models from openrouter in dry-run mode should succeed."""
    httpx_mock.add_response(
        url="https://openrouter.ai/api/v1/models",
        json=openrouter_response,
    )
    os.environ["TURSO_DB_URL"] = f"file:{tmp_path / 'test.db'}"

    result = runner.invoke(app, ["collect", "--table", "models", "--source", "openrouter", "--dry-run"])

    assert result.exit_code == 0
    assert "openrouter:" in result.stdout
    assert "models fetched (dry-run)" in result.stdout


def test_collect_pricing_dry_run(httpx_mock, openrouter_response, tmp_path):
    """Collect pricing from all sources in dry-run mode should succeed."""
    httpx_mock.add_response(
        url="https://openrouter.ai/api/v1/models",
        json=openrouter_response,
    )
    httpx_mock.add_response(
        url="https://platform.openai.com/docs/pricing",
        text="<html><body><p>Pricing page</p></body></html>",
    )
    httpx_mock.add_response(
        url="https://platform.claude.com/docs/en/about-claude/models",
        text="<html><body><p>Models page</p></body></html>",
    )
    os.environ["TURSO_DB_URL"] = f"file:{tmp_path / 'test.db'}"

    result = runner.invoke(app, ["collect", "--table", "pricing", "--dry-run"])

    assert result.exit_code == 0
    assert "pricing records fetched (dry-run)" in result.stdout


def test_collect_unknown_source():
    """Unknown source should exit with code 1."""
    result = runner.invoke(app, ["collect", "--table", "models", "--source", "nonexistent"])
    assert result.exit_code == 1
    assert "Unknown source" in result.output


def test_help_shows_commands():
    """--help should list the collect command."""
    result = runner.invoke(app, ["--help"])
    assert "collect" in result.stdout
