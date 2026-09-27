from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_chat_returns_answer_and_citation() -> None:
    response = client.post("/api/v1/chat", json={"message": "termination notice"})

    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "termination notice"
    assert body["answer"]
    assert body["citations"][0]["file_number"] == "178204"


def test_chat_rejects_blank_query() -> None:
    response = client.post("/api/v1/chat", json={"message": " "})

    assert response.status_code == 422
