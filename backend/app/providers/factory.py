"""Factory for configured AIS provider adapters."""

from __future__ import annotations

from app.core.settings import Settings
from app.providers.base import AISProvider
from app.providers.public_api import PublicAPIProvider
from app.providers.replay import ReplayAISProvider


def create_ais_provider(settings: Settings) -> AISProvider:
    provider = settings.ais_provider.lower().strip()
    if provider == "replay":
        return ReplayAISProvider(
            data_path=settings.replay_data_path,
            speed_multiplier=settings.replay_speed_multiplier,
            loop=settings.replay_loop,
        )
    if provider == "public_api":
        return PublicAPIProvider(
            api_url=settings.ais_api_url or "",
            api_key=settings.ais_api_key,
            poll_interval=settings.ais_poll_interval,
            request_timeout_seconds=settings.ais_request_timeout_seconds,
            max_backoff_seconds=settings.ais_max_backoff_seconds,
        )
    raise ValueError(f"Unsupported AIS_PROVIDER value: {settings.ais_provider}")

