# Hermes Trading Relay

OpenAI-compatible local relay for running TradingAgents through a Hermes environment that is already authenticated with OpenAI Codex OAuth.

This project lets tools such as [TradingAgents](https://github.com/TauricResearch/TradingAgents) point at a local `/v1/chat/completions` endpoint while the actual model call is executed by the local `hermes chat -q ...` command.

> Research-only default: this relay is for market research, paper-trading experiments, and agent workflow testing. It is not financial advice and it does not place trades.

## What problem this solves

TradingAgents' internal Python LLM clients expect a provider API key or an OpenAI-compatible HTTP endpoint. Hermes can already be authenticated through OAuth providers such as `openai-codex`, but that auth lives inside Hermes.

Hermes Trading Relay bridges that gap:

```text
TradingAgents -> http://127.0.0.1:8765/v1/chat/completions -> hermes chat -q -> Hermes OAuth Codex
```

## Current status

This is an initial public MVP:

- exposes `GET /health`
- exposes `GET /v1/models`
- exposes `POST /v1/chat/completions`
- shells out to `hermes chat -q` for non-streaming requests
- supports Windows-native Hermes and WSL2-native Hermes installs
- does not support streaming yet
- does not expose live trading or brokerage actions

## Install

### Windows-native Hermes

Use this when Hermes is installed on Windows like:

```text
C:\Users\<you>\AppData\Local\hermes\
```

```bash
cd /c/Users/<you>
git clone https://github.com/Hoaggie78/hermes-trading-relay.git
cd hermes-trading-relay
python -m venv .venv
source .venv/Scripts/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
hermes status --all
```

Start the relay:

```bash
source .venv/Scripts/activate
export HERMES_RELAY_PROVIDER=openai-codex
export HERMES_RELAY_PROFILE=trading   # optional; omit to use default profile
hermes-trading-relay --host 127.0.0.1 --port 8765
```

Verify:

```bash
curl -s http://127.0.0.1:8765/health
curl -s http://127.0.0.1:8765/v1/models
curl -s http://127.0.0.1:8765/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"hermes-codex","messages":[{"role":"user","content":"Say relay_ok in one word."}]}'
```

### WSL2-native Hermes

Use this when Hermes is installed inside WSL2 and `hermes` works from the WSL shell.

```bash
cd ~
git clone https://github.com/Hoaggie78/hermes-trading-relay.git
cd hermes-trading-relay
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
hermes status --all
```

Start the relay inside WSL2:

```bash
source .venv/bin/activate
export HERMES_RELAY_PROVIDER=openai-codex
export HERMES_RELAY_PROFILE=trading   # optional; omit to use default profile
hermes-trading-relay --host 127.0.0.1 --port 8765
```

Verify inside WSL2:

```bash
curl -s http://127.0.0.1:8765/health
curl -s http://127.0.0.1:8765/v1/models
```

If TradingAgents is running in Windows and the relay is running in WSL2, bind to all interfaces and use the WSL IP or Windows localhost forwarding:

```bash
hermes-trading-relay --host 0.0.0.0 --port 8765
hostname -I
```

Then test from Windows with the WSL IP:

```bash
curl http://<WSL_IP>:8765/health
```

## Configure TradingAgents

In your TradingAgents repo `.env`:

```env
TRADINGAGENTS_LLM_PROVIDER=openai_compatible
TRADINGAGENTS_LLM_BACKEND_URL=http://127.0.0.1:8765/v1
TRADINGAGENTS_DEEP_THINK_LLM=hermes-codex
TRADINGAGENTS_QUICK_THINK_LLM=hermes-codex
OPENAI_COMPATIBLE_API_KEY=not-needed-local-relay
TRADINGAGENTS_OUTPUT_LANGUAGE=English
TRADINGAGENTS_MAX_DEBATE_ROUNDS=1
TRADINGAGENTS_MAX_RISK_ROUNDS=1
TRADINGAGENTS_CHECKPOINT_ENABLED=true
TRADINGAGENTS_TEMPERATURE=0.0
```

If TradingAgents runs in WSL2 and the relay runs in Windows, use the Windows host IP from WSL2. Common options:

```bash
grep nameserver /etc/resolv.conf
```

Then set:

```env
TRADINGAGENTS_LLM_BACKEND_URL=http://<WINDOWS_HOST_IP>:8765/v1
```

## Environment variables

```env
HERMES_RELAY_COMMAND=hermes
HERMES_RELAY_PROFILE=trading
HERMES_RELAY_PROVIDER=openai-codex
HERMES_RELAY_MODEL=gpt-5.5
HERMES_RELAY_HOST=127.0.0.1
HERMES_RELAY_PORT=8765
HERMES_RELAY_TIMEOUT=300
HERMES_RELAY_SYSTEM_PREFIX=You are a research-only trading analysis assistant. Do not provide financial advice or place trades.
```

Notes:

- `HERMES_RELAY_PROFILE` is optional. Use it if you created a dedicated Hermes `trading` profile.
- `HERMES_RELAY_PROVIDER=openai-codex` tells Hermes to use the OAuth-backed provider.
- `HERMES_RELAY_MODEL` is optional. If omitted, Hermes uses its configured default model.
- `HERMES_RELAY_COMMAND` can point at a wrapper script if `hermes` is not on PATH.

## Safety boundaries

This relay:

- does not store API keys
- does not read brokerage credentials
- does not place trades
- does not stream responses yet
- does not guarantee TradingAgents output quality

You still need to validate:

- data freshness
- model hallucinations
- trading costs/slippage
- overfitting
- paper-trading results
- whether generated analysis is suitable for your use case

## Development

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
```

## License

MIT
