import os
from dataclasses import dataclass, field

# Load .env file for local development only (not needed in Lambda)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not available in Lambda environment, which is fine
    pass


class ConfigurationError(RuntimeError):
    """Raised when mandatory configuration is missing or invalid."""


@dataclass
class Config:
    """Configuration for search initializer orchestrator."""
    state_machine_arn: str
    execution_name_prefix: str = field(default_factory=lambda: os.getenv("EXECUTION_NAME_PREFIX", "search-exec"))
    cors_allowed_origin: str = field(default_factory=lambda: os.getenv("CORS_ALLOWED_ORIGIN", "*"))

    @classmethod
    def load(cls) -> "Config":
        """Load configuration from environment variables."""
        arn = os.getenv("LOGICAL_SEARCH_STATE_MACHINE_ARN", "").strip()
        if not arn:
            raise ConfigurationError("LOGICAL_SEARCH_STATE_MACHINE_ARN environment variable is required")

        return cls(state_machine_arn=arn)