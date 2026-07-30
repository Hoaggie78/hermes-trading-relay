from __future__ import annotations

import argparse
import json
import time
import uuid
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException

from .config import RelayConfig
from .hermes_client import HermesClient
from .openai_compat import ChatCompletionRequest, ModelsResponse


def _extract_json_object(text: str) -> dict[str, Any] | None:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _normalise_tool_calls(parsed: dict[str, Any]) -> list[dict[str, Any]]:
    calls = parsed.get("tool_calls")
    if not isinstance(calls, list):
        return []
    normalised: list[dict[str, Any]] = []
    for call in calls:
        if not isinstance(call, dict):
            continue
        function = call.get("function") if isinstance(call.get("function"), dict) else None
        name = call.get("name") or (function or {}).get("name")
        arguments = call.get("arguments") if "arguments" in call else (function or {}).get("arguments", {})
        if not name:
            continue
        if not isinstance(arguments, str):
            arguments = json.dumps(arguments or {}, ensure_ascii=False)
        normalised.append(
            {
                "id": call.get("id") or f"call_{uuid.uuid4().hex}",
                "type": "function",
                "function": {"name": str(name), "arguments": arguments},
            }
        )
    return normalised


def _assistant_message(raw_content: str, request: ChatCompletionRequest) -> tuple[dict[str, Any], str]:
    parsed = _extract_json_object(raw_content) if request.tools else None
    if parsed:
        tool_calls = _normalise_tool_calls(parsed)
        if tool_calls:
            return {"role": "assistant", "content": "", "tool_calls": tool_calls}, "tool_calls"
        if isinstance(parsed.get("content"), str):
            return {"role": "assistant", "content": parsed["content"]}, "stop"
    return {"role": "assistant", "content": raw_content}, "stop"


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
        message, finish_reason = _assistant_message(content, request)
        return {
            "id": f"chatcmpl-hermes-{uuid.uuid4().hex}",
            "object": "chat.completion",
            "created": now,
            "model": request.model,
            "choices": [
                {
                    "index": 0,
                    "message": message,
                    "finish_reason": finish_reason,
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
