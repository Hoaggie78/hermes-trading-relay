from __future__ import annotations

import os
from dataclasses import dataclass


def _split_command(raw: str) -> list[str]:
    # Keep command parsing intentionally simple and cross-platform. If a Hermes
    # path contains spaces, set HERMES_RELAY_COMMAND to a wrapper script path.
    return [part for part in raw.strip().split(" ") if part]


@dataclass(frozen=True)
class RelayConfig:
    hermes_command: list[str]
    hermes_profile: str | None
    hermes_model: str | None
    hermes_provider: str | None
    host: str
    port: int
    request_timeout_seconds: int
    system_prefix: str

    @classmethod
    def from_env(cls) -> RelayConfig:
        command = os.getenv("HERMES_RELAY_COMMAND", "hermes")
        return cls(
            hermes_command=_split_command(command),
            hermes_profile=os.getenv("HERMES_RELAY_PROFILE") or None,
            hermes_model=os.getenv("HERMES_RELAY_MODEL") or None,
            hermes_provider=os.getenv("HERMES_RELAY_PROVIDER") or None,
            host=os.getenv("HERMES_RELAY_HOST", "127.0.0.1"),
            port=int(os.getenv("HERMES_RELAY_PORT", "8765")),
            request_timeout_seconds=int(os.getenv("HERMES_RELAY_TIMEOUT", "300")),
            system_prefix=os.getenv(
                "HERMES_RELAY_SYSTEM_PREFIX",
                "You are responding through hermes-trading-relay. Return concise, "
                "research-only trading analysis. Do not claim financial advice or place trades.",
            ),
        )
