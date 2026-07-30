# Implement with Hermes

This guide shows how to use `hermes-trading-relay` in a Hermes environment so TradingAgents can call a local OpenAI-compatible endpoint while Hermes handles OAuth-authenticated Codex calls.

## Architecture

```text
TradingAgents Python process
  -> TRADINGAGENTS_LLM_BACKEND_URL=http://127.0.0.1:8765/v1
  -> hermes-trading-relay FastAPI server
  -> hermes chat -q ... --provider openai-codex
  -> Hermes authenticated Codex provider
```

## Prerequisites

- Hermes Agent installed and working.
- Hermes authenticated with OpenAI Codex OAuth.
- `hermes status --all` shows `Provider: OpenAI Codex` and `OpenAI Codex ✓ logged in`.
- Python 3.10+.
- TradingAgents installed separately.

Verify Hermes:

```bash
hermes status --all
hermes auth list
```

## Windows-native Hermes setup

Use Git Bash/MSYS shell syntax.

```bash
cd /c/Users/<you>
git clone https://github.com/Hoaggie78/hermes-trading-relay.git
cd hermes-trading-relay
python -m venv .venv
source .venv/Scripts/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Start:

```bash
export HERMES_RELAY_PROVIDER=openai-codex
export HERMES_RELAY_PROFILE=trading
hermes-trading-relay --host 127.0.0.1 --port 8765
```

If `hermes` is not on PATH, create a wrapper script and set:

```bash
export HERMES_RELAY_COMMAND=/c/Users/<you>/bin/hermes-wrapper.sh
```

## WSL2-native Hermes setup

Use this when Hermes is installed inside WSL2.

```bash
cd ~
git clone https://github.com/Hoaggie78/hermes-trading-relay.git
cd hermes-trading-relay
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Start:

```bash
export HERMES_RELAY_PROVIDER=openai-codex
export HERMES_RELAY_PROFILE=trading
hermes-trading-relay --host 127.0.0.1 --port 8765
```

## Cross-boundary Windows <-> WSL2 notes

### TradingAgents and relay both on Windows

Use:

```env
TRADINGAGENTS_LLM_BACKEND_URL=http://127.0.0.1:8765/v1
```

### TradingAgents and relay both in WSL2

Use:

```env
TRADINGAGENTS_LLM_BACKEND_URL=http://127.0.0.1:8765/v1
```

### Relay in Windows, TradingAgents in WSL2

Start relay on Windows with:

```bash
hermes-trading-relay --host 0.0.0.0 --port 8765
```

From WSL2, find Windows host IP:

```bash
grep nameserver /etc/resolv.conf
```

Then set TradingAgents:

```env
TRADINGAGENTS_LLM_BACKEND_URL=http://<WINDOWS_HOST_IP>:8765/v1
```

### Relay in WSL2, TradingAgents in Windows

Start relay inside WSL2 with:

```bash
hermes-trading-relay --host 0.0.0.0 --port 8765
hostname -I
```

Then from Windows use:

```env
TRADINGAGENTS_LLM_BACKEND_URL=http://<WSL_IP>:8765/v1
```

Windows localhost forwarding may also make `http://127.0.0.1:8765/v1` work, but verify with `curl` before trusting it.

## TradingAgents `.env`

```env
TRADINGAGENTS_LLM_PROVIDER=openai_compatible
TRADINGAGENTS_LLM_BACKEND_URL=http://127.0.0.1:8765/v1
TRADINGAGENTS_DEEP_THINK_LLM=hermes-codex
TRADINGAGENTS_QUICK_THINK_LLM=hermes-codex
OPENAI_COMPATIBLE_API_KEY=not-needed
TRADINGAGENTS_OUTPUT_LANGUAGE=English
TRADINGAGENTS_MAX_DEBATE_ROUNDS=1
TRADINGAGENTS_MAX_RISK_ROUNDS=1
TRADINGAGENTS_CHECKPOINT_ENABLED=true
TRADINGAGENTS_TEMPERATURE=0.0
```

## Verification

```bash
curl -s http://127.0.0.1:8765/health
curl -s http://127.0.0.1:8765/v1/models
curl -s http://127.0.0.1:8765/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"hermes-codex","messages":[{"role":"user","content":"Say relay_ok only."}]}'
```

Expected:

- `/health` returns `ok: true`
- `/v1/models` includes `hermes-codex`
- `/v1/chat/completions` returns an OpenAI-style response object

## Troubleshooting

### `hermes` command not found

Set `HERMES_RELAY_COMMAND` to a wrapper script or full command available from the relay process.

### 502 from `/v1/chat/completions`

The relay reached FastAPI but the Hermes subprocess failed. Run:

```bash
hermes status --all
hermes chat -q "Say ok" --provider openai-codex --quiet
```

### TradingAgents says OpenAI-compatible auth failed

Set a placeholder because some clients require the variable to exist:

```env
OPENAI_COMPATIBLE_API_KEY=not-needed
```

### WSL2 connection fails

Bind the relay to `0.0.0.0`, then use the actual host IP. Verify with `curl` across the OS boundary before running TradingAgents.
