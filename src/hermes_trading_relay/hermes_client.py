from __future__ import annotations

import json
import subprocess
from typing import Any

from .config import RelayConfig
from .openai_compat import ChatCompletionRequest, ChatMessage

MAX_MESSAGE_CHARS = 2_000
MAX_PROMPT_CHARS = 24_000


def _truncate_middle(text: str, max_chars: int, label: str = "content") -> str:
    if len(text) <= max_chars:
        return text
    marker = f"\n...[{label} truncated {len(text) - max_chars} chars by hermes-trading-relay]\n"
    if max_chars <= len(marker) + 20:
        return text[:max_chars]
    head = max_chars // 2
    tail = max_chars - head - len(marker)
    return text[:head] + marker + text[-tail:]


def _content_to_text(content: str | list[dict[str, Any]] | None, max_chars: int = MAX_MESSAGE_CHARS) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        text = content
    else:
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
            elif isinstance(item, dict):
                parts.append(str(item))
        text = "\n".join(parts)
    return _truncate_middle(text, max_chars, "message")


def _tool_names(tools: list[dict[str, Any]] | None) -> list[str]:
    names: list[str] = []
    for tool in tools or []:
        function = tool.get("function", {}) if isinstance(tool, dict) else {}
        name = function.get("name")
        if name:
            names.append(str(name))
    return names


def _summarise_tools(tools: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    summary: list[dict[str, Any]] = []
    for tool in tools or []:
        function = tool.get("function", {}) if isinstance(tool, dict) else {}
        name = function.get("name")
        if not name:
            continue
        parameters = function.get("parameters", {})
        properties = parameters.get("properties", {}) if isinstance(parameters, dict) else {}
        required = parameters.get("required", []) if isinstance(parameters, dict) else []
        summary.append(
            {
                "name": str(name),
                "description": str(function.get("description", ""))[:500],
                "parameters": {
                    key: value.get("type", "any") if isinstance(value, dict) else "any"
                    for key, value in properties.items()
                },
                "required": required,
            }
        )
    return summary


def _render_messages(messages: list[ChatMessage]) -> str:
    rendered = ["OpenAI-compatible request messages:"]
    for msg in messages:
        rendered.append(f"\n[{msg.role.upper()}]")
        if msg.name:
            rendered.append(f"name: {msg.name}")
        if msg.tool_call_id:
            rendered.append(f"tool_call_id: {msg.tool_call_id}")
        if msg.tool_calls:
            rendered.append("tool_calls:")
            rendered.append(_truncate_middle(json.dumps(msg.tool_calls, ensure_ascii=False), MAX_MESSAGE_CHARS, "tool_calls"))
        rendered.append(_content_to_text(msg.content))
    return "\n".join(rendered)


def _render_tool_instructions(
    tools: list[dict[str, Any]] | None,
    tool_choice: str | dict[str, Any] | None,
) -> str:
    if not tools:
        return "\nRespond as the assistant. Keep the answer compatible with a chat/completions response."
    return "\n".join(
        [
            "",
            "Tool-calling bridge instructions:",
            "You are serving an OpenAI-compatible Chat Completions client.",
            "The client provided tools. If a tool is needed, respond ONLY with valid JSON in this exact shape:",
            '{"tool_calls":[{"name":"tool_name","arguments":{"arg":"value"}}]}',
            "Use only tool names from the provided schemas. Do not wrap the JSON in markdown.",
            "If no tool is needed, respond ONLY with valid JSON in this exact shape:",
            '{"content":"assistant response text"}',
            f"Tool choice requested by client: {tool_choice!r}",
            f"Available tool names: {', '.join(_tool_names(tools))}",
            "Tool schemas summary:",
            json.dumps(_summarise_tools(tools), ensure_ascii=False),
        ]
    )


def messages_to_prompt(
    messages: list[ChatMessage],
    system_prefix: str,
    tools: list[dict[str, Any]] | None = None,
    tool_choice: str | dict[str, Any] | None = None,
) -> str:
    prefix = system_prefix.strip()
    message_block = _render_messages(messages)
    tool_block = _render_tool_instructions(tools, tool_choice)
    prompt = "\n\n".join([prefix, message_block, tool_block]).strip()
    if len(prompt) <= MAX_PROMPT_CHARS:
        return prompt

    reserved = len(prefix) + len(tool_block) + 80
    message_budget = max(1_000, MAX_PROMPT_CHARS - reserved)
    message_block = _truncate_middle(message_block, message_budget, "prompt truncated")
    return "\n\n".join([prefix, message_block, tool_block]).strip()


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
        prompt = messages_to_prompt(
            request.messages,
            self.config.system_prefix,
            tools=request.tools,
            tool_choice=request.tool_choice,
        )
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
