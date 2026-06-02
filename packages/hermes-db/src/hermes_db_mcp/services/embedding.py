import httpx

from hermes_db_mcp.config import settings


def build_embedding_payload(text: str) -> dict:
    payload = {
        "model": settings.embedding_model,
        "input": text,
    }
    if settings.embedding_dimension > 0:
        payload["dimensions"] = settings.embedding_dimension
    return payload


async def generate_embedding(http: httpx.AsyncClient, text: str) -> list[float] | None:
    try:
        resp = await http.post(
            "/embeddings",
            json=build_embedding_payload(text),
            headers={"Authorization": f"Bearer {settings.embedding_api_key}"},
            timeout=3.0,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["data"][0]["embedding"]
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError):
        return None
