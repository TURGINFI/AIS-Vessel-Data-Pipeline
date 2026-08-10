"""Environment-driven application settings."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AIS Trajectory Predictor"
    app_version: str = "0.1.0"
    environment: str = Field(default="development", alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    ais_provider: str = Field(default="replay", alias="AIS_PROVIDER")
    ais_api_url: str | None = Field(default=None, alias="AIS_API_URL")
    ais_api_key: str | None = Field(default=None, alias="AIS_API_KEY")
    ais_poll_interval: float = Field(default=15.0, alias="AIS_POLL_INTERVAL")
    ais_request_timeout_seconds: float = Field(default=10.0, alias="AIS_REQUEST_TIMEOUT_SECONDS")
    ais_max_backoff_seconds: float = Field(default=60.0, alias="AIS_MAX_BACKOFF_SECONDS")

    replay_data_path: str = Field(default="data/sample/replay_ais.csv", alias="REPLAY_DATA_PATH")
    replay_speed_multiplier: float = Field(default=30.0, alias="REPLAY_SPEED_MULTIPLIER")
    replay_loop: bool = Field(default=True, alias="REPLAY_LOOP")

    database_url: str = Field(default="sqlite:///./storage/ais.db", alias="DATABASE_URL")
    history_window_minutes: int = Field(default=60, alias="HISTORY_WINDOW_MINUTES")
    max_positions_per_vessel: int = Field(default=500, alias="MAX_POSITIONS_PER_VESSEL")

    prediction_horizon_seconds: int = Field(default=300, alias="PREDICTION_HORIZON_SECONDS")
    prediction_step_seconds: int = Field(default=30, alias="PREDICTION_STEP_SECONDS")
    max_prediction_speed_knots: float = Field(default=50.0, alias="MAX_PREDICTION_SPEED_KNOTS")

    cors_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        alias="CORS_ORIGINS",
    )
    ingestion_enabled: bool = Field(default=True, alias="INGESTION_ENABLED")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

