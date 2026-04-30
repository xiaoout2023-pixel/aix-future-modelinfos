from tests.conftest import load_fixture, load_fixture_json


def test_load_fixtures():
    html = load_fixture("openai_models_page.html")
    assert "gpt-4o" in html
    data = load_fixture_json("openrouter_models.json")
    assert len(data["data"]) == 3
