import json
from pathlib import Path
import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def load_fixture_json(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.fixture
def openrouter_response():
    return load_fixture_json("openrouter_models.json")


@pytest.fixture
def openai_models_html():
    return load_fixture("openai_models_page.html")


@pytest.fixture
def openai_pricing_html():
    return load_fixture("openai_pricing_page.html")


@pytest.fixture
def anthropic_models_html():
    return load_fixture("anthropic_models_page.html")


@pytest.fixture
def anthropic_pricing_html():
    return load_fixture("anthropic_pricing_page.html")
