import pytest

from hermes_trading_relay.config import RelayConfig
from hermes_trading_relay.hermes_client import HermesClient, messages_to_prompt
from hermes_trading_relay.openai_compat import ChatCompletionRequest, ChatMessage


def test_messages_to_prompt_renders_roles():
    prompt = messages_to_prompt(
        [
            ChatMessage(role="system", content="Use research-only wording."),
            ChatMessage(role="user", content="Analyze SPY."),
        ],
        "prefix",
    )

    assert "prefix" in prompt
    assert "[SYSTEM]" in prompt
    assert "Use research-only wording." in prompt
    assert "[USER]" in prompt
    assert "Analyze SPY." in prompt


def test_messages_to_prompt_adds_tool_call_bridge_instructions():
    prompt = messages_to_prompt(
        [ChatMessage(role="user", content="Analyze SPY.")],
        "prefix",
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "get_stock_data",
                    "description": "Fetch stock data",
                    "parameters": {"type": "object", "properties": {"ticker": {"type": "string"}}},
                },
            }
        ],
        tool_choice="auto",
    )

    assert "Tool-calling bridge instructions" in prompt
    assert "get_stock_data" in prompt
    assert '"tool_calls"' in prompt
    assert '"content"' in prompt


def test_build_command_includes_profile_provider_and_model():
    cfg = RelayConfig(
        hermes_command=["hermes"],
        hermes_profile="trading",
        hermes_model=None,
        hermes_provider="openai-codex",
        host="127.0.0.1",
        port=8765,
        request_timeout_seconds=300,
        system_prefix="prefix",
    )
    client = HermesClient(cfg)

    cmd = client.build_command("hello", "gpt-5.5")

    assert cmd[:4] == ["hermes", "chat", "-q", "hello"]
    assert "--profile" in cmd
    assert "trading" in cmd
    assert "--provider" in cmd
    assert "openai-codex" in cmd
    assert "--model" in cmd
    assert "gpt-5.5" in cmd


def test_streaming_rejected():
    cfg = RelayConfig(
        hermes_command=["hermes"],
        hermes_profile=None,
        hermes_model=None,
        hermes_provider=None,
        host="127.0.0.1",
        port=8765,
        request_timeout_seconds=300,
        system_prefix="prefix",
    )
    client = HermesClient(cfg)
    request = ChatCompletionRequest(
        model="hermes-codex",
        messages=[ChatMessage(role="user", content="hello")],
        stream=True,
    )

    with pytest.raises(ValueError, match="stream=true"):
        client.complete(request)
