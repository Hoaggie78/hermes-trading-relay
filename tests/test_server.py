from fastapi.testclient import TestClient

from hermes_trading_relay.config import RelayConfig
from hermes_trading_relay.server import create_app


class FakeHermesClient:
    def __init__(self, response="ok"):
        self.response = response
        self.requests = []

    def complete(self, request):
        self.requests.append(request)
        return self.response


def _config():
    return RelayConfig(
        hermes_command=["hermes"],
        hermes_profile="trading",
        hermes_model=None,
        hermes_provider="openai-codex",
        host="127.0.0.1",
        port=8765,
        request_timeout_seconds=300,
        system_prefix="prefix",
    )


def test_health():
    app = create_app(_config(), FakeHermesClient())
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert response.json()["profile"] == "trading"


def test_models_endpoint():
    app = create_app(_config(), FakeHermesClient())
    client = TestClient(app)

    response = client.get("/v1/models")

    assert response.status_code == 200
    assert response.json()["data"][0]["id"] == "hermes-codex"


def test_chat_completion_shape():
    fake = FakeHermesClient("research-only answer")
    app = create_app(_config(), fake)
    client = TestClient(app)

    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "hermes-codex",
            "messages": [{"role": "user", "content": "Analyze SPY"}],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["object"] == "chat.completion"
    assert payload["choices"][0]["message"]["content"] == "research-only answer"
    assert fake.requests[0].messages[0].content == "Analyze SPY"
