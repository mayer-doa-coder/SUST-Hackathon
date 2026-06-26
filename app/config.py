from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_version: str = "1.0.0"
    port: int = 8000
    gateway_upstream_url: str = ""
    gateway_upstream_timeout_seconds: float = 5.0
    auth_required: bool = False
    auth_issuer: str = "queuestorm-investigator"
    auth_audience: str = "queuestorm-api"
    auth_jwt_secret: str = "development-only-change-me"
    auth_access_token_seconds: int = 900
    auth_refresh_token_seconds: int = 604800
    auth_demo_username: str = "support.agent"
    auth_demo_password: str = "change-me"
    auth_demo_roles: str = "support_agent,admin"
    rate_limit_enabled: bool = False
    rate_limit_requests: int = 120
    rate_limit_window_seconds: int = 60
    evidence_shard_count: int = 16
    evidence_cache_ttl_seconds: int = 300
    investigation_active_ruleset_version: str = "rules-2026-06-26.v1"
    investigation_rule_cache_ttl_seconds: int = 300
    nlg_prompt_version: str = "nlg-prompt-2026-06-26.v1"
    nlg_template_version: str = "nlg-template-2026-06-26.v1"
    safety_policy_version: str = "safety-policy-2026-06-26.v1"
    gateway_replica_count: int = 2
    auth_replica_count: int = 2
    ticket_replica_count: int = 3
    evidence_replica_count: int = 4
    investigation_replica_count: int = 3
    nlg_replica_count: int = 2
    workflow_replica_count: int = 2
    messaging_replica_count: int = 2
    database_primary_url: str = "postgresql://primary/queuestorm"
    database_read_replica_urls: str = "postgresql://replica-a/queuestorm,postgresql://replica-b/queuestorm"
    database_pool_min_size: int = 5
    database_pool_max_size: int = 50
    transaction_shard_strategy: str = "account_id_hash"
    cache_backend: str = "in-memory"
    cache_stampede_jitter_seconds: int = 15
    load_test_virtual_users: int = 200
    load_test_duration_seconds: int = 60
    load_test_target_p95_ms: int = 5000
    service_name: str = "queuestorm-investigator"
    log_level: str = "INFO"
    observability_recent_trace_limit: int = 100
    readiness_require_llm_key: bool = False
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-haiku-4-5-20251001"
    anthropic_base_url: str = "https://api.anthropic.com/v1/messages"
    llm_timeout_seconds: float = 8.0
    llm_max_complaint_chars: int = 8000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

