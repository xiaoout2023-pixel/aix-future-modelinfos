from tests.conftest import load_fixture, load_fixture_json


def test_load_fixtures():
    html = load_fixture("openai_models_page.html")
    assert "gpt-4o" in html
    data = load_fixture_json("openrouter_models.json")
    assert len(data["data"]) == 3


import pytest
import httpx
from modelinfo.fetcher import Fetcher


@pytest.mark.asyncio
async def test_fetch_json_success(httpx_mock):
    httpx_mock.add_response(url="https://api.example.com/models", json={"data": [{"id": "test"}]})
    async with Fetcher() as fetcher:
        result = await fetcher.fetch_json("https://api.example.com/models")
    assert result == {"data": [{"id": "test"}]}


@pytest.mark.asyncio
async def test_fetch_html_success(httpx_mock):
    httpx_mock.add_response(url="https://example.com/models", text="<html><body><p>Models</p></body></html>")
    async with Fetcher() as fetcher:
        soup = await fetcher.fetch_html("https://example.com/models")
    assert soup.find("p") is not None
    assert soup.find("p").text == "Models"


@pytest.mark.asyncio
async def test_fetch_retry_on_server_error(httpx_mock):
    httpx_mock.add_response(status_code=500)
    httpx_mock.add_response(status_code=500)
    httpx_mock.add_response(json={"data": "ok"})
    async with Fetcher(max_retries=3) as fetcher:
        result = await fetcher.fetch_json("https://api.example.com/models")
    assert result == {"data": "ok"}
    assert len(httpx_mock.get_requests()) == 3


@pytest.mark.asyncio
async def test_fetch_exhausts_retries(httpx_mock):
    for _ in range(3):
        httpx_mock.add_response(status_code=500)
    async with Fetcher(max_retries=3) as fetcher:
        with pytest.raises(httpx.HTTPStatusError):
            await fetcher.fetch_json("https://api.example.com/models")
