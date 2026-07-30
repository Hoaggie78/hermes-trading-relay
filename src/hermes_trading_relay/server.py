from __future__ import annotations

import argparse
import time
import uuid
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException

from .config import RelayConfig
from .hermes_client import HermesClient
from .openai_compat import ChatCompletionRequest, ModelsResponse


def create_app(config: RelayConfig | None = None, client: HermesClient | None = None) -> FastAPI:
    relay_config = config or RelayConfig.from_env()
    hermes = client or HermesClient(relay_config)
    app = FastAPI(
        title="Hermes Trading Relay",
        description="OpenAI-compatible local relay from TradingAgents to Hermes OAuth-authenticated Codex.",
        version="0.1.0",
    )

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {
            "ok": True,
            "service": "hermes-trading-relay",
            "hermes_command": " ".join(relay_config.hermes_command),
            "profile": relay_config.hermes_profile,
        }

    @app.get("/v1/models")
    def models() -> ModelsResponse:
        return ModelsResponse()

    @app.post("/v1/chat/completions")
    def chat_completions(request: ChatCompletionRequest) -> dict[str, Any]:
        try:
            content = hermes.complete(request)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:  # noqa: BLE001 - surface local relay failures as HTTP errors
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        now = int(time.time())
        return {
            "id": f"chatcmpl-hermes-{uuid.uuid4().hex}",
            "object": "chat.completion",
            "created": now,
            "model": request.model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            },
        }

    return app


app = create_app()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Hermes Trading Relay")
    parser.add_argument("--host", default=None, help="Bind host, default from HERMES_RELAY_HOST")
    parser.add_argument("--port", type=int, default=None, help="Bind port, default from HERMES_RELAY_PORT")
    args = parser.parse_args()

    config = RelayConfig.from_env()
    host = args.host or config.host
    port = args.port or config.port
    uvicorn.run("hermes_trading_relay.server:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
