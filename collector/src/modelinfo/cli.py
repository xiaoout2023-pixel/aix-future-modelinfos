import asyncio
import os
import typer
import structlog
from modelinfo.fetcher import Fetcher
from modelinfo.db import Database, init_schema
from modelinfo.writer import Writer
from modelinfo.change_log import ChangeLogManager, ErrorTracker
from modelinfo.parsers.openrouter import OpenRouterParser
from modelinfo.parsers.openai import OpenAIParser
from modelinfo.parsers.anthropic import AnthropicParser

app = typer.Typer()
logger = structlog.get_logger()


@app.callback()
def main():
    """Model metadata collector - scrapes and normalizes AI model metadata."""


def get_db():
    url = os.environ.get("TURSO_DB_URL", "file:local.db")
    token = os.environ.get("TURSO_AUTH_TOKEN", "")
    return Database(url=url, auth_token=token)


@app.command(name="collect")
def collect(
    table: str = typer.Option("all", "--table", "-t", help="models, pricing, evaluations, or all"),
    source: str = typer.Option("all", "--source", "-s", help="openrouter, openai, anthropic, or all"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Fetch and parse but do not write to DB"),
):
    """Collect model metadata from configured sources."""
    db = get_db()
    init_schema(db)
    writer = Writer(db)
    error_tracker = ErrorTracker()
    changelog = ChangeLogManager()

    sources = _get_sources(source)

    async def _run():
        async with Fetcher() as fetcher:
            for src_cls in sources:
                parser = src_cls(fetcher)
                try:
                    if table in ("models", "all"):
                        models = await parser.fetch_models()
                        if not dry_run:
                            result = writer.write_models(models)
                            typer.echo(f"{parser.source_name}: {result['upserted']} models upserted, {result['errors']} errors")
                        else:
                            typer.echo(f"{parser.source_name}: {len(models)} models fetched (dry-run)")

                    if table in ("pricing", "all"):
                        pricings = await parser.fetch_pricing()
                        if not dry_run:
                            result = writer.write_pricing(pricings)
                            typer.echo(f"{parser.source_name}: {result['upserted']} pricing records upserted, {result['errors']} errors")
                        else:
                            typer.echo(f"{parser.source_name}: {len(pricings)} pricing records fetched (dry-run)")

                except Exception as e:
                    logger.error("parser_failed", source=parser.source_name, error=str(e))
                    error_tracker.log_error(parser.source_name, "", str(e))
                    if error_tracker.should_create_issue(parser.source_name):
                        typer.echo(f"WARNING: {parser.source_name} has failed 3+ times in the last 7 days. Consider creating a GitHub Issue.", err=True)

    asyncio.run(_run())


def _get_sources(source: str) -> list:
    registry = {
        "openrouter": OpenRouterParser,
        "openai": OpenAIParser,
        "anthropic": AnthropicParser,
    }
    if source == "all":
        return list(registry.values())
    if source in registry:
        return [registry[source]]
    typer.echo(f"Unknown source: {source}. Available: {list(registry.keys())}", err=True)
    raise typer.Exit(1)


if __name__ == "__main__":
    app()
