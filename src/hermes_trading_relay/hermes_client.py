from __future__ import annotations

import subprocess

from .config import RelayConfig
from .openai_compat import ChatCompletionRequest, ChatMessage


def _content_to_text(content: str | list[dict] | None) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    parts: list[str] = []
    for item in content:
        if isinstance(item, dict) and item.get("type") == "text":
            parts.append(str(item.get("text", "")))
        elif isinstance(item, dict):
            parts.append(str(item))
    return "\n".join(parts)


def messages_to_prompt(messages: list[ChatMessage], system_prefix: str) -> str:
    rendered = [system_prefix.strip(), "", "OpenAI-compatible request messages:"]
    for msg in messages:
        rendered.append(f"\n[{msg.role.upper()}]\n{_content_to_text(msg.content)}")
    rendered.append(
        "\nRespond as the assistant. Keep the answer compatible with a chat/completions response."
    )
    return "\n".join(rendered).strip()


class HermesClient:
    def __init__(self, config: RelayConfig):
        self.config = config

    def build_command(self, prompt: str, model: str | None = None) -> list[str]:
        cmd = [*self.config.hermes_command, "chat", "-q", prompt, "--quiet"]
        profile = self.config.hermes_profile
        if profile:
            cmd.extend(["--profile", profile])
        provider = self.config.hermes_provider
        if provider:
            cmd.extend(["--provider", provider])
        selected_model = model or self.config.hermes_model
        if selected_model and selected_model != "hermes-codex":
            cmd.extend(["--model", selected_model])
        return cmd

    def complete(self, request: ChatCompletionRequest) -> str:
        if request.stream:
            raise ValueError("stream=true is not supported by hermes-trading-relay yet")
        prompt = messages_to_prompt(request.messages, self.config.system_prefix)
        cmd = self.build_command(prompt, request.model)
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=self.config.request_timeout_seconds,
            check=False,
        )
        if result.returncode != 0:
            stderr = result.stderr.strip() or result.stdout.strip() or "Hermes command failed"
            raise RuntimeError(stderr)
        return result.stdout.strip()
