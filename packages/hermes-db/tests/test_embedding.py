import json

import pytest
import httpx
import respx

from hermes_db_mcp.config import settings
from hermes_db_mcp.services.embedding import build_embedding_payload, generate_embedding


@pytest.fixture
def mock_http():
    return httpx.AsyncClient(base_url="http://test-embedding:8080")


def test_payload_omits_dimensions_when_not_configured(monkeypatch):
    monkeypatch.setattr(settings, "embedding_dimension", 0)

    assert build_embedding_payload("test text") == {
        "model": settings.embedding_model,
        "input": "test text",
    }


def test_payload_includes_positive_dimensions(monkeypatch):
    monkeypatch.setattr(settings, "embedding_dimension", 1024)

    assert build_embedding_payload("test text") == {
        "model": settings.embedding_model,
        "input": "test text",
        "dimensions": 1024,
    }


@pytest.mark.asyncio
class TestEmbedding:
    @respx.mock
    async def test_success(self, mock_http, monkeypatch):
        monkeypatch.setattr(settings, "embedding_dimension", 0)
        fake_vector = [0.1] * 1024
        route = respx.post("http://test-embedding:8080/embeddings").respond(
            200, json={"data": [{"embedding": fake_vector}]}
        )
        result = await generate_embedding(mock_http, "test text")
        assert result == fake_vector
        assert json.loads(route.calls.last.request.content) == {
            "model": "BAAI/bge-m3",
            "input": "test text",
        }

    @respx.mock
    async def test_timeout_returns_none(self, mock_http):
        respx.post("http://test-embedding:8080/embeddings").mock(
            side_effect=httpx.ReadTimeout("timeout")
        )
        result = await generate_embedding(mock_http, "test text")
        assert result is None

    @respx.mock
    async def test_server_error_returns_none(self, mock_http):
        respx.post("http://test-embedding:8080/embeddings").respond(500)
        result = await generate_embedding(mock_http, "test text")
        assert result is None

    @respx.mock
    async def test_malformed_response_returns_none(self, mock_http):
        respx.post("http://test-embedding:8080/embeddings").respond(
            200, json={"unexpected": "format"}
        )
        result = await generate_embedding(mock_http, "test text")
        assert result is None

    @respx.mock
    async def test_invalid_json_returns_none(self, mock_http):
        respx.post("http://test-embedding:8080/embeddings").respond(
            200, text="not json"
        )
        result = await generate_embedding(mock_http, "test text")
        assert result is None
