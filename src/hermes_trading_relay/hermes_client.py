from __future__ import annotations

import json
import subprocess
from typing import Any

from .config import RelayConfig
from .openai_compat import ChatCompletionRequest, ChatMessage


def _content_to_text(content: str | list[dict[str, Any]] | None) -> str:
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


def messages_to_prompt(
    messages: list[ChatMessage],
    system_prefix: str,
    tools: list[dict[str, Any]] | None = None,
    tool_choice: str | dict[str, Any] | None = None,
) -> str:
    rendered = [system_prefix.strip(), "", "OpenAI-compatible request messages:"]
    for msg in messages:
        rendered.append(f"\n[{msg.role.upper()}]")
        if msg.name:
            rendered.append(f"name: {msg.name}")
        if msg.tool_call_id:
            rendered.append(f"tool_call_id: {msg.tool_call_id}")
        if msg.tool_calls:
            rendered.append("tool_calls:")
            rendered.append(json.dumps(msg.tool_calls, ensure_ascii=False))
        rendered.append(_content_to_text(msg.content))

    if tools:
        rendered.extend(
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
    else:
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
