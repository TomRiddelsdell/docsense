import os
from typing import TYPE_CHECKING

from .base import AIProvider, ProviderType
from .rate_limiter import RateLimiter, RateLimitConfig

if TYPE_CHECKING:
    from .gemini_provider import GeminiProvider
    from .openai_provider import OpenAIProvider
    from .claude_provider import ClaudeProvider

API_KEY_ENV_VARS = {
    ProviderType.CLAUDE: "AI_INTEGRATIONS_ANTHROPIC_API_KEY",
    ProviderType.GEMINI: "AI_INTEGRATIONS_GEMINI_API_KEY",
    ProviderType.OPENAI: "AI_INTEGRATIONS_OPENAI_API_KEY",
}

PROVIDER_PRIORITY = [ProviderType.CLAUDE, ProviderType.GEMINI, ProviderType.OPENAI]


class ProviderFactory:

    def __init__(self, rate_limit_config: RateLimitConfig | None = None):
        self._rate_limit_config = rate_limit_config or RateLimitConfig()
        self._instances: dict[ProviderType, AIProvider] = {}
        self._rate_limiters: dict[ProviderType, RateLimiter] = {}

    def is_provider_configured(self, provider_type: ProviderType) -> bool:
        env_var = API_KEY_ENV_VARS.get(provider_type)
        if not env_var:
            return False
        return bool(os.environ.get(env_var))

    def get_configured_providers(self) -> list[ProviderType]:
        return [p for p in PROVIDER_PRIORITY if self.is_provider_configured(p)]

    def get_provider(self, provider_type: ProviderType) -> AIProvider:
        if not self.is_provider_configured(provider_type):
            configured = self.get_configured_providers()
            if configured:
                raise ValueError(
                    f"Provider '{provider_type.value}' is not configured (missing API key). "
                    f"Available providers: {[p.value for p in configured]}"
                )
            else:
                raise ValueError(
                    f"Provider '{provider_type.value}' is not configured (missing API key). "
                    f"No providers are configured. Please set an API key for at least one provider."
                )
        if provider_type not in self._instances:
            self._instances[provider_type] = self._create_provider(provider_type)
        return self._instances[provider_type]

    def get_rate_limiter(self, provider_type: ProviderType) -> RateLimiter:
        if provider_type not in self._rate_limiters:
            self._rate_limiters[provider_type] = RateLimiter(self._rate_limit_config)
        return self._rate_limiters[provider_type]

    def _create_provider(self, provider_type: ProviderType) -> AIProvider:
        rate_limiter = self.get_rate_limiter(provider_type)
        
        if provider_type == ProviderType.GEMINI:
            from .gemini_provider import GeminiProvider
            return GeminiProvider(rate_limiter=rate_limiter)
        elif provider_type == ProviderType.OPENAI:
            from .openai_provider import OpenAIProvider
            return OpenAIProvider(rate_limiter=rate_limiter)
        elif provider_type == ProviderType.CLAUDE:
            from .claude_provider import ClaudeProvider
            return ClaudeProvider(rate_limiter=rate_limiter)
        else:
            raise ValueError(f"Unknown provider type: {provider_type}")

    def get_default_provider(self) -> AIProvider:
        configured = self.get_configured_providers()
        if not configured:
            raise ValueError(
                "No AI providers are configured. Please set an API key for at least one provider: "
                f"{[p.value for p in PROVIDER_PRIORITY]}"
            )
        return self.get_provider(configured[0])

    async def get_available_providers(self) -> list[ProviderType]:
        available = []
        for provider_type in ProviderType:
            try:
                provider = self.get_provider(provider_type)
                if await provider.is_available():
                    available.append(provider_type)
            except Exception:
                continue
        return available

    def clear_cache(self) -> None:
        self._instances.clear()
        self._rate_limiters.clear()
