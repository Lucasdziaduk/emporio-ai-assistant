
"""Central configuration for the Emporio AI Assistant."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


# Project root: parent directory of the app folder.
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Load environment variables from the project root.
load_dotenv(PROJECT_ROOT / ".env", override=False)


def get_int_setting(
    name: str,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    """Read and validate an integer environment variable."""

    raw_value = os.getenv(name, str(default)).strip()

    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ValueError(
            f"{name} must be an integer. Received: {raw_value!r}"
        ) from exc

    if not minimum <= value <= maximum:
        raise ValueError(
            f"{name} must be between {minimum} and {maximum}."
        )

    return value


def get_choice_setting(
    name: str,
    default: str,
    allowed_values: tuple[str, ...],
) -> str:
    """Read and validate a setting against allowed values."""

    value = os.getenv(name, default).strip()

    # Compare without considering letter case,
    # while preserving the canonical format.
    allowed_lookup = {
        item.lower(): item
        for item in allowed_values
    }

    normalized_value = value.lower()

    if normalized_value not in allowed_lookup:
        raise ValueError(
            f"Invalid value for {name}: {value!r}. "
            f"Allowed values: {', '.join(allowed_values)}"
        )

    return allowed_lookup[normalized_value]


@dataclass(frozen=True)
class Settings:
    """Application settings."""

    app_env: str
    gemini_api_key: str | None = field(repr=False)
    gemini_model: str

    max_tool_rounds: int
    max_tool_calls: int

    session_ttl_minutes: int
    order_auth_ttl_minutes: int

    log_level: str

    project_root: Path
    sample_data_dir: Path
    private_data_dir: Path
    policy_pdf_path: Path

    sqlite_database: str = ":memory:"


def load_settings() -> Settings:
    """Load and validate all application settings."""

    app_env = get_choice_setting(
        "APP_ENV",
        "development",
        ("development", "testing", "production"),
    )

    log_level = get_choice_setting(
        "LOG_LEVEL",
        "INFO",
        ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"),
    )

    gemini_model = os.getenv(
        "GEMINI_MODEL",
        "gemini-3.8-flash",
    ).strip()

    if not gemini_model:
        raise ValueError("GEMINI_MODEL cannot be empty.")

    return Settings(
        app_env=app_env,
        gemini_api_key=(
            os.getenv("GEMINI_API_KEY", "").strip() or None
        ),
        gemini_model=gemini_model,

        max_tool_rounds=get_int_setting(
            "MAX_TOOL_ROUNDS", 4, 1, 10
        ),
        max_tool_calls=get_int_setting(
            "MAX_TOOL_CALLS", 8, 1, 20
        ),

        session_ttl_minutes=get_int_setting(
            "SESSION_TTL_MINUTES", 30, 1, 1440
        ),
        order_auth_ttl_minutes=get_int_setting(
            "ORDER_AUTH_TTL_MINUTES", 10, 1, 60
        ),

        log_level=log_level,

        project_root=PROJECT_ROOT,
        sample_data_dir=PROJECT_ROOT / "data" / "sample",
        private_data_dir=PROJECT_ROOT / "data" / "private",
        policy_pdf_path=(
            PROJECT_ROOT / "data" / "private" / "store_policies.pdf"
        ),
    )


# Shared application configuration.
settings = load_settings()
