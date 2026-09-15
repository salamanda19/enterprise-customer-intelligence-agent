"""HTTP API smoke tests (no live server process; TestClient)."""

from __future__ import annotations

import pytest

from ecia.data.generate import DEFAULT_DB_PATH


@pytest.fixture(scope="module")
def require_db():
    if not DEFAULT_DB_PATH.exists():
        pytest.skip("Frozen DB missing; run: python scripts/rebuild_db.py")


@pytest.fixture(scope="module")
def client(require_db):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from api.app import create_app

    return TestClient(create_app())


def test_health(client) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["db_present"] is True


def test_ask_q5_downgrade(client) -> None:
    r = client.post("/ask", json={"question_id": "Q5"})
    assert r.status_code == 200
    body = r.json()
    assert body["response_mode"] == "downgrade"
    assert body["figures"]
    assert "meta" in body
    assert "latency_ms" in body["meta"]
    assert body["meta"]["prompt_version"]
    assert body["meta"]["token_usage"]["total"] == 0


def test_ask_q7_refuse(client) -> None:
    r = client.post("/ask", json={"question": "活動 A 是否造成營收增加？"})
    assert r.status_code == 200
    body = r.json()
    assert body["response_mode"] == "refuse"
    assert body["reason_codes"] == ["CAUSAL_UNSUPPORTED"]


def test_ask_requires_input(client) -> None:
    r = client.post("/ask", json={})
    assert r.status_code == 400
